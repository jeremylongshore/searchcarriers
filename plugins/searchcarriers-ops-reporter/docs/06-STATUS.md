# Ops Reporter - Status

## Current State: In Development (Phase 6)

- [x] Plugin manifest (`plugin.json`) -- complete, 4 tools defined with Pro tier gating
- [x] MCP configuration (`.mcp.json`) -- complete, server command and env configured
- [ ] MCP server (`ops_reporter_mcp.py`) -- **planned**, tool registration and handler routing
- [ ] Report generator (`report.py`) -- **planned**, section builders designed in docs
- [ ] Comparison engine (`compare.py`) -- **planned**, table construction and best/worst logic
- [ ] Export formatter (`export.py`) -- **planned**, JSON/CSV/Markdown output handlers
- [ ] Fleet formatter (`fleet.py`) -- **planned**, equipment breakdown and age analysis
- [ ] Template helpers (`templates.py`) -- **planned**, shared formatting utilities
- [x] 6-doc enterprise set (`docs/01-06`) -- **done**
- [ ] Commands (`sc-report.md`, `sc-compare.md`) -- **planned**
- [ ] Embedded skill (`SKILL.md`) -- **planned**
- [ ] Agent (`ops-reporter.md`) -- **planned**
- [ ] Unit tests (`test_report.py`, `test_compare.py`, `test_export.py`, `test_fleet.py`) -- **planned**
- [ ] Integration tests (`test_integration.py`) -- **planned**
- [ ] Inventory CSV updated -- **planned** (currently shows status: planned, version: 0.0.0)
- [ ] Validated with `validate.sh` -- **blocked on MCP server completion**

## Blockers

| Blocker | Description | Owner | ETA | Impact |
|---------|------------|-------|-----|--------|
| Carrier Intel MCP server | Ops Reporter depends on Carrier Intel for carrier data. Carrier Intel MCP server is scaffolded but not fully operational yet. | Jeremy | Parallel development | Blocks integration testing; unit testing with mock data can proceed independently |
| Risk Engine MCP server | Ops Reporter produces richer reports when Risk Engine data is available. Risk Engine MCP server is scaffolded but not fully operational yet. | Jeremy | Parallel development | Blocks full pipeline integration testing; Ops Reporter degrades gracefully without risk data |
| Tier detection from API | Same blocker as Carrier Intel and Risk Engine: need to confirm how the API communicates subscription tier. Currently using `SEARCHCARRIERS_TIER` env var as workaround. | Garret (adrenallen) | TBD | Using env var workaround; no immediate blocker for implementation |
| Report format validation | No formal acceptance criteria for "professional report quality" beyond the examples in docs. Need stakeholder review of sample output before locking report template. | Jeremy / Garret | Before v0.2 | Does not block v0.1 implementation, but template may change based on feedback |

## Next Steps

1. **Implement MCP server** (`scripts/ops_reporter_mcp.py`)
   - Register 4 tools with MCP protocol
   - Wire up tier gating via shared `check_tier`
   - Implement tool handlers that accept carrier data, risk data, and format options
   - Add structured error handling and disclaimer injection

2. **Implement report generator** (`scripts/report.py`)
   - Section builder functions (executive summary, company overview, safety, insurance, authority, risk, qualification)
   - Missing data handling with "not available" stubs
   - Template helpers integration

3. **Implement comparison engine** (`scripts/compare.py`)
   - Carrier count validation (2-5)
   - Metric extraction from carrier and risk data
   - Markdown table construction with best/worst highlighting
   - Summary recommendation generation

4. **Implement export formatter** (`scripts/export.py`)
   - JSON serializer with meta block
   - CSV generator with standard TMS headers
   - Markdown delegator (reuses report generator)
   - Format validation and error handling

5. **Implement fleet formatter** (`scripts/fleet.py`)
   - Equipment type breakdown with percentages
   - Make/model distribution tables
   - Fleet age analysis
   - Notable characteristics auto-detection

6. **Write template helpers** (`scripts/templates.py`)
   - format_table, format_header, format_disclaimer
   - format_currency, format_percentage
   - Status and rating code mapping

7. **Write slash commands** (`commands/sc-report.md`, `commands/sc-compare.md`)
   - `/sc-report DOT` maps to `generate_report`
   - `/sc-compare DOT1 DOT2 [DOT3 DOT4 DOT5]` maps to `generate_compare`

8. **Write unit tests**
   - Report section builders with known data
   - Comparison table construction with 2 to 5 carriers
   - CSV/JSON export format validation
   - Fleet analysis with various fleet compositions
   - Missing data and edge cases

9. **Write integration tests**
   - Full pipeline: Carrier Intel -> Risk Engine -> Ops Reporter
   - Partial pipeline: Carrier Intel -> Ops Reporter (no risk data)
   - Latency benchmarks

10. **Write embedded skill** (`skills/searchcarriers-ops-reporter/SKILL.md`)
    - Teach Claude when to use each reporting tool
    - Pipeline orchestration guidance
    - Output format selection guidance

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-26 | Ops Reporter does not call SearchCarriers API directly | Separation of concerns. Carrier Intel retrieves data; Risk Engine analyzes; Ops Reporter formats. This keeps each stage independently testable and avoids duplicate API client code across three plugins. |
| 2026-02-26 | All four tools gated to Pro tier | Ops Reporter's value depends on the full pipeline. Since Risk Engine (the data source for the most useful report sections) is Pro, and Free users already get raw data via Carrier Intel, gating Ops Reporter at Pro creates a clean tier boundary: Free = raw data, Pro = analysis + reports. |
| 2026-02-26 | Reports generated in Markdown, not PDF | Markdown is universally renderable (GitHub, VS Code, email clients, web browsers). PDF adds complexity (page layout, fonts, rendering engine) without clear user demand. Markdown-to-PDF conversion is a one-line pandoc command for users who need it. Deferred PDF to v0.2. |
| 2026-02-26 | Comparison limited to 2-5 carriers | More than 5 carriers makes the comparison table unreadable in a terminal. The 2-5 range covers the common use case: evaluating a shortlist for load tendering. Bulk carrier analysis belongs to a different workflow (batch reporting, v0.2). |
| 2026-02-26 | Reports degrade gracefully when risk data is missing | Users may install Ops Reporter before Risk Engine, or Risk Engine may fail on a specific carrier. The report should never fail completely -- it should produce the best output possible with available data and clearly indicate what is missing. This is a UX principle: partial information is better than an error. |
| 2026-02-26 | CSV headers use lowercase with underscores | Compatibility with TMS import tools and database columns. Most TMS systems expect snake_case or lowercase headers. Using the same field naming convention as the SearchCarriers API avoids mapping confusion. |
| 2026-02-26 | Section builders are independent pure functions | Testability. Each section can be tested independently with mock data. The report assembler composes sections, but each section is self-contained. This also enables future customization: users could opt to include/exclude specific sections. |
| 2026-02-26 | Documentation written before implementation | Same documentation-first approach as Carrier Intel and Risk Engine. The 6-doc set serves as the specification. Report templates, comparison metrics, CSV headers, and error handling behaviors are all defined before writing code. |

## Release History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-26 | Initial plugin scaffold: plugin.json, .mcp.json, 6-doc enterprise documentation set |
| 0.2.0 | -- | MCP server with 4 tools, report generator, comparison engine, export formatter, fleet formatter |
| 0.3.0 | -- | Commands, embedded skill, agent, comprehensive test suite |
| 0.4.0 | -- | Full pipeline integration validation (Carrier Intel -> Risk Engine -> Ops Reporter) |
| 0.5.0 | -- | Custom report templates, PDF export, batch reporting |
| 1.0.0 | -- | Production release: fully tested, validated, documented, inventory updated |
