# Risk Engine - Status

## Current State: In Development (Phase 5)

- [x] Plugin manifest (`plugin.json`) -- complete, 4 tools defined with tier gating
- [x] MCP configuration (`.mcp.json`) -- complete, server command and env configured
- [ ] MCP server (`risk_engine_mcp.py`) -- **in progress**, scaffolded, tool registration pending
- [ ] Risk scoring module (`scoring.py`) -- **planned**, algorithm designed in docs
- [ ] Vetting rules module (`vetting.py`) -- **planned**, default rules defined in docs
- [ ] Data normalizer (`normalize.py`) -- **planned**
- [x] 6-doc enterprise set (`docs/01-06`) -- **done**
- [ ] Commands (`sc-risk.md`, `sc-vet.md`) -- **planned**
- [ ] Embedded skill (`SKILL.md`) -- **planned**
- [ ] Agent (`risk-analyst.md`) -- **planned**
- [ ] Unit tests (`test_scoring.py`, `test_vetting.py`) -- **planned**
- [ ] Integration tests (`test_integration.py`) -- **planned**
- [ ] Inventory CSV updated -- **planned** (currently shows status: planned, version: 0.0.0)
- [ ] Validated with `validate.sh` -- **blocked on MCP server completion**

## Blockers

| Blocker | Description | Owner | ETA | Impact |
|---------|------------|-------|-----|--------|
| Risk Factors endpoint | `GET /company/{dot}/risk-factors` returns 404 on all tested route patterns. Need Garret to confirm the exact path, or confirm this endpoint does not exist yet. If it exists, it would provide pre-computed risk factor data. | Garret (adrenallen) | TBD | Would simplify scoring if available; without it, Risk Engine computes scores from raw carrier/inspection data |
| Safety inspection data fields | Need to confirm which fields in the carrier object contain OOS rates and inspection counts. The 143-field schema from Carrier Intel maps `oos_rate_vehicle` and `oos_rate_driver` but actual field names in the API response may differ. | Jeremy | This week | Scoring accuracy depends on correct field mapping |
| Carrier Intel dependency | Risk Engine scoring works best with data from `carrier_profile` (carrier + authorities + insurances). Need Carrier Intel MCP server fully operational to test the pipeline end-to-end. | Jeremy | Parallel development | Blocks integration testing but not unit testing of scoring algorithms |
| Tier detection | Same as Carrier Intel: need to confirm how the API communicates subscription tier. Risk Engine inherits from `SEARCHCARRIERS_TIER` env var for now, but a runtime tier check would be more robust. | Garret (adrenallen) | TBD | Using env var workaround; no immediate blocker |

## Next Steps

1. **Implement MCP server** (`scripts/risk_engine_mcp.py`)
   - Register 4 tools with MCP protocol
   - Wire up tier gating via shared `check_tier`
   - Implement tool handlers that accept carrier data or DOT number
   - Add structured error handling and disclaimer injection

2. **Implement scoring module** (`scripts/scoring.py`)
   - Pure functions for each dimension (safety, insurance, authority, operational)
   - Composite score calculation with configurable weights
   - Confidence assessment based on data completeness
   - Score tier classification (LOW/MODERATE/ELEVATED/HIGH/CRITICAL)

3. **Implement vetting rules module** (`scripts/vetting.py`)
   - Default rules VET-01 through VET-08
   - Override mechanism for custom thresholds
   - Verdict logic: PASS/REVIEW/FAIL
   - Per-rule result reporting

4. **Implement data normalizer** (`scripts/normalize.py`)
   - Accept raw Carrier Intel JSON, output flat normalized dict
   - Handle missing fields with sentinel values
   - Type coercion (string numbers to int/float)
   - Data completeness percentage calculation

5. **Write slash commands** (`commands/sc-risk.md`, `commands/sc-vet.md`)
   - `/sc-risk DOT` maps to `risk_score`
   - `/sc-vet DOT` maps to `vetting_check`
   - Include help text and examples

6. **Write embedded skill** (`skills/searchcarriers-risk-engine/SKILL.md`)
   - Teach Claude when to use each tool
   - Interpretation guidance: what a score of 47 means, when REVIEW needs human attention
   - Pipeline chaining: how to pass Carrier Intel data to Risk Engine

7. **Write unit tests**
   - Scoring algorithm tests with known carrier profiles
   - Vetting rule evaluation tests with edge cases
   - Normalization tests with missing/malformed data
   - Confidence calculation tests

8. **Write integration tests**
   - Pipeline test: Carrier Intel -> Risk Engine with real API data
   - Tier gating validation
   - Latency benchmarks

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-26 | Risk Engine does not call SearchCarriers API directly | Separation of concerns. Carrier Intel handles data retrieval; Risk Engine handles data interpretation. This keeps Risk Engine testable without API access and prevents duplicate API client code. |
| 2026-02-26 | Scoring weights: Safety 35%, Insurance 25%, Authority 20%, Operational 20% | Safety is the strongest predictor of carrier performance. Insurance is the primary financial protection. Authority and operational factors are secondary indicators. Weights are informed by FMCSA enforcement priorities and industry claim patterns. |
| 2026-02-26 | Missing data treated as risk factor, not neutral | Absence of information is worse than known data. A carrier with no safety rating has not been audited -- this is itself a risk indicator. A carrier with no insurance records on file may be uninsured. Defaulting to elevated risk for missing data is the conservative (safer) choice. |
| 2026-02-26 | Vetting rules return PASS/REVIEW/FAIL, not just pass/fail | REVIEW is essential for real-world vetting. Not every borderline carrier should be rejected. A carrier with a 28% OOS rate (between the 25% REVIEW and 40% FAIL thresholds) deserves human attention, not automatic rejection. REVIEW triggers escalation to a compliance manager. |
| 2026-02-26 | `vetting_check` requires Pro+ while other tools require Pro | Configurable rules are an enterprise feature. The ability to set custom insurance minimums, OOS thresholds, and authority age requirements is how organizations enforce their specific carrier qualification policies. Pro gets the assessment; Pro+ gets the policy enforcement. |
| 2026-02-26 | Every response includes a disclaimer | Liability mitigation. Risk Engine provides decision support, not decisions. The disclaimer is injected at the response-building layer so it cannot be accidentally omitted. If this tool is ever cited in a legal proceeding, the advisory language must be present in every single response. |
| 2026-02-26 | Documentation written before implementation | Same documentation-first approach as Carrier Intel. The PRD, architecture, and scoring algorithm design force clear thinking about data contracts, edge cases, and component boundaries before writing code. The 6-doc set serves as the specification for implementation. |
| 2026-02-26 | Scoring modules are pure functions with no I/O | Testability. Pure scoring functions can be tested with mock data, no API key needed, no network dependency. The MCP server is the thin I/O shell; scoring logic is a separate, importable module. |

## Release History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-26 | Initial plugin scaffold: plugin.json, .mcp.json, 6-doc enterprise documentation set |
| 0.2.0 | -- | MCP server with 4 tools, scoring module, vetting rules, data normalizer |
| 0.3.0 | -- | Commands, embedded skill, agent, comprehensive test suite |
| 0.4.0 | -- | Pipeline integration validation (Carrier Intel -> Risk Engine -> Ops Reporter) |
| 1.0.0 | -- | Production release: fully tested, validated, documented, inventory updated |
