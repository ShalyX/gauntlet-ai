# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from dataclasses import dataclass
from genlayer import *

ERROR_EXPECTED = "[EXPECTED]"
MIN_REQUIRED_CONFIDENCE_BPS = 8_000  # 80% confidence required for high-value actions


@allow_storage
@dataclass
class SettlementRecord:
    feed_id: str
    settled_value: str
    confidence_bps: u256
    settled_at: str


class SynthesizerConsumer(gl.Contract):
    """
    SynthesizerConsumer: Example Consumer Contract
    
    Demonstrates how external GenLayer protocols (prediction markets, DeFi vaults,
    parametric insurance) consume MultiSourceSynthesizer via cross-contract calls.
    """
    synthesizer_address: Address
    owner: Address
    settlements: TreeMap[str, SettlementRecord]

    def __init__(self, synthesizer_address: Address):
        self.synthesizer_address = synthesizer_address
        self.owner = gl.message.sender_address

    @gl.public.write
    def settle_market(self, market_id: str, feed_id: str) -> str:
        """
        Settle a conditional market or trigger payout based on multi-source verified data.
        Enforces confidence and freshness thresholds.
        """
        # 1. Connect to the deployed MultiSourceSynthesizer contract
        synthesizer = gl.get_contract(self.synthesizer_address)

        # 2. Query the latest synthesized data via gasless cross-contract view
        data = synthesizer.get_latest_data(feed_id)

        # 3. Defensive checks on the synthesized data
        if not data.get("is_initialized", False):
            raise Exception(f"{ERROR_EXPECTED} feed '{feed_id}' has not been initialized")

        if data.get("status") != "OK":
            raise Exception(
                f"{ERROR_EXPECTED} feed '{feed_id}' status is '{data.get('status')}', expected 'OK'"
            )

        confidence = data.get("confidence_bps", 0)
        if confidence < MIN_REQUIRED_CONFIDENCE_BPS:
            raise Exception(
                f"{ERROR_EXPECTED} confidence {confidence} BPS below threshold {MIN_REQUIRED_CONFIDENCE_BPS} BPS"
            )

        settled_val = str(data.get("value_str", ""))
        self.settlements[market_id] = SettlementRecord(
            feed_id=feed_id,
            settled_value=settled_val,
            confidence_bps=u256(confidence),
            settled_at=str(gl.message.timestamp),
        )

        return settled_val

    @gl.public.view
    def get_settlement(self, market_id: str) -> dict:
        """Return the settled record for a market."""
        if market_id not in self.settlements:
            return {}
        s = self.settlements[market_id]
        return {
            "market_id": market_id,
            "feed_id": s.feed_id,
            "settled_value": s.settled_value,
            "confidence_bps": int(s.confidence_bps),
            "settled_at": s.settled_at,
        }
