"""Direct-mode unit test suite for MultiSourceSynthesizer primitive."""

import json
import pytest


def test_register_feed_success(direct_vm, direct_deploy, direct_alice):
    """Test registering a valid multi-source numeric feed."""
    contract = direct_deploy("contracts/multi_source_synthesizer.py")
    direct_vm.sender = direct_alice

    sources = [
        "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT",
        "https://api.kraken.com/0/public/Ticker?pair=ETHUSD",
        "https://api.coinbase.com/v2/prices/ETH-USD/spot",
    ]

    contract.register_feed(
        feed_id="ETH_USD",
        name="Ethereum / USD Spot Price",
        feed_type="NUMERIC",
        query_prompt="What is the current spot price of Ethereum in USD?",
        sources=sources,
        tolerance_bps=100,  # 1.0% tolerance
        min_sources_required=2,
        heartbeat_seconds=300,
    )

    config = contract.get_feed_config("ETH_USD")
    assert config["feed_id"] == "ETH_USD"
    assert config["feed_type"] == "NUMERIC"
    assert config["tolerance_bps"] == 100
    assert config["min_sources_required"] == 2
    assert len(config["sources"]) == 3
    assert config["is_active"] is True

    feed_list = contract.list_feeds()
    assert "ETH_USD" in feed_list


def test_register_feed_validation_bounds(direct_vm, direct_deploy, direct_alice):
    """Test validation errors for invalid feed registration parameters."""
    contract = direct_deploy("contracts/multi_source_synthesizer.py")
    direct_vm.sender = direct_alice

    # 1. Empty feed_id
    with pytest.raises(Exception, match=r"\[EXPECTED\] feed_id cannot be empty"):
        contract.register_feed(
            feed_id="",
            name="Test",
            feed_type="NUMERIC",
            query_prompt="query",
            sources=["https://api1.com", "https://api2.com"],
            tolerance_bps=100,
            min_sources_required=2,
            heartbeat_seconds=300,
        )

    # 2. Invalid feed_type
    with pytest.raises(Exception, match=r"\[EXPECTED\] feed_type must be 'NUMERIC' or 'CATEGORICAL'"):
        contract.register_feed(
            feed_id="TEST_FEED",
            name="Test",
            feed_type="INVALID_TYPE",
            query_prompt="query",
            sources=["https://api1.com", "https://api2.com"],
            tolerance_bps=100,
            min_sources_required=2,
            heartbeat_seconds=300,
        )

    # 3. Too few sources (< 2)
    with pytest.raises(Exception, match=r"\[EXPECTED\] sources count must be between 2 and 5"):
        contract.register_feed(
            feed_id="TEST_FEED",
            name="Test",
            feed_type="NUMERIC",
            query_prompt="query",
            sources=["https://api1.com"],
            tolerance_bps=100,
            min_sources_required=1,
            heartbeat_seconds=300,
        )


def test_refresh_feed_numeric_consensus(direct_vm, direct_deploy, direct_alice):
    """Test multi-validator consensus aggregation across 3 agreeing APIs."""
    contract = direct_deploy("contracts/multi_source_synthesizer.py")
    direct_vm.sender = direct_alice

    sources = [
        "https://api1.example.com/eth",
        "https://api2.example.com/eth",
        "https://api3.example.com/eth",
    ]

    contract.register_feed(
        feed_id="ETH_PRICE",
        name="ETH Price Feed",
        feed_type="NUMERIC",
        query_prompt="Extract ETH/USD spot price.",
        sources=sources,
        tolerance_bps=50,
        min_sources_required=2,
        heartbeat_seconds=300,
    )

    # Mock web endpoints returning slightly differing but close values
    direct_vm.mock_web(
        r".*api1\.example\.com/eth.*",
        {"response": {"status": 200, "headers": {}, "body": json.dumps({"price": 3450.00}).encode("utf-8")}, "method": "GET"}
    )
    direct_vm.mock_web(
        r".*api2\.example\.com/eth.*",
        {"response": {"status": 200, "headers": {}, "body": json.dumps({"spot": 3451.20}).encode("utf-8")}, "method": "GET"}
    )
    direct_vm.mock_web(
        r".*api3\.example\.com/eth.*",
        {"response": {"status": 200, "headers": {}, "body": json.dumps({"last": 3449.80}).encode("utf-8")}, "method": "GET"}
    )

    # Mock LLM output extracting and synthesizing median price
    direct_vm.mock_llm(
        json.dumps({
            "value_numeric": 3450.33,
            "confidence_bps": 9800,
            "outliers_count": 0,
            "summary": "Synthesized 3 consistent prices within 0.04% variance.",
        })
    )

    contract.refresh_feed("ETH_PRICE")

    latest = contract.get_latest_data("ETH_PRICE")
    assert latest["is_initialized"] is True
    assert latest["feed_id"] == "ETH_PRICE"
    assert latest["value_scaled"] == 345033  # 3450.33 with decimals=2
    assert latest["decimals"] == 2
    assert latest["confidence_bps"] == 9800
    assert latest["sources_successful"] == 3
    assert latest["sources_failed"] == 0
    assert latest["outliers_detected"] == 0
    assert latest["status"] == "OK"


def test_refresh_feed_outlier_rejection(direct_vm, direct_deploy, direct_alice):
    """Test multi-source synthesis rejecting an outlier/corrupted endpoint."""
    contract = direct_deploy("contracts/multi_source_synthesizer.py")
    direct_vm.sender = direct_alice

    sources = [
        "https://api1.example.com/btc",
        "https://api2.example.com/btc",
        "https://api3.example.com/btc",
    ]

    contract.register_feed(
        feed_id="BTC_PRICE",
        name="BTC Price Feed",
        feed_type="NUMERIC",
        query_prompt="Extract BTC/USD spot price.",
        sources=sources,
        tolerance_bps=100,
        min_sources_required=2,
        heartbeat_seconds=300,
    )

    # Sources 1 and 2 agree on ~$65,000; source 3 returns anomalous $999,999
    direct_vm.mock_web(
        r".*api1\.example\.com/btc.*",
        {"response": {"status": 200, "headers": {}, "body": json.dumps({"price": 65000.0}).encode("utf-8")}, "method": "GET"}
    )
    direct_vm.mock_web(
        r".*api2\.example\.com/btc.*",
        {"response": {"status": 200, "headers": {}, "body": json.dumps({"price": 65050.0}).encode("utf-8")}, "method": "GET"}
    )
    direct_vm.mock_web(
        r".*api3\.example\.com/btc.*",
        {"response": {"status": 200, "headers": {}, "body": json.dumps({"price": 999999.0}).encode("utf-8")}, "method": "GET"}
    )

    # LLM rejects source 3 as outlier and calculates consensus from sources 1 & 2
    direct_vm.mock_llm(
        json.dumps({
            "value_numeric": 65025.0,
            "confidence_bps": 9200,
            "outliers_count": 1,
            "summary": "Source 3 (999999.0) rejected as extreme outlier. Sources 1 and 2 agree.",
        })
    )

    contract.refresh_feed("BTC_PRICE")

    latest = contract.get_latest_data("BTC_PRICE")
    assert latest["value_scaled"] == 6502500
    assert latest["outliers_detected"] == 1
    assert latest["status"] == "OK"


def test_refresh_feed_categorical_consensus(direct_vm, direct_deploy, direct_alice):
    """Test multi-source consensus on categorical / real-world event facts."""
    contract = direct_deploy("contracts/multi_source_synthesizer.py")
    direct_vm.sender = direct_alice

    sources = [
        "https://sports1.example.com/match/101",
        "https://sports2.example.com/match/101",
    ]

    contract.register_feed(
        feed_id="CHAMPIONSHIP_FINAL",
        name="Championship Final Winner",
        feed_type="CATEGORICAL",
        query_prompt="Determine the winning team of match 101.",
        sources=sources,
        tolerance_bps=0,
        min_sources_required=2,
        heartbeat_seconds=300,
    )

    direct_vm.mock_web(
        r".*sports1\.example\.com.*",
        {"response": {"status": 200, "headers": {}, "body": json.dumps({"winner": "Lions", "score": "24-17"}).encode("utf-8")}, "method": "GET"}
    )
    direct_vm.mock_web(
        r".*sports2\.example\.com.*",
        {"response": {"status": 200, "headers": {}, "body": json.dumps({"result": "Lions victory over Tigers"}).encode("utf-8")}, "method": "GET"}
    )

    direct_vm.mock_llm(
        json.dumps({
            "value_categorical": "LIONS_WON",
            "confidence_bps": 9900,
            "outliers_count": 0,
            "summary": "Both sports feeds confirm Lions victory.",
        })
    )

    contract.refresh_feed("CHAMPIONSHIP_FINAL")

    latest = contract.get_latest_data("CHAMPIONSHIP_FINAL")
    assert latest["value_str"] == "LIONS_WON"
    assert latest["value_scaled"] == 0
    assert latest["confidence_bps"] == 9900
    assert latest["status"] == "OK"


def test_degraded_status_on_low_confidence(direct_vm, direct_deploy, direct_alice):
    """Test that degraded status is assigned when sources fail or confidence is low."""
    contract = direct_deploy("contracts/multi_source_synthesizer.py")
    direct_vm.sender = direct_alice

    sources = [
        "https://api1.example.com/failing",
        "https://api2.example.com/failing",
    ]

    contract.register_feed(
        feed_id="FLAKY_FEED",
        name="Flaky Feed",
        feed_type="NUMERIC",
        query_prompt="Extract metric value.",
        sources=sources,
        tolerance_bps=100,
        min_sources_required=2,
        heartbeat_seconds=300,
    )

    # Both endpoints return 500 server errors
    direct_vm.mock_web(
        r".*api1\.example\.com.*",
        {"response": {"status": 500, "headers": {}, "body": b"Internal Error"}, "method": "GET"}
    )
    direct_vm.mock_web(
        r".*api2\.example\.com.*",
        {"response": {"status": 502, "headers": {}, "body": b"Bad Gateway"}, "method": "GET"}
    )

    direct_vm.mock_llm(
        json.dumps({
            "value_numeric": 0.0,
            "confidence_bps": 1000,
            "outliers_count": 0,
            "summary": "All endpoints failed with HTTP errors.",
        })
    )

    contract.refresh_feed("FLAKY_FEED")

    latest = contract.get_latest_data("FLAKY_FEED")
    assert latest["status"] == "DEGRADED"
    assert latest["confidence_bps"] == 1000
    assert latest["sources_successful"] == 0
    assert latest["sources_failed"] == 2
