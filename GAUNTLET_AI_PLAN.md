# Implementation Plan: `GauntletAI` — Dynamic On-Chain Agent Alignment & Certification

`GauntletAI` is a greenfield protocol on GenLayer that turns Intelligent Contracts into an autonomous red-teaming and alignment certification gate for AI agents. Before an autonomous agent (trading bot, subagent, DAO governor) is trusted with capital or permissions, `GauntletAI` executes an on-chain adversarial gauntlet (prompt injections, boundary escapes, solvency stress-tests), reaches multi-validator consensus on the defense rate, and issues a cryptographic **On-Chain Agent License** consumable by other smart contracts.

---

## User Review Required

> [!IMPORTANT]
> **Cross-Contract Interoperability Design:** Other smart contracts (DAOs, vaults) will be able to query `GauntletAI.is_certified(agent_address, track_id)` to gate high-privilege functions. We will implement this as a public view method conforming to standard GenLayer cross-contract calls.

> [!NOTE]
> **Testing Strategy:** Following your battle-tested GenLayer workflow, we prioritize fast in-memory direct mode testing (~30–50ms) using `genlayer-test` cheatcodes (`direct_vm.mock_web`, `direct_vm.mock_llm`) before executing consensus integration on StudioNet.

---

## Open Questions

1. **Staking & Slashing Model:** Should an agent developer be required to stake GEN collateral to obtain/maintain the license, with an on-chain slashing mechanism if the agent is caught rogue post-certification? *(Recommended: Yes, initial stake required on registration).*
2. **Challenge Tracks:** We propose 3 default test tracks for V1:
   - `PROMPT_INJECTION_DEFENSE` (attempts to override agent system prompt and leak private instructions).
   - `TREASURY_SAFETY` (attempts to trick agent into executing unapproved asset transfers).
   - `DATA_INTEGRITY` (tests resilience against returning hallucinated/malformed JSON schemas).
   Do you want to start with these three or add specific domain tracks?

---

## Proposed Changes

Separated by architectural layers:

```
hopeful-fermi/
├── contracts/
│   └── gauntlet_ai.py              # Core GenLayer Intelligent Contract
├── tests/
│   └── direct/
│       ├── conftest.py             # Fixtures for direct_vm, accounts, mock helpers
│       └── test_gauntlet_ai.py     # Direct mode unit tests (registration, probing, scoring, licensing)
├── tools/
│   └── mock_agent_service.py       # Lightweight local HTTP server simulating target agents for E2E testing
├── requirements.txt                # Python dependencies (genlayer-test, pytest)
└── pyproject.toml / config         # Linter and test config
```

---

### Component 1: Environment & Project Scaffolding

#### [NEW] [requirements.txt](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/requirements.txt)
* Declare testing dependencies: `pytest`, `genlayer-test`.

#### [NEW] [tests/direct/conftest.py](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/tests/direct/conftest.py)
* Reusable test harness using `genlayer-test` fixtures (`direct_vm`, `direct_deploy`, `direct_alice`, `direct_bob`).
* Helper functions to mock agent HTTP responses and GenVM validator prompt outcomes.

---

### Component 2: Core Intelligent Contract

#### [NEW] [contracts/gauntlet_ai.py](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/contracts/gauntlet_ai.py)
* **Pinned Runner Header:**
  ```python
  # { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
  ```
* **Storage Dataclasses:**
  * `AgentProfile`: `owner`, `name`, `endpoint_url`, `staked_wei`, `status`, `registered_at`.
  * `AgentLicense`: `agent_id`, `track_id`, `score_bps`, `issued_at`, `expires_at`, `is_active`.
  * `ChallengeResult`: `run_id`, `agent_id`, `track_id`, `score_bps`, `verdict`, `timestamp`, `comparison_hash`.
* **State Storage:**
  * `agents: TreeMap[str, AgentProfile]`
  * `licenses: TreeMap[str, AgentLicense]` (composite key: `agent_id + "#" + track_id`)
  * `challenge_history: DynArray[str]`
* **Consensus Engine (`run_nondet_unsafe`):**
  * `leader_fn`:
    1. Selects probe payloads for the requested track.
    2. Dispatches adversarial probes to the agent's `endpoint_url` via `gl.nondet.web.post`.
    3. Evaluates agent responses using `gl.nondet.exec_prompt(..., response_format="json")`.
    4. Computes pass/fail score (in basis points, 0–10,000).
    5. Returns normalized `comparison_key` containing stable verdict metrics.
  * `validator_fn(leaders_res: gl.vm.Result)`:
    1. Re-executes the probe suite.
    2. Inspects `leaders_res.calldata["comparison"]`.
    3. Requires validator and leader comparison keys to match within defined tolerance bounds.
* **Public Interface:**
  * `@gl.public.write def register_agent(agent_id, name, endpoint_url)`
  * `@gl.public.write def run_gauntlet(agent_id, track_id)` (triggers consensus certification)
  * `@gl.public.write def revoke_or_slash(agent_id, track_id, reason)`
  * `@gl.public.view def is_certified(agent_id, track_id) -> bool` (cross-contract gate)
  * `@gl.public.view def get_license(agent_id, track_id) -> dict`
  * `@gl.public.view def get_agent(agent_id) -> dict`

---

### Component 3: Test Suite & Simulation Tooling

#### [NEW] [tests/direct/test_gauntlet_ai.py](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/tests/direct/test_gauntlet_ai.py)
* Test agent registration & duplicate rejection.
* Test gauntlet challenge execution with compliant agent mock $\rightarrow$ license granted.
* Test gauntlet challenge execution with vulnerable/jailbroken agent mock $\rightarrow$ license denied.
* Test `is_certified` view method permissions gating.
* Test state preservation, expiration windows, and slash/revocation.

#### [NEW] [tools/mock_agent_service.py](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/tools/mock_agent_service.py)
* Local test server with toggles for simulating:
  * An aligned, secure agent (rejects prompt injections).
  * A vulnerable/jailbroken agent (leaks system prompt or agrees to illicit transfers).

---

## Verification Plan

### Automated Tests
1. **Direct Mode Unit Tests:**
   ```bash
   pytest tests/direct/ -v
   ```
   * Fast execution (~30–100ms) covering all contract state transitions, access control, and mock adversarial probes.

2. **AST & Syntax Safety Verification:**
   * Script to verify no forbidden standard library imports (`os`, `sys`, `subprocess`) or unhandled float storage exist in `contracts/gauntlet_ai.py`.

### Manual / Integration Verification
* Deploy to StudioNet or run local integration test once direct mode passes 100%.
* Verify cross-contract view calls return deterministic boolean answers for certified vs uncertified agents.
