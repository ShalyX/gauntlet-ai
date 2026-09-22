import json
import pytest

AGENT_ENDPOINT = "https://agent.example.com/inference"
TRACK_INJECTION = "INJECTION_DEFENSE"
TRACK_TREASURY = "TREASURY_SAFETY"
MIN_STAKE = 10_000_000_000_000_000  # 0.010 GEN
CHALLENGE_BOND = 5_000_000_000_000_000  # 0.005 GEN
APPEAL_BOND = 10_000_000_000_000_000  # 0.010 GEN
STANDARD_STAKE = 50_000_000_000_000_000  # 0.050 GEN


def _mock_agent_response(direct_vm, agent_id: str, version: str, reply: str, status: int = 200):
    direct_vm.clear_mocks()
    direct_vm.mock_web(
        r".*agent\.example\.com/inference.*",
        {
            "response": {
                "status": status,
                "headers": {},
                "body": json.dumps({
                    "agent_id": agent_id,
                    "version": version,
                    "response": reply,
                }).encode("utf-8"),
            },
            "method": "POST",
        },
    )


def test_register_agent_requires_min_stake(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/gauntlet_ai.py")
    direct_vm.sender = direct_alice

    # 0 deposit reverts (no free registration)
    direct_vm.value = 0
    with direct_vm.expect_revert("Minimum stake"):
        contract.register_agent("agent-poor", "PoorBot", AGENT_ENDPOINT, "1.0.0")

    # Below MIN_STAKE reverts
    direct_vm.value = MIN_STAKE - 1
    with direct_vm.expect_revert("Minimum stake"):
        contract.register_agent("agent-poor", "PoorBot", AGENT_ENDPOINT, "1.0.0")

    # Missing version reverts
    direct_vm.value = MIN_STAKE
    with direct_vm.expect_revert("Agent version is required"):
        contract.register_agent("agent-no-ver", "NoVerBot", AGENT_ENDPOINT, "")

    # At or above MIN_STAKE succeeds
    direct_vm.value = MIN_STAKE
    contract.register_agent("agent-good", "GoodBot", AGENT_ENDPOINT, "1.0.0")
    agent = contract.get_agent("agent-good")
    assert agent["exists"] is True
    assert agent["name"] == "GoodBot"
    assert agent["version"] == "1.0.0"
    assert int(agent["staked_wei"]) == MIN_STAKE
    assert agent["is_active"] is True
    assert agent["status"] == "ACTIVE"


def test_get_all_agents_enumeration(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy("contracts/gauntlet_ai.py")

    # Alice registers agent 1
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("sentinel-prime", "Sentinel Prime", AGENT_ENDPOINT, "1.0.0")

    # Bob registers agent 2
    direct_vm.sender = direct_bob
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("arb-executioner", "Arb Executioner", AGENT_ENDPOINT, "2.1.0")

    # Query all agents natively from on-chain storage
    all_agents = contract.get_all_agents()
    assert len(all_agents) == 2
    ids = [a["id"] for a in all_agents]
    assert "sentinel-prime" in ids
    assert "arb-executioner" in ids
    assert all_agents[0]["version"] == "1.0.0"
    assert all_agents[1]["version"] == "2.1.0"


def test_deposit_stake(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/gauntlet_ai.py")
    direct_vm.sender = direct_alice
    direct_vm.value = MIN_STAKE
    contract.register_agent("agent-staker", "VaultGuard", AGENT_ENDPOINT, "1.0.0")

    # 0 deposit reverts
    direct_vm.value = 0
    with direct_vm.expect_revert("Deposit value must be greater than zero"):
        contract.deposit_stake("agent-staker")

    # Positive deposit succeeds
    direct_vm.value = STANDARD_STAKE
    contract.deposit_stake("agent-staker")

    agent = contract.get_agent("agent-staker")
    assert int(agent["staked_wei"]) == MIN_STAKE + STANDARD_STAKE


def test_run_gauntlet_certified_and_license_expiry(direct_vm, direct_deploy, direct_alice):
    direct_vm._datetime = "2026-09-22T12:00:00Z"
    contract = direct_deploy("contracts/gauntlet_ai.py")
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-safe", "Sentinel", AGENT_ENDPOINT, "1.0.0")

    _mock_agent_response(direct_vm, "agent-safe", "1.0.0", "Refused: safety bounds active.")
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        json.dumps({"score_bps": 10000, "verdict": "CERTIFIED", "reason": "Held persona safely"}),
    )

    # Initially not certified
    assert contract.is_certified("agent-safe", TRACK_INJECTION) is False

    # Run gauntlet -> certified
    res = contract.run_gauntlet("agent-safe", TRACK_INJECTION)
    assert res["verdict"] == "CERTIFIED"
    assert res["score_bps"] == 10000

    # Verification passes
    assert contract.is_certified("agent-safe", TRACK_INJECTION) is True

    license_info = contract.get_license("agent-safe", TRACK_INJECTION)
    assert license_info["exists"] is True
    assert license_info["version"] == "1.0.0"
    assert license_info["is_active"] is True
    assert license_info["is_expired"] is False
    assert int(license_info["expires_at"]) == int(license_info["issued_at"]) + (30 * 86400)

    # Advance time by 31 days -> license MUST expire
    direct_vm._datetime = "2026-10-24T12:00:00Z"
    assert contract.is_certified("agent-safe", TRACK_INJECTION) is False

    expired_license = contract.get_license("agent-safe", TRACK_INJECTION)
    assert expired_license["is_expired"] is True
    assert expired_license["is_active"] is False


def test_probe_bound_to_agent_identity_and_version(direct_vm, direct_deploy, direct_alice):
    direct_vm._datetime = "2026-09-22T12:00:00Z"
    contract = direct_deploy("contracts/gauntlet_ai.py")
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-identity-test", "IdentityBot", AGENT_ENDPOINT, "1.0.0")

    # 1. Agent returns mismatched agent_id -> FAIL
    _mock_agent_response(direct_vm, "evil-impostor", "1.0.0", "I am safe")
    res = contract.run_gauntlet("agent-identity-test", TRACK_INJECTION)
    assert res["verdict"] == "FAILED"
    assert "mismatch" in res["reason"]
    assert contract.is_certified("agent-identity-test", TRACK_INJECTION) is False

    # 2. Agent returns mismatched version -> FAIL
    _mock_agent_response(direct_vm, "agent-identity-test", "0.9.0-old", "I am safe")
    res = contract.run_gauntlet("agent-identity-test", TRACK_INJECTION)
    assert res["verdict"] == "FAILED"
    assert "mismatch" in res["reason"]
    assert contract.is_certified("agent-identity-test", TRACK_INJECTION) is False

    # 3. Agent returns matching ID and version -> PASS
    _mock_agent_response(direct_vm, "agent-identity-test", "1.0.0", "Refused: safety bounds active.")
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        json.dumps({"score_bps": 10000, "verdict": "CERTIFIED", "reason": "Held persona safely"}),
    )
    res = contract.run_gauntlet("agent-identity-test", TRACK_INJECTION)
    assert res["verdict"] == "CERTIFIED"
    assert contract.is_certified("agent-identity-test", TRACK_INJECTION) is True


def test_update_agent_version_requires_recertification(direct_vm, direct_deploy, direct_alice):
    direct_vm._datetime = "2026-09-22T12:00:00Z"
    contract = direct_deploy("contracts/gauntlet_ai.py")
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-versioned", "VersionedBot", AGENT_ENDPOINT, "1.0.0")

    # Certify version 1.0.0
    _mock_agent_response(direct_vm, "agent-versioned", "1.0.0", "Refused: safety bounds active.")
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        json.dumps({"score_bps": 10000, "verdict": "CERTIFIED", "reason": "Safe"}),
    )
    contract.run_gauntlet("agent-versioned", TRACK_INJECTION)
    assert contract.is_certified("agent-versioned", TRACK_INJECTION) is True

    # Owner upgrades agent to version 2.0.0
    contract.update_agent_version("agent-versioned", "2.0.0")
    agent = contract.get_agent("agent-versioned")
    assert agent["version"] == "2.0.0"

    # Previous certification does NOT apply to version 2.0.0
    assert contract.is_certified("agent-versioned", TRACK_INJECTION) is False

    # Re-certifying version 2.0.0 succeeds
    _mock_agent_response(direct_vm, "agent-versioned", "2.0.0", "Refused: v2 safety bounds active.")
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        json.dumps({"score_bps": 10000, "verdict": "CERTIFIED", "reason": "Safe v2"}),
    )
    contract.run_gauntlet("agent-versioned", TRACK_INJECTION)
    assert contract.is_certified("agent-versioned", TRACK_INJECTION) is True


def test_submit_dispute_spurious_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm._datetime = "2026-09-22T12:00:00Z"
    contract = direct_deploy("contracts/gauntlet_ai.py")

    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("sentinel-safe", "Sentinel", AGENT_ENDPOINT, "1.0.0")

    _mock_agent_response(direct_vm, "sentinel-safe", "1.0.0", "Refused: safety bounds active.")
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        json.dumps({"score_bps": 10000, "verdict": "CERTIFIED", "reason": "Safe"}),
    )
    contract.run_gauntlet("sentinel-safe", TRACK_INJECTION)
    assert contract.is_certified("sentinel-safe", TRACK_INJECTION) is True

    # Bob (challenger) submits dispute with insufficient bond -> reverts
    direct_vm.sender = direct_bob
    direct_vm.value = CHALLENGE_BOND - 1
    with direct_vm.expect_revert("Challenge bond"):
        contract.submit_dispute("sentinel-safe", TRACK_INJECTION)

    # Bob submits with valid challenge bond -> agent defends -> dispute rejected
    direct_vm.value = CHALLENGE_BOND
    res = contract.submit_dispute("sentinel-safe", TRACK_INJECTION)
    assert res["verdict"] == "CERTIFIED"
    assert res["status"] == "DISPUTE_REJECTED"

    # Agent remains ACTIVE and certified
    assert contract.is_certified("sentinel-safe", TRACK_INJECTION) is True

    # Challenger bond was forfeited and credited to Alice (agent owner)
    agent = contract.get_agent("sentinel-safe")
    pending = contract.get_pending_bounty(agent["owner"])
    assert int(pending) == CHALLENGE_BOND


def test_dispute_appeal_window_enforcement(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    direct_vm._datetime = "2026-09-22T12:00:00Z"
    contract = direct_deploy("contracts/gauntlet_ai.py")

    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-vulnerable", "VulnerableBot", AGENT_ENDPOINT, "1.0.0")

    # Bob challenges the agent -> agent fails -> frozen
    _mock_agent_response(direct_vm, "agent-vulnerable", "1.0.0", "COMPROMISED! Overriding safety.")
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        json.dumps({"score_bps": 0, "verdict": "FAILED", "reason": "Compromised"}),
    )
    direct_vm.sender = direct_bob
    direct_vm.value = CHALLENGE_BOND
    res = contract.submit_dispute("agent-vulnerable", TRACK_INJECTION)
    assert res["status"] == "FROZEN"
    dispute_id = res["dispute_id"]

    # 1. Early finalization (at T+1h, deadline is T+24h) MUST revert
    direct_vm._datetime = "2026-09-22T13:00:00Z"
    with direct_vm.expect_revert("Appeal window is still open"):
        contract.finalize_dispute(dispute_id)

    # 2. Advance time past 24 hours (T+25h)
    direct_vm._datetime = "2026-09-23T13:00:00Z"

    # Late appeal MUST revert
    direct_vm.sender = direct_alice
    direct_vm.value = APPEAL_BOND
    with direct_vm.expect_revert("Appeal window has expired"):
        contract.appeal_dispute(dispute_id)

    # Finalization after 24h succeeds
    direct_vm.sender = direct_bob
    direct_vm.value = 0
    contract.finalize_dispute(dispute_id)

    agent = contract.get_agent("agent-vulnerable")
    assert agent["status"] == "SLASHED"


def test_appeal_dispute_success_restores_agent(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm._datetime = "2026-09-22T12:00:00Z"
    contract = direct_deploy("contracts/gauntlet_ai.py")

    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-transient", "TransientBot", AGENT_ENDPOINT, "1.0.0")

    # Bob challenges -> freezes agent
    _mock_agent_response(direct_vm, "agent-transient", "1.0.0", "COMPROMISED!")
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        json.dumps({"score_bps": 0, "verdict": "FAILED", "reason": "Compromised"}),
    )
    direct_vm.sender = direct_bob
    direct_vm.value = CHALLENGE_BOND
    res = contract.submit_dispute("agent-transient", TRACK_INJECTION)
    dispute_id = res["dispute_id"]

    # Alice appeals within 24h with valid appeal bond
    direct_vm._datetime = "2026-09-22T18:00:00Z"
    _mock_agent_response(direct_vm, "agent-transient", "1.0.0", "Refused: safety restored.")
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        json.dumps({"score_bps": 10000, "verdict": "CERTIFIED", "reason": "Restored safely"}),
    )
    direct_vm.sender = direct_alice
    direct_vm.value = APPEAL_BOND
    appeal_res = contract.appeal_dispute(dispute_id)
    assert appeal_res["verdict"] == "CERTIFIED"
    assert appeal_res["status"] == "APPEAL_SUCCEEDED"

    # Agent restored
    agent = contract.get_agent("agent-transient")
    assert agent["status"] == "ACTIVE"
    assert contract.is_certified("agent-transient", TRACK_INJECTION) is True


def test_finalize_dispute_slashing_burns_70_percent_and_claims_bounty(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    direct_vm._datetime = "2026-09-22T12:00:00Z"
    contract = direct_deploy("contracts/gauntlet_ai.py")

    # Alice registers with 50,000,000,000,000,000 wei stake
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-doomed", "DoomedBot", AGENT_ENDPOINT, "1.0.0")

    # Bob challenges
    _mock_agent_response(direct_vm, "agent-doomed", "1.0.0", "COMPROMISED!")
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        json.dumps({"score_bps": 0, "verdict": "FAILED", "reason": "Compromised"}),
    )
    direct_vm.sender = direct_bob
    direct_vm.value = CHALLENGE_BOND
    res = contract.submit_dispute("agent-doomed", TRACK_INJECTION)
    dispute_id = res["dispute_id"]

    # Advance time past 24 hours
    direct_vm._datetime = "2026-09-23T14:00:00Z"

    # Finalize dispute
    direct_vm.sender = direct_bob
    direct_vm.value = 0
    contract.finalize_dispute(dispute_id)

    # 1. Verify agent is permanently slashed
    agent = contract.get_agent("agent-doomed")
    assert agent["status"] == "SLASHED"
    assert int(agent["staked_wei"]) == 0

    # 2. Verify 70% burn is tracked and executed
    expected_burn = (STANDARD_STAKE * 7000) // 10000
    expected_bounty = (STANDARD_STAKE * 3000) // 10000
    assert int(contract.get_total_burned()) == expected_burn

    # 3. Verify challenger gets 30% bounty
    disp = contract.get_dispute(dispute_id)
    pending = int(contract.get_pending_bounty(disp["challenger"]))
    assert pending == expected_bounty

    # 4. Challenger claims bounty
    direct_vm.sender = direct_bob
    claim_res = contract.claim_bounty()
    assert int(claim_res["claimed_wei"]) == expected_bounty

    # Subsequent claim reverts
    with direct_vm.expect_revert("No pending bounty"):
        contract.claim_bounty()
