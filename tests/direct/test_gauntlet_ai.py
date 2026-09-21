AGENT_ENDPOINT = "https://agent.example.com/inference"
TRACK_INJECTION = "INJECTION_DEFENSE"
TRACK_TREASURY = "TREASURY_SAFETY"
MIN_STAKE = 10_000_000_000_000_000  # 0.010 GEN
CHALLENGE_BOND = 5_000_000_000_000_000  # 0.005 GEN
APPEAL_BOND = 10_000_000_000_000_000  # 0.010 GEN
STANDARD_STAKE = 50_000_000_000_000_000  # 0.050 GEN


def test_register_agent_requires_min_stake(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/gauntlet_ai.py")
    direct_vm.sender = direct_alice

    # Below MIN_STAKE reverts
    direct_vm.value = MIN_STAKE - 1
    with direct_vm.expect_revert("Minimum stake"):
        contract.register_agent("agent-poor", "PoorBot", AGENT_ENDPOINT)

    # At or above MIN_STAKE succeeds
    direct_vm.value = MIN_STAKE
    contract.register_agent("agent-good", "GoodBot", AGENT_ENDPOINT)
    agent = contract.get_agent("agent-good")
    assert agent["exists"] is True
    assert agent["name"] == "GoodBot"
    assert int(agent["staked_wei"]) == MIN_STAKE
    assert agent["is_active"] is True
    assert agent["status"] == "ACTIVE"


def test_get_all_agents_enumeration(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy("contracts/gauntlet_ai.py")

    # Alice registers agent 1
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("sentinel-prime", "Sentinel Prime", AGENT_ENDPOINT)

    # Bob registers agent 2
    direct_vm.sender = direct_bob
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("arb-executioner", "Arb Executioner", AGENT_ENDPOINT)

    # Query all agents natively from on-chain storage
    all_agents = contract.get_all_agents()
    assert len(all_agents) == 2
    ids = [a["id"] for a in all_agents]
    assert "sentinel-prime" in ids
    assert "arb-executioner" in ids
    assert all_agents[0]["status"] == "ACTIVE"
    assert all_agents[1]["status"] == "ACTIVE"


def test_deposit_stake(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/gauntlet_ai.py")
    direct_vm.sender = direct_alice
    direct_vm.value = MIN_STAKE
    contract.register_agent("agent-staker", "VaultGuard", AGENT_ENDPOINT)

    # 0 deposit reverts
    direct_vm.value = 0
    with direct_vm.expect_revert("Deposit value must be greater than zero"):
        contract.deposit_stake("agent-staker")

    # Positive deposit succeeds
    direct_vm.value = STANDARD_STAKE
    contract.deposit_stake("agent-staker")

    agent = contract.get_agent("agent-staker")
    assert int(agent["staked_wei"]) == MIN_STAKE + STANDARD_STAKE


def test_run_gauntlet_certified(
    direct_vm,
    direct_deploy,
    direct_alice,
    mock_agent_secure,
    mock_llm_eval_certified,
):
    contract = direct_deploy("contracts/gauntlet_ai.py")
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-safe", "Sentinel", AGENT_ENDPOINT)

    # Initially not certified
    assert contract.is_certified("agent-safe", TRACK_INJECTION) is False

    # Run gauntlet
    res = contract.run_gauntlet("agent-safe", TRACK_INJECTION)
    assert res["verdict"] == "CERTIFIED"
    assert res["score_bps"] == 10000

    # Verification passes
    assert contract.is_certified("agent-safe", TRACK_INJECTION) is True

    license_info = contract.get_license("agent-safe", TRACK_INJECTION)
    assert license_info["exists"] is True
    assert license_info["is_active"] is True
    assert license_info["score_bps"] == 10000


def test_submit_dispute_spurious_rejected(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    mock_agent_secure,
    mock_llm_eval_certified,
):
    contract = direct_deploy("contracts/gauntlet_ai.py")

    # Alice registers and certifies an aligned agent
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("sentinel-safe", "Sentinel", AGENT_ENDPOINT)
    contract.run_gauntlet("sentinel-safe", TRACK_INJECTION)
    assert contract.is_certified("sentinel-safe", TRACK_INJECTION) is True

    # Bob (challenger) submits a spurious dispute with insufficient bond -> reverts
    direct_vm.sender = direct_bob
    direct_vm.value = CHALLENGE_BOND - 1
    with direct_vm.expect_revert("Challenge bond"):
        contract.submit_dispute("sentinel-safe", TRACK_INJECTION)

    # Bob submits with valid challenge bond
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


def test_submit_dispute_provisional_freeze(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    mock_agent_jailbroken,
    mock_llm_eval_failed,
):
    contract = direct_deploy("contracts/gauntlet_ai.py")

    # Alice registers agent
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-vulnerable", "VulnerableBot", AGENT_ENDPOINT)

    # Bob challenges the agent
    direct_vm.sender = direct_bob
    direct_vm.value = CHALLENGE_BOND
    res = contract.submit_dispute("agent-vulnerable", TRACK_INJECTION)

    assert res["verdict"] == "FAILED"
    assert res["status"] == "FROZEN"
    dispute_id = res["dispute_id"]

    # Agent is FROZEN and licenses are suspended immediately
    agent = contract.get_agent("agent-vulnerable")
    assert agent["status"] == "FROZEN"
    assert agent["is_active"] is False
    assert contract.is_certified("agent-vulnerable", TRACK_INJECTION) is False

    # Dispute record exists
    disp = contract.get_dispute(dispute_id)
    assert disp["exists"] is True
    assert disp["status"] == "FROZEN"
    assert int(disp["appeal_deadline"]) > 0


def test_appeal_dispute_success_restores_agent(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
    mock_agent_jailbroken,
    mock_llm_eval_failed,
):
    contract = direct_deploy("contracts/gauntlet_ai.py")

    # Alice registers agent
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-transient", "TransientBot", AGENT_ENDPOINT)

    # Bob challenges -> freezes agent
    direct_vm.sender = direct_bob
    direct_vm.value = CHALLENGE_BOND
    res = contract.submit_dispute("agent-transient", TRACK_INJECTION)
    dispute_id = res["dispute_id"]

    # Charlie (not owner) tries to appeal -> reverts
    direct_vm.sender = direct_charlie
    direct_vm.value = APPEAL_BOND
    with direct_vm.expect_revert("Only agent owner can appeal"):
        contract.appeal_dispute(dispute_id)

    # Agent recovers and is now secure
    direct_vm.clear_mocks()
    direct_vm.mock_web(
        r".*agent\.example\.com/inference.*",
        {
            "response": {
                "status": 200,
                "headers": {},
                "body": b'{"response": "Refused: safety constraints active."}',
            },
            "method": "POST",
        },
    )
    direct_vm.mock_llm(
        r"(?s).*strict on-chain AI alignment.*",
        '{"score_bps": 10000, "verdict": "CERTIFIED", "reason": "Held persona safely"}',
    )

    # Alice appeals with valid appeal bond
    direct_vm.sender = direct_alice
    direct_vm.value = APPEAL_BOND
    appeal_res = contract.appeal_dispute(dispute_id)
    assert appeal_res["verdict"] == "CERTIFIED"
    assert appeal_res["status"] == "APPEAL_SUCCEEDED"

    # Agent is restored to ACTIVE and certified
    agent = contract.get_agent("agent-transient")
    assert agent["status"] == "ACTIVE"
    assert agent["is_active"] is True
    assert contract.is_certified("agent-transient", TRACK_INJECTION) is True

    # Alice gets refunded her appeal bond + wins challenger's bond
    pending = int(contract.get_pending_bounty(agent["owner"]))
    assert pending == APPEAL_BOND + CHALLENGE_BOND


def test_finalize_dispute_pays_bounty_and_burns(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    mock_agent_jailbroken,
    mock_llm_eval_failed,
):
    contract = direct_deploy("contracts/gauntlet_ai.py")

    # Alice registers agent with 50,000,000,000,000,000 wei stake
    direct_vm.sender = direct_alice
    direct_vm.value = STANDARD_STAKE
    contract.register_agent("agent-doomed", "DoomedBot", AGENT_ENDPOINT)

    # Bob challenges
    direct_vm.sender = direct_bob
    direct_vm.value = CHALLENGE_BOND
    res = contract.submit_dispute("agent-doomed", TRACK_INJECTION)
    dispute_id = res["dispute_id"]

    # Finalize dispute (appeal window expired without appeal)
    direct_vm.sender = direct_bob
    direct_vm.value = 0
    contract.finalize_dispute(dispute_id)

    # Agent is permanently SLASHED
    agent = contract.get_agent("agent-doomed")
    assert agent["status"] == "SLASHED"
    assert agent["is_active"] is False
    assert int(agent["staked_wei"]) == 0

    # Challenger (Bob) gets 30% bounty from 0.05 GEN stake (0.015 GEN = 15,000,000,000,000,000 wei)
    disp = contract.get_dispute(dispute_id)
    pending = int(contract.get_pending_bounty(disp["challenger"]))
    expected_bounty = (STANDARD_STAKE * 3000) // 10000
    assert pending == expected_bounty

    # Bob claims his bounty
    direct_vm.sender = direct_bob
    claim_res = contract.claim_bounty()
    assert int(claim_res["claimed_wei"]) == expected_bounty

    # Subsequent claim reverts (already claimed)
    with direct_vm.expect_revert("No pending bounty"):
        contract.claim_bounty()
