# Implementation Plan: `MultiSourceSynthesizer` — Reusable Multi-API Consensus Aggregator Primitive

We are building and contributing **`MultiSourceSynthesizer`** as a standalone, production-grade **Reusable Intelligent Contract** primitive under the **Builder** category (`contribution_type: 52`, 50x multiplier) on the GenLayer Portal.

---

## 1. Problem & Reusability Value for GenLayer Builders

### The Problem in GenVM
GenVM contracts can interact with the web via `gl.nondet.web.get` / `post`. However, web APIs are inherently noisy:
* Endpoints change JSON response formats, include shifting timestamps/headers, or suffer intermittent downtime.
* Multiple data providers reporting the same real-world fact (e.g., Binance vs. Kraken vs. CoinGecko for prices, or ESPN vs. BBC for sports results) frequently report slight variations.
* Naive contracts that call a single API fail when that API goes down. Naive contracts that call multiple APIs fail consensus because validators receive slightly differing raw bytes or timestamps and cannot reach strict agreement.

### The Solution & Reusable Primitive
**`MultiSourceSynthesizer`** is an OpenZeppelin-style reusable primitive contract that:
1. Takes $N$ independent web API endpoints representing the same target metric or fact.
2. Uses `gl.vm.run_nondet_unsafe` to fetch all sources, sandbox untrusted responses, and prompt GenVM validators to extract, cross-reference, and reconcile the data into a canonical payload.
3. Implements a bounded **Tolerance Comparison Key** (`comparison_key`) ensuring validators reach consensus if extracted values are within an allowable delta (e.g. 50 BPS / 0.5% for numeric feeds, or normalized enum strings for categorical facts).
4. Stores verified historical data with confidence scores and outlier detection on-chain.
5. Exposes a clean, gasless cross-contract view interface (`get_latest_data(feed_id)`) that any external GenLayer contract (prediction market, DeFi vault, parametric insurance, dynamic NFT) can consume in one line of code.

---

## 2. User Review Required

> [!IMPORTANT]
> **Cross-Contract Consumption Standard:**
> Other contracts will consume this primitive using GenLayer's standard cross-contract call mechanism:
> ```python
> synthesizer = gl.get_contract("0x<SYNTHESIZER_ADDRESS>")
> data = synthesizer.get_latest_data("ETH_USD_PRICE")
> # data contains: { "value_scaled": 345000, "decimals": 2, "confidence_bps": 9800, "sources_used": 3, "timestamp": "..." }
> ```
> We will provide a clean consumer example contract ([`contracts/examples/synthesizer_consumer.py`](file:///c:/Users/USER/Documents/antigravity/hopeful-fermi/contracts/examples/synthesizer_consumer.py)) demonstrating this.

> [!NOTE]
> **Equivalence Principle & Consensus Strategy:**
> To ensure validator agreement across noisy APIs:
> - **Numeric Feeds:** Comparison keys round the synthesized value to the feed's configured precision bucket (e.g., within $\pm 0.5\%$).
> - **Categorical Feeds:** Comparison keys normalize strings to uppercase trimmed tokens (e.g., `"TEAM_A_WON"`, `"CANCELLED"`).
> - **Prompt Injection Defense:** External API payloads are strictly wrapped inside `BEGIN RAW SOURCE DATA ... END RAW SOURCE DATA` delimiters with instructions that content inside is untrusted data.

---

## 3. Open Questions

1. **Default Feed Types:**
   Should the contract ship with pre-configured schemas for:
   - **Numeric / Financial Feeds** (scaled integers with decimal precision, e.g. token prices, weather temperatures)?
   - **Categorical / Event Feeds** (normalized string enums, e.g. election outcomes, sports match results)?
   *(Recommended: Support both via a `feed_type: "NUMERIC" | "CATEGORICAL"` configuration).*
2. **Access Control for Feed Registration:**
   Should anyone be able to register a custom feed by staking a bond, or should feed creation be permissioned/governed?
   *(Recommended: Anyone can register a feed, with a minimal stake to prevent storage spam).*

---

## 4. Proposed Changes

```
hopeful-fermi/
├── contracts/
│   ├── multi_source_synthesizer.py       # Core reusable Intelligent Contract primitive
│   └── examples/
│       └── synthesizer_consumer.py       # Reference contract showing how other builders integrate it
├── tests/
│   └── direct/
│       └── test_multi_source_synthesizer.py # In-memory direct VM test suite (7+ tests)
├── docs/
│   └── REUSABLE_SYNTHESIZER_PRIMITIVE.md # Architecture, integration guide & API documentation
├── MULTI_SOURCE_SYNTHESIZER_PLAN.md      # Project-level copy of this plan
└── walkthrough.md                        # Verification summary and submission package
```

### Component 1: Core Reusable Contract (`contracts/multi_source_synthesizer.py`)
* **Pinned Runner Header:**
  ```python
  # { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
  ```
* **Storage Dataclasses:**
  * `FeedConfig`: `owner: Address`, `feed_id: str`, `name: str`, `feed_type: str`, `query_prompt: str`, `sources: DynArray[str]`, `tolerance_bps: u256`, `min_sources_required: u256`, `heartbeat_seconds: u256`, `is_active: bool`.
  * `SynthesizedData`: `feed_id: str`, `value_scaled: u256`, `value_str: str`, `decimals: u256`, `confidence_bps: u256`, `sources_successful: u256`, `sources_failed: u256`, `outliers_detected: u256`, `updated_at: str`, `summary: str`.
* **State Storage:**
  * `feeds: TreeMap[str, FeedConfig]`
  * `latest_data: TreeMap[str, SynthesizedData]`
  * `feed_ids: DynArray[str]`
* **Consensus Engine (`run_nondet_unsafe`):**
  * `leader_fn`:
    1. Fetches all configured sources via `gl.nondet.web.get`.
    2. Builds sandboxed extraction prompt with raw payloads.
    3. Prompts LLM (`response_format="json"`) to parse, cross-reference, reject outliers, and synthesize consensus value.
    4. Computes normalized `comparison_key` (rounded bucket for numbers, enum token for categories).
  * `validator_fn(leaders_res: gl.vm.Result)`:
    1. Re-executes the multi-source fetch.
    2. Extracts consensus value and comparison key.
    3. Validates that the validator's comparison key matches `leaders_res.calldata["comparison_key"]` within tolerance.
* **Public Interface:**
  * `@gl.public.write def register_feed(...)`
  * `@gl.public.write def update_feed_sources(...)`
  * `@gl.public.write def refresh_feed(feed_id: str)`
  * `@gl.public.view def get_latest_data(feed_id: str) -> dict`
  * `@gl.public.view def get_feed_config(feed_id: str) -> dict`
  * `@gl.public.view def list_feeds() -> list[dict]`

### Component 2: Consumer Reference Contract (`contracts/examples/synthesizer_consumer.py`)
* Shows other builders how to import and consume `MultiSourceSynthesizer`.
* Demonstrates gating on confidence thresholds (`confidence_bps >= 8000`) and freshness checks.

### Component 3: Direct Mode Test Suite (`tests/direct/test_multi_source_synthesizer.py`)
* Unit tests using `genlayer-test` cheatcodes (`direct_vm.mock_web`, `direct_vm.mock_llm`, `direct_deploy`):
  1. `test_register_feed_success`
  2. `test_register_feed_validation_bounds`
  3. `test_refresh_feed_numeric_consensus_multi_source`
  4. `test_refresh_feed_outlier_rejection`
  5. `test_refresh_feed_categorical_consensus`
  6. `test_cross_contract_consumer_reading`
  7. `test_insufficient_sources_fails_gracefully`

### Component 4: Developer Documentation (`docs/REUSABLE_SYNTHESIZER_PRIMITIVE.md`)
* Clear documentation explaining the primitive, how consensus is achieved, equivalence principles used, and step-by-step code snippets for other developers.

---

## 5. Verification Plan

### Automated Tests
1. **Direct Mode Unit Tests:**
   * Run using the Python environment:
     ```powershell
     C:\Users\USER\.venv\Scripts\pytest.exe tests/direct/test_multi_source_synthesizer.py -v
     ```
   * Assert all tests pass with 0 failures.
2. **AST & Syntax Safety Check:**
   * Verify strictly compliant imports (no `os`, `sys`, `random`), no float storage, and correct `@allow_storage` annotations.

### Manual Verification & Portal Package
* Format the complete submission package (Studio import instructions, GitHub repository structure, and Portal form text) ready for the user to submit on their logged-in portal page.
