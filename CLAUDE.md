# SearchCarriers CLAUDE.md

Motor carrier research platform plugin + skills repo. 5 MCP plugins (3 stackable pipeline + 2 standalone), 14 standalone skills. 4M+ companies. BSL 1.1 — production use requires active SearchCarriers subscription.

## API Reference

- **Base URL**: `https://searchcarriers.com/api/v1`
- **Auth**: `Authorization: Bearer $SEARCHCARRIERS_API_KEY`
- **Carrier object**: 143 fields (identity, contact, fleet, operations, safety, cargo)
- **Rate limit**: ~3 req/s, cache 5 min TTL, respect `Retry-After`

### Endpoints

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/search` | GET | `superSearchTerm`, `dotNumber`, `mcNumber`, `legalName`, VIN, filters |
| `/search/scac` | GET | SCAC code lookup |
| `/company/{dot}/inspections` | GET | Paginated, 58+ fields per inspection |
| `/company/{dot}/authorities` | GET | Broker/contract/common authority status |
| `/company/{dot}/insurances` | GET | Paginated insurance records |
| `/company/{dot}/equipment` | GET | VIN, make, model, GVWR detail |
| `/company/{dot}/vehicles` | GET | Simplified vehicle list |
| `/company/{dot}/out-of-service-orders` | GET | Paginated OOS history |
| `/company/{dot}/watch` | GET/POST | Carrier Watch add/check |
| `/authority/{dot}/history` | GET | Authority status change history |
| `/export` | GET | Bulk export: `dot_numbers[]` + `file_format` |

## Directory Layout

```
plugins/          5 MCP server plugins (carrier-intel, risk-engine, ops-reporter, watchdog, api-bridge)
skills/           14 standalone skills in 4 categories (search-discovery, safety-compliance, vetting-risk, operations)
scripts/          validate.sh, setup-dev.sh
tests/            pytest suite (test_plugins.py, test_skills.py, conftest.py)
templates/        6-doc enterprise planning templates (01-BUSINESS-CASE through 06-STATUS)
inventory/        plugins_inventory.csv, skills_inventory.csv
```

## Conventions

- **Skill naming**: `searchcarriers-{name}`, kebab-case, max 64 chars
- **Skill descriptions**: max 200 chars, third person, "Use when" pattern
- **File refs in skills**: always `{baseDir}/`, never absolute paths
- **Bash scoping**: `Bash(python:*)` not raw `Bash`
- **Tier gating**: every MCP tool declares its min tier
- **Plugin docs**: 6-doc set lives in each plugin's `docs/` directory
- **API wrappers**: thin wrappers only — don't reproduce API logic
- **Value-add**: intelligence, interpretation, natural language, reports, comparisons

## Tier Order

`free` → `basic` → `pro` → `proplus` → `smb` → `enterprise`

```python
TIER_ORDER = ["free", "basic", "pro", "proplus", "smb", "enterprise"]
```

## Plugin Pipeline

```
Carrier Intel (INPUT, free+) → Risk Engine (ANALYSIS, pro+) → Ops Reporter (OUTPUT, pro+)
```

Standalone: Watchdog (pro+), API Bridge (smb+)

## Plugin Development Workflow

1. Copy `templates/` into `plugins/{name}/docs/`
2. Write MCP server in `plugins/{name}/scripts/`
3. Add tier gating per tool (Layer 2 check in every tool handler)
4. Write `commands/` (slash commands)
5. Write embedded `skills/{name}/SKILL.md`
6. Update `inventory/` CSVs
7. Test: `./scripts/validate.sh`

## Skill Body Structure

Required sections in every SKILL.md:

```
## Overview
## Prerequisites        (include min tier)
## Instructions         (use {baseDir}/ for file refs)
## Examples             (real freight scenarios)
## Error Handling       (tier gating, API errors)
## Resources            (related skills, SC docs)
```

## Validation

```bash
./scripts/validate.sh --verbose       # Full validation
./scripts/validate.sh --skills-only   # Skills only
pytest -v                             # Python tests
```

## Ecosystem

Full ecosystem context: `/home/jeremy/000-projects/000-ecosystem/CLAUDE.md`
