# API Bridge - Status

## Current State: Documentation Complete (Phase 8)

- [x] Plugin manifest (`plugin.json`) -- complete, 4 tools defined with SMB/Enterprise tier gating
- [x] MCP configuration (`.mcp.json`) -- complete, server command and env configured
- [ ] MCP server (`api_bridge_mcp.py`) -- **planned**, scaffolded directory exists
- [ ] Batch processor (`batch.py`) -- **planned**, architecture designed in docs
- [ ] Rate limiter (`rate_limiter.py`) -- **planned**, token bucket design specified
- [ ] Health checker (`health.py`) -- **planned**, endpoint probing logic specified
- [ ] TMS mapper (`tms_mapper.py`) -- **planned**, field mappings specified for McLeod, TMW, generic CSV
- [ ] Webhook client (`webhooks.py`) -- **planned**, CRUD interface specified
- [ ] Commands -- **planned**
- [ ] Embedded skill (`SKILL.md`) -- **planned**
- [ ] Agent -- **planned**
- [x] 6-doc enterprise set (`docs/01-06`) -- **done**
- [ ] Unit tests -- **planned**
- [ ] Integration tests -- **planned**
- [ ] Inventory CSV updated -- **planned** (currently shows status: planned, version: 0.0.0)
- [ ] SCHEMA.md -- **planned**
- [ ] README.md -- **planned**
- [ ] Validated with `validate.sh` -- **blocked on MCP server completion**

## Blockers

| Blocker | Description | Owner | ETA | Impact |
|---------|------------|-------|-----|--------|
| Webhook API endpoint paths | Need to confirm exact endpoint paths for Carrier Watch webhook CRUD. Using assumed paths (`/api/v1/webhooks`) based on REST conventions. | Garret (adrenallen) | TBD | Blocks webhook_manage implementation. Docs use assumed paths. |
| Webhook API response schema | Need example responses from the webhook CRUD endpoints to validate tool output schemas. | Garret (adrenallen) | TBD | Blocks webhook_manage implementation and integration tests. |
| Rate limit header format | Need to confirm exact rate limit response headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`). Health check and rate limiter depend on parsing these. | Garret (adrenallen) | TBD | Using assumed header names. Can implement with fallback if headers not present. |
| Tier detection from API | Same as other plugins: need to confirm how the API communicates subscription tier. Using `SEARCHCARRIERS_TIER` env var as workaround. | Garret (adrenallen) | TBD | Using env var workaround; no immediate blocker for implementation. |
| TMS format validation | McLeod and TMW field mappings are based on published import specs, but need validation against actual TMS import processes at a customer site. | Jeremy | TBD | Can ship generic CSV in v0.1; TMS-specific formats are v0.2 anyway. |

## Next Steps

1. **Implement MCP server** (`scripts/api_bridge_mcp.py`)
   - Register 4 tools with MCP protocol
   - Implement httpx-based API client with retry logic
   - Wire up tier gating (SMB for 3 tools, Enterprise for tms_sync)
   - Add structured error handling for all HTTP error codes

2. **Implement rate limiter** (`scripts/rate_limiter.py`)
   - Token bucket with configurable rate and capacity
   - Shared across all tools in a session
   - Parse rate limit response headers to adapt dynamically

3. **Implement batch processor** (`scripts/batch.py`)
   - DOT queue management with progress callbacks
   - Error isolation per DOT
   - Configurable section depth (basic, standard, full)
   - Progress reporting every 10 carriers

4. **Implement health checker** (`scripts/health.py`)
   - Sequential endpoint probing with timing
   - Status classification (ok / slow / error)
   - Overall health computation
   - Rate limit header parsing

5. **Implement webhook client** (`scripts/webhooks.py`)
   - CRUD operations against Carrier Watch API
   - URL and event type validation
   - Structured response formatting

6. **Implement TMS mapper** (`scripts/tms_mapper.py`)
   - Generic CSV export (v0.1)
   - JSON export (v0.1)
   - McLeod and TMW mappings (v0.2)
   - Date format and status code translation

7. **Write unit tests**
   - Mock API responses for all 4 tools and all actions
   - Test batch processing at scale (100 DOTs, mixed success/failure)
   - Test rate limiter token bucket behavior
   - Test TMS field mapping accuracy
   - Test tier gating (SMB blocked from tms_sync, Free blocked from all)

8. **Write integration tests**
   - Test api_health against live API
   - Test bulk_lookup with 5 known DOTs
   - Test webhook_manage list (read-only, safe to run)
   - Measure latency baselines

9. **Write commands, skill, and agent**
   - Slash commands for common operations
   - Embedded skill for Claude integration guidance
   - Agent for complex multi-tool workflows

10. **Update inventory**
    - `inventory/plugins_inventory.csv`: status from "planned" to "in_progress", version to 0.1.0
    - Write SCHEMA.md with directory tree and tool registry

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-26 | API Bridge is standalone, not part of the stackable pipeline | Bulk operations, TMS sync, API monitoring, and webhook management are integration concerns, not per-carrier analysis steps. They operate at a different scale (batch vs. single carrier) and a different time axis (operational vs. analytical). Forcing them into the pipeline adds complexity for no benefit. |
| 2026-02-26 | SMB tier ($199/mo) for api_health, bulk_lookup, webhook_manage | These tools serve mid-size operations teams that need batch processing and monitoring. The price point reflects the operational value: quarterly re-qualification that saves 3+ days of analyst time justifies $199/month immediately. |
| 2026-02-26 | Enterprise tier ($499/mo) for tms_sync | TMS integration is the highest-value feature. It eliminates manual re-keying, reduces transcription errors, and requires maintaining format-specific field mappings. Enterprise tier reflects both the value delivered and the maintenance cost of supporting TMS format compatibility. |
| 2026-02-26 | Maximum 100 DOTs per bulk_lookup | Balances batch utility against execution time. At 3 req/s, 100 DOTs with full sections takes ~100 seconds. Larger batches risk MCP tool timeouts and provide diminishing UX returns (users waiting 5+ minutes for a response). 500-carrier panels split into 5 manageable batches. |
| 2026-02-26 | Client-side rate limiting, not server-side throttling | The MCP server controls request pacing to avoid 429 responses. This is more predictable than hitting 429s and retrying. The token bucket ensures smooth request distribution rather than burst-then-wait patterns. |
| 2026-02-26 | TMS field mappings are code, not config files | Mappings are Python dictionaries in `tms_mapper.py`. Adding a new TMS requires adding a dictionary and registering it. This is simpler than external YAML/JSON config files that need loading, validation, and error handling. The mapping set is small (3-5 TMS platforms) and changes infrequently. |
| 2026-02-26 | Generic CSV and JSON in v0.1; McLeod and TMW in v0.2 | Generic formats work with any TMS that supports CSV import. TMS-specific formats (McLeod, TMW) require validation against real TMS import processes that we have not done yet. Ship the useful thing now, refine TMS specifics with customer feedback. |
| 2026-02-26 | api_health uses Werner (DOT 69494) as probe target | Werner is a large, stable carrier that will always be in the database. Using a real carrier for health probes ensures end-to-end validation (not just connectivity but actual data retrieval). The 5 probe requests consume minimal rate limit budget. |
| 2026-02-26 | Documentation written before implementation | Same documentation-first approach as all other plugins. The 6-doc set defines scope, API contracts, error handling, and component boundaries before any code is written. Prevents scope creep and ensures all implementation decisions are pre-documented. |

## Release History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-26 | Initial plugin scaffold: plugin.json, .mcp.json, 6-doc enterprise documentation set |
| 0.2.0 | -- | MCP server with api_health, bulk_lookup (basic/standard), webhook_manage, generic CSV/JSON export |
| 0.3.0 | -- | tms_sync with McLeod and TMW formats, bulk_lookup full sections, import mode with diff |
| 0.4.0 | -- | Commands, embedded skill, agent, comprehensive test suite |
| 1.0.0 | -- | Production release: validated, tested, documented, inventory updated |
