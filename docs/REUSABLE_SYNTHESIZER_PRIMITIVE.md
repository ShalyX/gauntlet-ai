# `MultiSourceSynthesizer`: Reusable Multi-API Consensus Aggregator Primitive

> **GenLayer Intelligent Contract Contribution — Builder Category (`contribution_type: 52`)**  
> *A production-ready, composable primitive for aggregating, cross-referencing, and normalizing data across $N$ independent web APIs using GenVM multi-validator consensus.*

---

## 1. Executive Summary & Problem Space

### The Core Friction in GenVM Web Integration
GenLayer gives smart contracts the superpower of interacting with off-chain web data via `gl.nondet.web.get` and `gl.nondet.web.post`. However, in real-world decentralized applications, relying on a single web API introduces catastrophic failure points:
1. **API Outages & Downtime:** If an oracle contract relies on one endpoint, the entire dApp freezes if that endpoint fails.
2. **Schema Drift & Unstable Payloads:** Web endpoints frequently change JSON keys, include unpredictable HTTP headers, or return dynamic request IDs.
3. **Consensus Desynchronization:** If a developer attempts to call multiple APIs naively, validators receive slightly different numbers (e.g. Binance reporting \$3,450.10 while Kraken reports \$3,451.20). Without a principled equivalence mechanism, validator consensus fails.

### The Solution: `MultiSourceSynthesizer`
`MultiSourceSynthesizer` is a standardized, reusable Intelligent Contract primitive that solves these challenges:
* **Multi-Source Resilience:** Queries $N$ independent endpoints (e.g., 2 to 5 sources) in parallel.
* **Prompt Injection & Sandboxing Defense:** Delimits untrusted external payloads using `BEGIN RAW SOURCE DATA ... END RAW SOURCE DATA`.
* **Subjective Equivalence & Tolerance Buckets:** Employs a bounded numerical bucketing formula or normalized categorical enum tokens, ensuring validators reach consensus despite minor cross-source variances.
* **Gasless Cross-Contract Integration:** Exposes `get_latest_data(feed_id)` so any external contract (prediction market, DeFi vault, insurance protocol) can read verified, multi-source data in a single line of code.

---

## 2. Architecture & Workflow

```
[External Web API 1] ──┐
[External Web API 2] ──┼─> [gl.nondet.web.get] ──> [Prompt Sandbox] ──> [LLM Synthesis]
[External Web API 3] ──┘                                                      │
                                                                             ▼
[External DApps / DAOs] <── [get_latest_data()] <── [On-Chain State] <── [Tolerance Bucket]
```

### 1. Multi-Validator Consensus (`run_nondet_unsafe`)
```python
def leader_fn() -> dict:
    return _fetch_and_synthesize()

def validator_fn(leaders_res: gl.vm.Result) -> bool:
    validators_res = _fetch_and_synthesize()
    leader_key = leaders_res.calldata.get("comparison_key")
    validator_key = validators_res.get("comparison_key")
    
    # Numeric feeds allow +/- 1 tolerance bucket
    if feed_type == FEED_TYPE_NUMERIC:
        return abs(int(leader_key) - int(validator_key)) <= 1
    # Categorical feeds require exact enum match
    return int(leader_key) == int(validator_key)

result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
```

### 2. The Tolerance Bucketing Formula
For numeric feeds, raw floats cannot be compared directly across independent validators. We bucket scaled integers according to the feed's allowable tolerance (in basis points):

$$\text{bucket\_size} = \max\left(1, \frac{\text{value\_scaled} \times \text{tolerance\_bps}}{10000}\right)$$
$$\text{comparison\_key} = \left\lfloor \frac{\text{value\_scaled}}{\text{bucket\_size}} \right\rfloor$$

This guarantees that minor price fluctuations across agreeing APIs fall into the same or adjacent comparison buckets, enabling robust BFT consensus.

---

## 3. Storage Schema & Public Interface

### Storage Dataclasses
```python
@allow_storage
@dataclass
class FeedConfig:
    owner: Address
    feed_id: str
    name: str
    feed_type: str              # "NUMERIC" or "CATEGORICAL"
    query_prompt: str
    sources: DynArray[str]      # 2 to 5 independent URLs
    tolerance_bps: u256         # e.g., 100 bps = 1.0% allowable delta
    min_sources_required: u256  # Minimum successful endpoints needed
    heartbeat_seconds: u256
    is_active: bool
    created_at: str

@allow_storage
@dataclass
class SynthesizedData:
    feed_id: str
    value_scaled: u256          # Scaled by 10^decimals (e.g. 345033 for $3450.33)
    value_str: str              # String representation or normalized enum
    decimals: u256              # Precision scale (e.g., 2)
    confidence_bps: u256        # Reliability score (0 to 10000)
    sources_successful: u256    # Number of sources that returned 200 OK
    sources_failed: u256        # Number of failed/timeout sources
    outliers_detected: u256     # Number of anomalous sources rejected
    status: str                 # "OK", "DEGRADED", or "STALE"
    updated_at: str
    summary: str
```

### Public Methods
* `@gl.public.write def register_feed(feed_id, name, feed_type, query_prompt, sources, tolerance_bps, min_sources_required, heartbeat_seconds)`
* `@gl.public.write def refresh_feed(feed_id)`: Triggers multi-validator consensus re-fetch and synthesis.
* `@gl.public.view def get_latest_data(feed_id) -> dict`: Returns the latest verified payload.
* `@gl.public.view def get_feed_config(feed_id) -> dict`: Returns configuration parameters.
* `@gl.public.view def list_feeds() -> list[str]`: Returns all active feed IDs.

---

## 4. How Other Builders Integrate It (Cross-Contract Integration)

Any GenLayer contract can consume `MultiSourceSynthesizer` with standard cross-contract calls:

```python
from genlayer import *

class PredictionMarket(gl.Contract):
    synthesizer_address: Address

    def __init__(self, synthesizer_address: Address):
        self.synthesizer_address = synthesizer_address

    @gl.public.write
    def resolve_market(self, market_id: str, feed_id: str):
        # 1. Connect to deployed MultiSourceSynthesizer
        synthesizer = gl.get_contract(self.synthesizer_address)

        # 2. Query latest verified data
        data = synthesizer.get_latest_data(feed_id)

        # 3. Defensive quality gates
        if not data["is_initialized"]:
            raise Exception("Feed not initialized")
        if data["status"] != "OK":
            raise Exception("Feed status is not OK")
        if data["confidence_bps"] < 8000:
            raise Exception("Confidence below 80% threshold")

        # 4. Settle market using verified canonical value
        winner = data["value_str"]
        self._payout_winners(market_id, winner)
```

---

## 5. Testing & Verification

The contract is thoroughly covered by direct in-memory unit tests (`tests/direct/test_multi_source_synthesizer.py`):
1. **`test_register_feed_success`:** Validates feed registration, configuration storage, and listing.
2. **`test_register_feed_validation_bounds`:** Ensures bounds checking on sources count, feed types, and empty identifiers.
3. **`test_refresh_feed_numeric_consensus`:** Mocks 3 independent APIs with minor price variances and verifies scaled integer consensus.
4. **`test_refresh_feed_outlier_rejection`:** Simulates 1 corrupted/anomalous API and verifies that the consensus engine rejects it as an outlier while maintaining high confidence from agreeing endpoints.
5. **`test_refresh_feed_categorical_consensus`:** Verifies normalization and consensus on real-world event/sports outcomes.
6. **`test_degraded_status_on_low_confidence`:** Asserts that when sources fail with HTTP 500s, the feed marks status as `DEGRADED`.

---

## 6. GenLayer Portal Submission Information

* **Contribution Category:** Builder
* **Contribution Type:** `Intelligent Contracts` (`id: 52`)
* **Title:** `MultiSourceSynthesizer: Reusable Multi-API Consensus Aggregator Primitive`
* **Evidence URLs:**
  - GenLayer Studio Contract: `https://studio.genlayer.com/?import-contract=...`
  - GitHub Repository: `https://github.com/.../multi-source-synthesizer`
* **Summary for Notes Field:**
  > MultiSourceSynthesizer is an OpenZeppelin-style reusable Intelligent Contract primitive for GenVM. It solves the core oracle challenge of web API fragility by querying N independent endpoints in parallel, sandboxing untrusted inputs, and using GenVM multi-validator consensus with a bounded tolerance comparison key to extract and reconcile data into a canonical on-chain feed. Supports both NUMERIC (scaled integer with tolerance buckets) and CATEGORICAL (normalized string enums) feeds, with built-in outlier rejection and confidence scoring. Any GenLayer contract (prediction markets, DeFi, parametric insurance) can consume it in one line of code via `get_latest_data(feed_id)`. Includes complete test suite and consumer reference implementation.
