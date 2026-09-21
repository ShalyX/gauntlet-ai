# GenLayer Building Workflow: Architecture, Patterns & Standards

Synthesized from your `.codex` configuration, installed skills (`genlayer-dev`, `genlayernode`), and real-world project codebases (**Docket**, **Verdict**, and **Agent Reputation Registry**).

---

## 1. Executive Summary & Core Philosophy

Your GenLayer workflow has evolved from initial experimentation (June 2026 in *Verdict*) into an end-to-end, battle-tested engineering standard (September 2026 in *Docket*). 

The guiding principle across your codebase is:
> **"GenLayer is an on-chain subjective settlement gate, not a generic AI backend."**

You strictly separate concerns:
1. **Frontend / Agent Client:** UI, orchestration, non-authoritative previews, and transaction submission.
2. **External Sources:** Public, bounded evidence (GitHub APIs, REST endpoints) treated as untrusted until validated.
3. **GenLayer Contract:** The single source of truth for state transitions, subjective equivalence consensus, escrow lock/release, and dispute adjudication.

---

## 2. The Tooling & Skill Ecosystem (in `.codex`)

Your `.codex/plugins/cache/genlayerlabs` environment contains five core development skills:

| Skill | Purpose | Key CLI / Framework Commands |
|---|---|---|
| **`genvm-lint`** | AST safety & SDK semantic verification before test/deploy | `genvm-lint check <contract.py> --json`, `validate`, `schema`, `typecheck` |
| **`write-contract`** | Architecture rules, runner pinning, and equivalence patterns | Guidelines on storage (`TreeMap`, `DynArray`, `u256`), LLM resilience, error handling |
| **`direct-tests`** | Ultra-fast in-memory unit tests (~30–50ms, no server) | `pytest tests/direct/ -v` using `genlayer-test` fixtures (`direct_vm`, `direct_deploy`) |
| **`integration-tests`**| Multi-validator consensus verification | `gltest tests/integration/ -v -s --network studionet` (or `localnet`) |
| **`genlayer-cli`** | Network setup, deployment, receipt inspection, account management | `genlayer network set`, `genlayer deploy`, `genlayer receipt <hash> --stdout --stderr` |

---

## 3. End-to-End Contract Development Lifecycle

Your standard build cycle follows an uncompromised 6-stage pipeline:

```
[1. Boundary Design] ──> [2. Contract Authoring] ──> [3. AST / SDK Linting]
                                                             │
[6. Production / Frontend] <── [5. Integration Consensus] <── [4. Fast Direct Testing]
```

### Stage 1: The Boundary & Consensus Gate Check
Before writing any Python code:
- Confirm whether the contract requires independent validator agreement on external facts or AI judgments.
- Define the **Equivalence Principle**: Can outputs be canonicalized deterministically?
  - If **Yes** (e.g. strict JSON sort, RPC hashes): Use `gl.eq_principle.strict_eq()`.
  - If **No** (e.g. LLM prompts, external API calls with dynamic metadata): Use `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`.

### Stage 2: Contract Authoring Standards
- **Always pin concrete GenVM runner version hashes** at line 1:
  ```python
  # { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
  ```
  *(Never use `py-genlayer:test` or `py-genlayer:latest` in deployable network code).*
- **Storage Field Declarations:**
  - Class-level typed annotations only (`owner: Address`, `tasks: TreeMap[str, Task]`, `items: DynArray[str]`).
  - No Python built-in `dict` or `list` in persistent storage.
  - Sized integers (`u256` in atto-scale `10^18`) for currency and token values.
  - Enums stored as `str` (`PASS = "PASS"`), not Python `Enum` objects.
- **Defensive LLM Output Parsing:**
  - Always enforce `response_format="json"` in `gl.nondet.exec_prompt()`.
  - Sanitize markdown fences, strip trailing commas, and alias common alternate keys.
  - Fallback to neutral statuses (`INCONCLUSIVE` or `[LLM_ERROR]`) if malformed.
- **Custom Validator Pattern (`run_nondet_unsafe`):**
  - In `validator_fn(leaders_res: gl.vm.Result)`, inspect `leaders_res.calldata` (not `.data`).
  - Compare **only normalized, consensus-critical fields** via a comparison key (`_comparison_key`), ignoring unstable API timestamps, request counts, or non-essential headers.

### Stage 3: Linting & Validation Gate
- Run `genvm-lint check contracts/<contract>.py` before running tests.
- Catches forbidden Python imports (`os`, `sys`, `random`, `subprocess`), unhandled float arithmetic, and malformed `@gl.public.view` / `@gl.public.write` signatures.

### Stage 4: Fast Direct Testing (`pytest` + `genlayer-test`)
- In-memory execution without spinning up Docker or remote nodes:
  ```python
  def test_escrow_lifecycle(direct_vm, direct_deploy, direct_alice, direct_bob):
      contract = direct_deploy("contracts/docket.py")
      direct_vm.sender = direct_alice
      direct_vm.mock_web(r".*api\.github\.com/repos/.*", {"status": 200, "body": "{...}"})
      contract.register_task(...)
  ```
- Cheatcodes used: `direct_vm.sender`, `direct_vm.deal()`, `direct_vm.mock_web()`, `direct_vm.mock_llm()`, `direct_vm.expect_revert()`.

### Stage 5: Consensus Integration Testing (`gltest`)
- Run against StudioNet (`studio.genlayer.com`) or local Studio.
- Crucial rule established in your workflow:
  > **`ACCEPTED` / `FINALIZED` is transaction lifecycle status, NOT execution success.**
  - Transactions can finalize even when internal contract execution reverts.
  - Always assert `tx_execution_succeeded(receipt)` and verify `--stdout` / `--stderr`.

### Stage 6: Client & Frontend Integration
- Built with `genlayer-js` and `@genlayer/transaction-kit`.
- Normalized receipt extraction (`buildCaseReceipt`):
  - Formats verifiable evidence manifests (`pr_url`, `head_sha`, `actions_run_url`).
  - Separates off-chain workflow proofs from on-chain authoritative state transitions.
  - Implements fallback recovery paths (`REFUNDED`, `NEEDS_EVIDENCE`) with time-delayed claim windows.

---

## 4. Advanced Production Patterns Established in Docket

In your `Docket` dispute settlement project (September 2026), you resolved several non-trivial GenVM edge cases:

### 1. Bootstrapper Multi-Chunk Deployment
When complex intelligent contracts exceed the single transaction size limit on GenVM / Studio Next:
1. Deploy `contracts/docket_bootstrapper.py` first with `save_default_locked_slots = true` to claim the contract address.
2. Break compacted contract bytecode into small sequential chunks (`prepare_bootstrap_chunks.py`).
3. Pipe chunks through `push_code(b#<hex>)` in strictly ordered, non-retried transactions.
4. Call `finish()` once to atomically replace the bootstrapper bytecode with the full contract at the exact same address.
5. Re-verify the deployed bytecode SHA-256 against `manifest.json`.

### 2. Prompt Injection & Evidence Sandboxing
When feeding external, user-supplied content into GenVM LLM prompts:
- Delimit external inputs with explicit evidence boundaries:
  ```
  BEGIN EVIDENCE JSON
  <sanitized_payload>
  END EVIDENCE JSON
  ```
- Explicitly instruct the model that content inside the delimiter is untrusted data, never instructions.
- Validate structural invariants (e.g. SHA-256 hashes, file lengths, commit SHAs) deterministically in code *before* calling the LLM.

---

## 5. Quick Reference Checklist for Future Builds

- [ ] **Runner:** First line has pinned `py-genlayer:<hash>`.
- [ ] **Storage:** Class annotations use `TreeMap`, `DynArray`, `u256`, `@allow_storage`.
- [ ] **Consensus:** Custom validator compares a minimized `comparison_key` using `leaders_res.calldata`.
- [ ] **Lint:** `genvm-lint check contracts/<name>.py` returns exit code `0`.
- [ ] **Direct Tests:** Unit tests pass with `pytest tests/direct/`.
- [ ] **Receipt Verification:** Frontend inspects `tx_execution_succeeded` and execution payloads, not just `FINALIZED` lifecycle state.
