# Watchdog - Status

## Current State: In Development (Phase 7)

- [x] Plugin manifest (`plugin.json`) -- complete, 4 tools defined with Pro+ tier gating
- [x] MCP configuration (`.mcp.json`) -- complete, server command and env configured
- [ ] MCP server (`watchdog_mcp.py`) -- **planned**, scaffolded directory exists
- [ ] Alert formatter module (`formatters.py`) -- **planned**, format specs defined in docs
- [ ] Drift analyzer module (`drift.py`) -- **planned**, algorithm designed in docs
- [ ] Commands -- **planned**
- [ ] Embedded skill (`SKILL.md`) -- **planned**
- [ ] Agent (`watchdog-analyst.md`) -- **planned**
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
| Carrier Watch API endpoint paths | Need to confirm exact endpoint paths for watch list CRUD, alert retrieval, and change history. Expected patterns documented in architecture, but actual paths may differ. | Garret (adrenallen) | TBD | Blocks MCP server implementation. Docs use assumed paths based on API conventions. |
| Carrier Watch API response schema | Need example responses from the Carrier Watch endpoints to validate tool output schemas in the technical spec. Currently working from inferred structure. | Garret (adrenallen) | TBD | Blocks formatter implementation and integration tests. Unit tests can use mocked responses. |
| Tier detection from API | Same as other plugins: need to confirm how the API communicates subscription tier. Using `SEARCHCARRIERS_TIER` env var as workaround. | Garret (adrenallen) | TBD | Using env var workaround; no immediate blocker for implementation |
| Alert severity classification | Need to confirm the full list of change event types the Carrier Watch system detects. Severity classification logic depends on knowing all possible change types. | Garret (adrenallen) | TBD | Can implement with known types (insurance, authority, safety) and add others later |

## Next Steps

1. **Confirm Carrier Watch API endpoints** with Garret
   - Validate endpoint paths for watch list management
   - Validate endpoint paths for alert retrieval
   - Validate endpoint paths for change history
   - Get example request/response payloads

2. **Implement MCP server** (`scripts/watchdog_mcp.py`)
   - Register 4 tools with MCP protocol
   - Implement httpx-based API client with retry logic
   - Wire up tier gating (Pro+ on all tools)
   - Add structured error handling for all HTTP error codes

3. **Implement alert formatters** (`scripts/formatters.py`)
   - Slack Block Kit formatter with severity coloring
   - Webhook JSON formatter with flat structure
   - Telegram MarkdownV2 formatter with character escaping (v0.2)
   - Email HTML formatter with inline CSS (v0.2)

4. **Implement drift analyzer** (`scripts/drift.py`)
   - Event categorization (positive/negative/neutral)
   - Drift direction computation (improving/stable/deteriorating)
   - Summary statistics calculation

5. **Write unit tests**
   - Mock API responses for all tool actions
   - Test alert severity classification for all change types
   - Test each formatter output against channel specifications
   - Test drift computation with synthetic change histories
   - Test tier gating (non-Pro+ user blocked from all tools)
   - Test error handling paths (401, 403, 404, 429, 504)

6. **Write integration tests**
   - Test watch list CRUD against live API
   - Test alert retrieval with real data
   - Measure and record latency baselines
   - Validate response schemas against actual API output

7. **Write embedded skill** (`skills/searchcarriers-watchdog/SKILL.md`)
   - Teach Claude when to use each Watchdog tool
   - Monitoring strategy guidance (what to watch, how often to check)
   - Alert interpretation and recommended actions

8. **Write commands and agent**
   - Slash commands for common operations
   - Watchdog analyst agent for comprehensive monitoring workflows

9. **Update inventory**
   - `inventory/plugins_inventory.csv`: status from "planned" to "in_progress", version to 0.1.0
   - Write SCHEMA.md with directory tree and tool registry

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-26 | Watchdog is standalone, not part of the stackable pipeline | Monitoring is a fundamentally different operation from the lookup -> score -> report pipeline. Watch lists and alerts operate on a different time axis (ongoing vs. point-in-time). Forcing Watchdog into the pipeline would add complexity for no benefit. It can coexist alongside pipeline plugins without being chained to them. |
| 2026-02-26 | All tools gated to Pro+ tier | Carrier Watch is a premium SearchCarriers feature with server-side resource costs (monitoring loops, change detection, alert storage). Pro+ tier ($99/mo) aligns with the value proposition: ongoing monitoring prevents claims that cost 50-250x the subscription price. |
| 2026-02-26 | Format-only alert routing (no direct delivery) | Storing delivery credentials (Slack OAuth tokens, SMTP passwords, Telegram bot tokens) in a plugin is a security liability. By formatting only, Watchdog avoids credential management entirely. Users control delivery through their existing infrastructure. |
| 2026-02-26 | Four channels: Slack, Telegram, email, webhook | These cover the primary communication tools in freight operations. Slack and webhook for tech-forward teams, Telegram for dispatch groups (popular in trucking), email for management and customer communication. Webhook is the escape hatch for any integration not covered by the other three. |
| 2026-02-26 | Compliance drift as a separate tool, not embedded in alerts | Point-in-time alerts and longitudinal trend analysis serve different use cases. Alerts answer "what changed today?" Drift analysis answers "is this carrier getting worse?" Separating them keeps each tool focused and avoids overloading the alert response with historical context. |
| 2026-02-26 | Three severity levels: critical, warning, info | Two levels (alert/no-alert) is too coarse -- users need to prioritize. Four or more levels create confusion about what each level means. Three levels map cleanly to operational response: critical = stop tendering now, warning = investigate within 24-48 hours, info = note for the record. |
| 2026-02-26 | Slack and webhook in v0.1; Telegram and email in v0.2 | Slack and webhook are the highest-value channels for the target market (tech-forward 3PLs and brokerages). Telegram MarkdownV2 escaping and email HTML compatibility testing are more complex to implement correctly. Deferring them to v0.2 reduces MVP scope without losing core value. |
| 2026-02-26 | Documentation written before implementation | Same documentation-first approach as the pipeline plugins. Writing the business case, PRD, and architecture forces clear thinking about scope, API contracts, and component boundaries before writing code. The 6-doc set is the specification for implementation. |

## Release History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-26 | Initial plugin scaffold: plugin.json, .mcp.json, 6-doc enterprise documentation set |
| 0.2.0 | -- | MCP server with 4 tools, Slack and webhook formatters, drift analyzer |
| 0.3.0 | -- | Telegram and email formatters, commands, embedded skill, agent |
| 0.4.0 | -- | Comprehensive test suite (unit + integration + formatter + drift tests) |
| 1.0.0 | -- | Production release: fully tested, validated, documented, inventory updated |
