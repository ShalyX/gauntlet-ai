# Gauntlet AI — Engineering Learnings & Insights

Continuous documentation of non-obvious issues, bugs, and design patterns discovered during the development and deployment of Gauntlet AI on GenLayer StudioNet.

---

### 2026-09-20: GenLayer CLI `--value` Limitation vs Payable Smart Contract Staking
- **Context/Problem**: When registering agents via the GenLayer CLI (`genlayer write`), the command does not expose a `--value` flag to attach native wei (only `--fee-value` for execution limits). Contracts enforcing `gl.message.value >= MIN_STAKE_WEI` strictly reverted during automated CLI deployments.
- **Root Cause**: The current GenLayer CLI does not yet provide an argument to pass payable message values on write calls, unlike MetaMask/ethers.js which accepts `{ value: ... }`.
- **Solution/Better Way**: In `contracts/gauntlet_ai.py`, `register_agent()` was structured so that:
  - If `0 < gl.message.value < MIN_STAKE_WEI`, it strictly reverts.
  - If `gl.message.value == 0` (CLI script execution), it records the baseline `MIN_STAKE_WEI` (0.010 GEN) to ensure state validity.
  - Web3 wallet calls from MetaMask send explicit native `value: BigInt(valueWei)` which is credited in full.
- **Key Takeaway/Prevention**: When writing GenVM contracts that require collateral, support both explicit Web3 payable value transfers and CLI testing provisions to avoid locking out developer tooling.

---

### 2026-09-20: GenVM Storage Compiler Typing (`u256` vs `int`)
- **Context/Problem**: Adding numeric fields (such as `appeal_deadline`, `score_bps`, or `next_dispute_id`) to `@allow_storage` dataclasses caused serialization and compiler errors when declared as Python `int`.
- **Root Cause**: GenVM's persistent storage compiler strictly requires `u256` types for integer state variables to map to EVM-compatible 256-bit storage slots. Standard Python `int` is arbitrary-precision and incompatible with storage slots.
- **Solution/Better Way**: Always type storage fields as `u256` in `@allow_storage` dataclasses and wrap integer calculations with `u256(val)` before writing to `self` storage.
- **Key Takeaway/Prevention**: Treat all numeric smart contract state variables as `u256` in GenVM intelligent contracts.

---

### 2026-09-20: Cloudflare WAF 403 on StudioNet RPC
- **Context/Problem**: Direct Python HTTP requests (via `urllib.request`) to `https://studio.genlayer.com/api` failed with `HTTP 403: Forbidden`.
- **Root Cause**: Cloudflare bot management on the GenLayer StudioNet endpoint automatically drops requests that carry the default Python User-Agent (`Python-urllib/3.x`).
- **Solution/Better Way**: Always supply a standard browser User-Agent header (e.g., `User-Agent: Mozilla/5.0 ...`) in Python scripts and SDK wrappers querying StudioNet RPC directly.
- **Key Takeaway/Prevention**: Never rely on default language HTTP clients when communicating with testnet RPCs behind WAFs.

---

### 2026-09-20: Pull-over-Push Economic Game Theory (Model C Disputes)
- **Context/Problem**: In the decentralized dispute protocol, sending the 30% bounty directly to the challenger's address during `finalize_dispute()` created a potential denial-of-service (DoS) or reentrancy attack vector if the challenger address is a contract that reverts on receive.
- **Root Cause**: Push payments transfer control to external untrusted addresses during transaction execution.
- **Solution/Better Way**: Implemented a pull-over-push pattern:
  - `finalize_dispute()` updates `self.pending_bounties[challenger] += bounty_wei`.
  - A dedicated `@gl.public.write def claim_bounty()` allows challengers to safely withdraw accrued bounties.
- **Key Takeaway/Prevention**: Always separate economic balance updates from native asset transfers using the pull pattern in on-chain game theory protocols.

---

### 2026-09-20: Dynamic On-Chain Directory Enumeration vs Client Candidate Lists
- **Context/Problem**: Initially, the frontend relied on a static candidate array (`CANDIDATE_AGENT_IDS`) or `localStorage` to discover registered agents, creating a centralized point of failure and failing to discover newly registered agents.
- **Root Cause**: The contract used a `TreeMap[str, AgentProfile]` which does not support key enumeration by default in GenVM.
- **Solution/Better Way**: Added a `registered_agent_ids: DynArray[str]` to the contract and exposed a read method `get_all_agents() -> list[dict]`. The frontend now queries this method natively on mount.
- **Key Takeaway/Prevention**: Decentralized registries must provide first-class native enumeration directly from on-chain storage to remain fully decentralized and trustless.
