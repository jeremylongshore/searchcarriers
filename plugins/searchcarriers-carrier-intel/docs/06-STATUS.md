# Carrier Intel - Status

## Current State

- [x] Plugin manifest (`plugin.json`) -- complete, 4 tools defined with tier gating
- [x] MCP configuration (`.mcp.json`) -- complete, server command and env configured
- [ ] MCP server (`carrier_intel_mcp.py`) -- **in progress**, scaffolded, tool registration pending
- [ ] Tier gating logic -- **in progress**, TIER_ORDER and TOOL_TIERS defined, runtime check not wired
- [ ] Commands (`sc-lookup.md`, `sc-profile.md`) -- **planned**
- [ ] Embedded skill (`SKILL.md`) -- **planned**
- [ ] Agent (`carrier-analyst.md`) -- **planned**
- [x] 6-doc set (`docs/01-06`) -- **done**
- [ ] Unit tests -- **planned**
- [ ] Integration tests -- **planned**
- [ ] Inventory CSV updated -- **planned** (currently shows status: planned, version: 0.0.0)
- [ ] SCHEMA.md -- **planned**
- [ ] README.md -- **planned**
- [ ] Validated with `validate.sh` -- **blocked on MCP server completion**

## Blockers

| Blocker | Description | Owner | ETA | Impact |
|---------|------------|-------|-----|--------|
| Risk Factors endpoint | `GET risk-factors` returns 404 on all tested route patterns. Need Garret to confirm the exact path, or confirm this endpoint does not exist yet. | Garret (adrenallen) | TBD | Blocks Risk Engine plugin (not this plugin), but entity_map could benefit from risk factor data |
| Vetting Report endpoint | `GET company-vetting-report` returns 404. Same situation as risk factors. | Garret (adrenallen) | TBD | Blocks Risk Engine plugin, not Carrier Intel |
| Insurance data completeness | `GET /company/{dot}/insurances` returned empty for test carriers. Need to verify with a carrier known to have active insurance filings. | Jeremy | This week | May affect carrier_profile output quality |
| Tier detection from API | Need to confirm how the API communicates the user's subscription tier. Does it return tier info on auth, or do we check via a separate endpoint? | Garret (adrenallen) | TBD | Tier gating implementation depends on this |

## Next Steps

1. **Complete MCP server implementation** (`carrier_intel_mcp.py`)
   - Register 4 tools with MCP protocol
   - Implement httpx-based API client with retry logic
   - Wire up tier gating checks
   - Add structured error handling for all HTTP error codes

2. **Write slash commands** (`commands/sc-lookup.md`, `commands/sc-profile.md`)
   - Map `/sc-lookup` to `carrier_lookup` with argument parsing
   - Map `/sc-profile` to `carrier_profile` accepting DOT number
   - Include help text and usage examples

3. **Write unit tests**
   - Mock API responses for all 4 tools
   - Test search auto-detection logic (DOT vs MC vs name vs VIN)
   - Test tier gating (Free user blocked from entity_map)
   - Test error handling paths (401, 403, 404, 429, 504)

4. **Write integration tests**
   - Test against live API with known carriers (Werner DOT 69494)
   - Verify response schema matches expected fields
   - Measure and record latency baselines

5. **Write embedded skill** (`skills/searchcarriers-carrier-intel/SKILL.md`)
   - Teach Claude when to use each tool
   - Include interpretation guidance for 143-field carrier object
   - Document pipeline handoff to Risk Engine

6. **Update inventory**
   - `inventory/plugins_inventory.csv`: status from "planned" to "in_progress", version to 0.1.0
   - Write SCHEMA.md with directory tree and tool registry

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-26 | Thin wrapper architecture -- MCP server calls API directly, no business logic duplication | SearchCarriers API already handles search, filtering, and pagination. Our value layer is in skills (interpretation, chaining, reporting), not in reimplementing API logic. Keeps MCP server simple and maintainable. |
| 2026-02-26 | carrier_profile aggregates 3 endpoints in one tool | Users should not need to know which endpoints exist. "Give me the full profile" should be one command, not three. The MCP server handles the fan-out. |
| 2026-02-26 | entity_map gated to Pro tier | VIN-based entity mapping requires N+1 API calls (1 equipment + N VIN searches). This is expensive in terms of rate limit consumption. Pro tier justifies the API cost and targets the compliance/fraud-detection use case. |
| 2026-02-26 | carrier_lookup and carrier_profile set to Free tier | Getting users into the product with real value on Free tier is critical for conversion. Basic lookup and profile are the gateway. Users who see the speed improvement over manual SAFER will upgrade for entity mapping and fleet analysis. |
| 2026-02-26 | fleet_summary set to Free tier | Fleet data (equipment and vehicles) is a high-interest data point that demonstrates depth. Keeping it Free lets users see the full data picture before upgrading. |
| 2026-02-26 | Sequential API calls for carrier_profile, not parallel | Authorities and insurances endpoints are fast (<500ms each). Sequential calls simplify error handling (if search returns no carrier, skip the other two). Parallel is a v0.2 optimization if latency is an issue. |
| 2026-02-26 | No local caching in v0.1 | Stateless is simpler. Caching adds complexity (TTL management, invalidation, storage). Defer to v0.2 when we have latency baselines and can measure the benefit. |
| 2026-02-26 | 6-doc set written before MCP server code | Documentation-first approach. Writing the business case, PRD, and architecture forces clear thinking about scope, non-goals, and data contracts before writing code. Prevents scope creep. |

## Release History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-26 | Initial plugin scaffold: plugin.json, .mcp.json, requirements.txt, 6-doc enterprise documentation set |
| 0.2.0 | -- | MCP server implementation with 4 tools, tier gating, error handling |
| 0.3.0 | -- | Commands, embedded skill, agent, tests |
| 1.0.0 | -- | Production release: validated, tested, documented, inventory updated |
