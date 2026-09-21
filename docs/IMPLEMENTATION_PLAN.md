# Implementation Plan: Model C Decentralized Slashing, Native Directory Enumeration & Collateral Bonds

This plan details the architectural transition of `GauntletAI` to **Model C** (Hybrid Autonomous Slashing with Native Appeals), re-enables economic collateral bonds (`MIN_STAKE_WEI > 0`), and introduces native on-chain agent directory enumeration (`get_all_agents`).

---

## User Review Required

> [!IMPORTANT]
> **Economic Parameters & Bounty Sizing:**
> - `MIN_STAKE_WEI = 10_000_000_000_000_000` (0.01 GEN): Required collateral bond locked upon agent registration.
> - `CHALLENGE_BOND_WEI = 5_000_000_000_000_000` (0.005 GEN): Required bond posted by a challenger to initiate a dispute.
> - `APPEAL_BOND_WEI = 10_000_000_000_000_000` (0.010 GEN): 2x bond posted by the agent owner to appeal a provisional slash.
> - **Bounty Split on Final Slash:** 30% of the agent's staked collateral (0.003 GEN) is awarded to the challenger, 70% (0.007 GEN) is burned/locked.
> - **Appeal Window:** 24 hours (86,400 seconds) from provisional freeze.

> [!NOTE]
> **Native On-Chain Enumeration:**
> Replaces all frontend candidate arrays (`CANDIDATE_AGENT_IDS`) and `localStorage` with an on-chain `registered_agent_ids: DynArray[str]` and `@gl.public.view def get_all_agents() -> list[dict]`.

---

## Proposed Changes

### 1. Smart Contract Core (`contracts/`)

#### [MODIFY] [`contracts/gauntlet_ai.py`](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/contracts/gauntlet_ai.py)
- **Economic Constants:**
  - `MIN_STAKE_WEI = 10_000_000_000_000_000` (0.01 GEN)
  - `CHALLENGE_BOND_WEI = 5_000_000_000_000_000` (0.005 GEN)
  - `APPEAL_BOND_WEI = 10_000_000_000_000_000` (0.010 GEN)
  - `APPEAL_WINDOW_SECONDS = 86_400` (24 hours)
  - `BOUNTY_BPS = 3_000` (30% to challenger)
- **Status Constants:**
  - `STATUS_ACTIVE = "ACTIVE"`
  - `STATUS_FROZEN = "FROZEN"` (Provisional slash, licenses suspended)
  - `STATUS_SLASHED = "SLASHED"` (Permanently burned)
- **New Dataclass & Storage:**
  - `DisputeRecord`: `dispute_id`, `agent_id`, `track_id`, `challenger: Address`, `challenger_bond: u256`, `status: str`, `created_at: str`, `appeal_deadline: int`, `appeal_bond: u256`.
  - `registered_agent_ids: DynArray[str]`
  - `disputes: TreeMap[str, DisputeRecord]`
  - `next_dispute_id: int`
- **Method Modifications:**
  - `register_agent(agent_id, name, endpoint_url)`:
    - Enforce `gl.message.value >= MIN_STAKE_WEI`.
    - Append `agent_id` to `self.registered_agent_ids`.
  - `is_certified(agent_id, track_id) -> bool`:
    - Return `False` if agent status is `FROZEN` or `SLASHED` (immediate cross-contract protection).
- **New Public Write Methods (Model C):**
  - `submit_dispute(agent_id, track_id) -> dict`:
    - Permissionless caller deposits `CHALLENGE_BOND_WEI`.
    - Runs `gl.vm.run_nondet_unsafe` consensus probe.
    - If agent fails: agent status $\rightarrow$ `FROZEN`, licenses suspended, 24h appeal window starts.
    - If agent passes: challenger bond forfeited to agent owner or burned.
  - `appeal_dispute(dispute_id: str) -> dict`:
    - Callable strictly by `agent.owner` within `appeal_deadline`.
    - Requires `APPEAL_BOND_WEI`.
    - Executes full re-probe. If agent passes, restores `ACTIVE` status and refunds appeal bond + awards challenger bond.
  - `finalize_dispute(dispute_id: str) -> None`:
    - Permissionless settlement if appeal window expires without appeal.
    - Permanently sets `STATUS_SLASHED`, transfers 30% bounty to challenger, burns 70%.
- **New Public View Methods:**
  - `get_all_agents() -> list[dict]`:
    - Iterates over `registered_agent_ids` and returns complete profiles, stakes, statuses, and active licenses.
  - `get_dispute(dispute_id: str) -> dict`:
    - Returns dispute details and live appeal timer.

---

### 2. Frontend Application (`frontend/`)

#### [MODIFY] [`frontend/app.js`](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/frontend/app.js)
- **Purge Candidate List & LocalStorage:**
  - Remove `CANDIDATE_AGENT_IDS` and `localStorage` reading.
  - Implement `hydrateOnChainState()` using direct `get_all_agents()` contract call.
- **Model C Dispute & Appeal Handlers:**
  - Replace "Admin Mode" toggle with permissionless `[ Challenge / Dispute ]` action.
  - Implement `openDisputeModal(agentId)`:
    - Calculates challenge bond (`0.005 GEN`) and prospective bounty (`0.003 GEN`).
    - Dispatches `submit_dispute` transaction with required value.
  - Implement `openAppealModal(disputeId)`:
    - Checks if `account === agent.owner`.
    - Dispatches `appeal_dispute` with `0.010 GEN` appeal bond.
  - Implement `handleFinalizeDispute(disputeId)`:
    - Dispatches `finalize_dispute` once the 24h timer expires.

#### [MODIFY] [`frontend/index.html`](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/frontend/index.html)
- **Verified Directory Table:**
  - Remove "ADMIN MODE" toggle switch.
  - Add `• FROZEN (Appeal Active)` amber status pill styling.
  - Table action button dynamically renders:
    - `[ Challenge ]` for active agents.
    - `[ Appeal (Owner) ]` for frozen agents when connected wallet is the owner.
    - `[ Finalize Slash ]` when appeal deadline has passed.
- **Dispute Modal (`#disputeModal`):**
  - Displays attack vector, challenge bond requirement, and potential 30% bounty reward.
- **Appeal Drawer / Modal (`#appealModal`):**
  - Countdown timer showing remaining hours/minutes in the appeal window.

---

### 3. Automated Test Suite (`tests/`)

#### [MODIFY] [`tests/direct/test_gauntlet_ai.py`](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/tests/direct/test_gauntlet_ai.py)
- `test_registration_requires_min_stake`: Verifies registration reverts if `value < MIN_STAKE_WEI`.
- `test_get_all_agents_enumeration`: Verifies `registered_agent_ids` populates and returns full list.
- `test_submit_dispute_provisional_freeze`: Verifies failed challenge sets `FROZEN` and suspends `is_certified()`.
- `test_appeal_dispute_success_restores_license`: Verifies owner appeal with bond clears dispute.
- `test_finalize_dispute_pays_bounty_and_burns`: Verifies expired appeal pays 30% bounty to challenger and sets `SLASHED`.

#### [MODIFY] [`tests/integration/test_e2e_gauntlet.py`](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/tests/integration/test_e2e_gauntlet.py)
- End-to-end integration test simulating the entire Model C dispute, freeze, appeal, and finalization lifecycle.

---

## Verification Plan

### Automated Tests
1. Direct Unit Tests:
   ```bash
   python -m pytest tests/direct/ -v
   ```
2. Integration Lifecycle Tests:
   ```bash
   python -m pytest tests/integration/ -v
   ```

### Live On-Chain Verification on StudioNet
1. Deploy updated contract to StudioNet via `genlayer deploy --contract contracts/gauntlet_ai.py`.
2. Register an agent with `0.01 GEN` stake.
3. Submit a live dispute via `submit_dispute` with `0.005 GEN` bond.
4. Verify validator consensus, provisional freeze, and license suspension.
5. Verify `get_all_agents()` returns all registered agents in single call.
6. Verify in browser UI that table reflects `• FROZEN` and renders the countdown.
