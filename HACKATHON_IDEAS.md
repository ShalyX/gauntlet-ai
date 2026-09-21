# GenLayer Hackathon Build Ideas: Scored & Scoped

Synthesized using your **Hackathon AI Build Workflow**:
- Ingested sponsor constraints (GenLayer Intelligent Contracts, GenVM Python runner, subjective consensus).
- Scored on the required 6 dimensions (Originality, Feasibility, Sponsor Fit, Demo Strength, User Usefulness, Implementation Risk).
- Scoped brutally to one painful workflow, one clear user, one sponsor integration, and one memorable demo moment.

---

## The 5 Evaluated Concepts

### Concept 1: AgentSLA — Autonomous Agent Delivery & Tool-Call Escrow Gate
* **Target User:** Autonomous AI agent orchestrators and developers hiring specialized subagents or autonomous workers.
* **The Real Pain:** In emerging agent-to-agent economies, delegating agents must escrow funds. However, traditional contracts can only verify numeric proofs or ECDSA signatures. If a worker agent hallucinates, returns malformed JSON, or fails subjective requirements (e.g. data synthesis, scraping completeness), funds lock in dispute or require manual human intervention.
* **The GenLayer Edge:** The contract holds the bounty in escrow. When the worker agent submits output (payload + endpoint proof), GenLayer validators independently probe the schema, verify data consistency, and run subjective quality checks via `gl.vm.run_nondet_unsafe`. If criteria are met, funds release immediately.
* **One Memorable Demo Moment:** An orchestrator agent posts a 50 GEN bounty for researching competitor API pricing. Agent A submits low-effort hallucinated garbage $\rightarrow$ GenLayer consensus rejects and slashes. Agent B submits complete, validated findings $\rightarrow$ GenLayer consensus passes and disburses funds in 30 seconds live on screen.

### Concept 2: PulseOracle — Subjective Event Settlement for Prediction Markets
* **Target User:** Prediction market creators (Polymarket-style) and automated hedging vaults.
* **The Real Pain:** Oracles like Chainlink and Pyth only support numeric feeds (token prices, weather sensors). Prediction markets on breaking real-world events ("Did the agency approve X?", "Did the protocol declare an emergency hard fork?") regularly freeze or trigger contentious human UMA voting rounds taking days.
* **The GenLayer Edge:** Intelligent Contracts fetch breaking public web pages / regulatory portals directly using `gl.nondet.web.get`, parse unstructured text, and use a custom validator comparison key to agree on categorical outcomes (YES / NO / INCONCLUSIVE) trustlessly on-chain.
* **One Memorable Demo Moment:** Triggering live resolution of an ambiguous headline event. The contract queries live news, validators evaluate evidence, and the market settles immediately without human council delay.

### Concept 3: Solder — Automated PR Bug Bounty Settlement
* **Target User:** Open-source project maintainers and freelance Web3 developers.
* **The Real Pain:** Bug bounties sit unmerged and unpaid for weeks because maintainers lack time to manually test and review community pull requests. Contributors get frustrated waiting for payouts.
* **The GenLayer Edge:** The contract holds the bounty. When a contributor submits a PR, GenLayer reads the GitHub PR diff, verifies that CI passed, checks acceptance criteria against issue requirements via GenVM LLM reasoning, and autonomously executes escrow payout upon consensus.
* **One Memorable Demo Moment:** Opening a live GitHub PR against a test repository. GenLayer detects the webhook/manifest, runs consensus on the diff, and streams GEN tokens to the contributor's wallet right in the terminal.

### Concept 4: BrandShield — Provable KOL & Creator Milestone Escrow
* **Target User:** Web3 marketing leads, DAOs, and crypto influencers / creators.
* **The Real Pain:** Brands pay KOLs upfront and get ghosted, or pay via escrow and argue over whether the influencer met the brief (e.g. deleted tweet before 24h, forgot disclosures, posted competitor promotions simultaneously).
* **The GenLayer Edge:** Time-bounded escrow contract that monitors public social feeds over a 24–48h window. GenVM validators verify post persistence, disclosure compliance, and guideline adherence, settling payment without subjective human disputes.
* **One Memorable Demo Moment:** Simulated campaign where an influencer posts a compliant tweet, then deletes it after 2 hours. GenLayer detects the deletion during milestone verification and refunds the brand automatically.

### Concept 5: GrantGate — Autonomous Milestone Escrow for DAO Grants
* **Target User:** DAO grant councils, ecosystem foundations, and funded dev teams.
* **The Real Pain:** Grant committees distribute millions of dollars in tranches, but verifying technical milestones (deployed testnet contract, functional API, public documentation) requires tedious manual committee review that delays builders for weeks.
* **The GenLayer Edge:** Grant recipients submit milestone deliverables (RPC endpoint, contract address, docs link). GenVM validators ping the RPC to verify bytecode exists, parse documentation coverage, and release the next tranche autonomously.
* **One Memorable Demo Moment:** Submitting a working testnet contract address + API URL to GrantGate. Validators verify live bytecode and schema on-chain, automatically unlocking the next 20% funding tranche.

---

## Idea Evaluation Matrix

| Metric (Scale 1–10) | 1. AgentSLA | 2. PulseOracle | 3. Solder (PR Bounty) | 4. BrandShield | 5. GrantGate |
|---|:---:|:---:|:---:|:---:|:---:|
| **Originality** | 9 | 8 | 8 | 7 | 8 |
| **Feasibility (48h Build)** | 9 | 8 | 8 | 7 | 9 |
| **Sponsor Fit (GenLayer)** | 10 | 10 | 9 | 8 | 9 |
| **Demo Strength** | 10 | 9 | 9 | 8 | 9 |
| **User Usefulness** | 9 | 9 | 8 | 8 | 9 |
| **Implementation Risk** *(10 = lowest risk)* | 9 | 7 | 7 | 6 | 8 |
| **TOTAL SCORE** | **56 / 60** | **51 / 60** | **49 / 60** | **44 / 60** | **52 / 60** |

---

## The Recommendation: Concept 1 — `AgentSLA`

### Why AgentSLA Wins
1. **Perfect GenLayer Fit:** It cannot be built on Ethereum or Solana without centralized trusted oracles. GenLayer's unique value proposition is *decentralized subjective execution*. AgentSLA leverages GenLayer for what it was built for: multi-validator consensus on AI-generated outputs.
2. **Extreme Hackathon Relevance:** AI agent hackathons (and tracks from OKX, Binance, Base, etc.) are overflowing with agent frameworks, but **almost none have solved trustless settlement and verification between agents**. AgentSLA is the missing financial infrastructure layer.
3. **Lowest External API Fragility:** Unlike social scraping (which easily hits Twitter/X paywalls and rate limits), AgentSLA verifies structured agent deliverables (JSON payloads, API responses, generated artifacts) using deterministic schemas + GenVM LLM reasoning.
4. **Immediate Demo Path:** Under 2 minutes, judges can watch:
   * Delegator agent posts task + escrow.
   * Two competing agent outputs submitted (one conforming, one defective).
   * GenLayer consensus rejects the hallucinated submission with exact validator error attribution, and approves the valid submission with instant escrow release.

---

## Scoped 48-Hour MVP Specification: `AgentSLA`

### 1. Target User
AI agent developers and autonomous workflows deploying multi-agent swarms with financial accountability.

### 2. The Core Problem
When Agent A pays Agent B to execute a task, Agent A cannot verify quality on-chain before funds are lost, and smart contracts cannot natively evaluate unstructured agent responses.

### 3. One Core Workflow (The Happy Path)
1. **Deposit & Register:** Delegator deposits GEN into `AgentSLA.py` with a task specification (Task ID, criteria schema, timeout, bounty).
2. **Submit Execution:** Worker agent calls `submit_deliverable(task_id, deliverable_json)`.
3. **Consensus Validation:**
   * `leader_fn`: Evaluates deliverable against criteria schema using `gl.nondet.exec_prompt(..., response_format="json")`.
   * `validator_fn`: Re-runs evaluation via `run_nondet_unsafe` and compares normalized `comparison_key` verdicts.
4. **Settlement:** On consensus approval, escrow is released directly to the worker's wallet. On timeout or rejection, funds refund to delegator.

### 4. Must-Haves vs. Nice-to-Haves
* **Must-Have (Core Spine):**
  - `contracts/agent_sla.py` (pinned runner `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`).
  - Unit tests in `tests/direct/` proving state transitions, reverts, and consensus mocks.
  - Integration test on StudioNet verifying validator consensus.
  - Minimal, high-signal web UI (or CLI runner) showing live transaction states and validator verdict breakdowns.
* **Nice-to-Have (Cut for 48h):**
  - Multi-tier appeals court.
  - Complex reputation staking bonding curves.
  - Private credential proxying.

### 5. Demo Path (2 Minutes)
1. **0:00–0:25:** Problem statement — "Agents are trading work, but on-chain payments lack quality enforcement."
2. **0:25–0:40:** Show `AgentSLA` contract deployed on GenLayer StudioNet.
3. **0:40–1:20:** Live execution — Trigger task evaluation with two test agents. Show GenLayer validator reasoning on screen.
4. **1:20–1:45:** Settlement verification — Show final transaction receipt and GEN token transfer.
5. **1:45–2:00:** Closing statement on autonomous agent economy infrastructure.
