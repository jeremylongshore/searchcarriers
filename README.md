# SearchCarriers Plugins + Skills

**Motor carrier intelligence for Claude Code.**

Search, vet, and monitor 4M+ motor carriers directly from your terminal. Five plugins and fourteen skills turn raw FMCSA data into actionable freight intelligence -- carrier lookups, risk scoring, vetting reports, compliance monitoring, and TMS integration, all through natural language.

Built for freight brokers, safety teams, and logistics ops who need answers, not dashboards.

---

## Quick Start

Up and running in under 2 minutes:

```bash
git clone https://github.com/intent-solutions-io/searchcarriers.git
cd searchcarriers && ./scripts/setup-dev.sh
```

Set your API key:

```bash
export SEARCHCARRIERS_API_KEY="your_id|your_token"
```

Then try your first lookup in Claude Code:

```
/sc-lookup JB Hunt
```

---

## Plugin Catalog

| Plugin | Type | Pipeline Stage | Min Tier | Description |
|--------|------|----------------|----------|-------------|
| `searchcarriers-carrier-intel` | Stackable (INPUT) | Data retrieval | Free | Carrier lookup, entity mapping, fleet summary, SCAC/VIN resolution |
| `searchcarriers-risk-engine` | Stackable (ANALYSIS) | Risk assessment | Pro | Risk scoring, vetting checks, insurance validation, compliance audit |
| `searchcarriers-ops-reporter` | Stackable (OUTPUT) | Reporting | Pro | Vetting reports, fleet reports, carrier comparisons, data export |
| `searchcarriers-watchdog` | Standalone | Monitoring | Pro+ | Carrier watch management, alert routing (Slack/Telegram/email), compliance drift detection |
| `searchcarriers-api-bridge` | Standalone | Integration | SMB | Bulk carrier operations, TMS sync, webhook management, API health checks |

---

## Stackable Pipeline

The three stackable plugins chain together automatically. Claude routes data through the pipeline without manual intervention.

```
                        STACKABLE PIPELINE
  ================================================================

  +-----------------------+     +------------------------+     +-------------------------+
  |   CARRIER INTEL       |     |   RISK ENGINE          |     |   OPS REPORTER          |
  |   (INPUT)             |---->|   (ANALYSIS)           |---->|   (OUTPUT)              |
  |                       |     |                        |     |                         |
  |   carrier_lookup      |     |   risk_score           |     |   generate_report       |
  |   carrier_profile     |     |   vetting_check        |     |   generate_fleet        |
  |   entity_map          |     |   insurance_check      |     |   generate_compare      |
  |   fleet_summary       |     |   compliance_audit     |     |   export_data           |
  |                       |     |                        |     |                         |
  |   Min: Free           |     |   Min: Pro             |     |   Min: Pro              |
  +-----------------------+     +------------------------+     +-------------------------+

  Example: "/sc-lookup KLLM" --> carrier data --> risk assessment --> formatted vetting report
```

**Standalone plugins** operate independently:

```
  +------------------------+     +-------------------------+
  |   WATCHDOG             |     |   API BRIDGE            |
  |   (MONITORING)         |     |   (INTEGRATION)         |
  |                        |     |                         |
  |   manage_watchlist     |     |   api_health            |
  |   get_alerts           |     |   bulk_lookup           |
  |   route_alert          |     |   tms_sync              |
  |   monitor_compliance   |     |   webhook_manage        |
  |                        |     |                         |
  |   Min: Pro+            |     |   Min: SMB              |
  +------------------------+     +-------------------------+
```

---

## Skill Catalog

14 skills organized by category. Each skill is a standalone `.md` file that teaches Claude domain-specific freight intelligence.

### Search & Discovery

| Skill | Trigger Phrases | Description |
|-------|----------------|-------------|
| `searchcarriers-carrier-lookup` | "look up carrier", "find DOT", "search MC number" | Search carriers by DOT, MC, name, or SCAC from 4M+ companies |
| `searchcarriers-vin-decoder` | "decode VIN", "VIN lookup", "who owns this truck" | Resolve VINs to owning carriers and equipment details |
| `searchcarriers-entity-mapper` | "map entity", "related companies", "corporate family" | Map relationships between carriers, brokers, and shippers |

### Safety & Compliance

| Skill | Trigger Phrases | Description |
|-------|----------------|-------------|
| `searchcarriers-safety-scorer` | "safety score", "how safe is", "rate this carrier" | Interpret safety ratings, crash rates, and BASIC scores into plain-language assessments |
| `searchcarriers-inspection-analyzer` | "analyze inspections", "violation history", "OOS rate" | Analyze inspection history, violation patterns, and out-of-service trends |
| `searchcarriers-compliance-monitor` | "compliance check", "authority status", "operating authority" | Monitor authority status, insurance requirements, and regulatory compliance |

### Vetting & Risk

| Skill | Trigger Phrases | Description |
|-------|----------------|-------------|
| `searchcarriers-insurance-validator` | "check insurance", "coverage valid", "insurance status" | Validate insurance coverage, detect lapses, verify policy requirements |
| `searchcarriers-authority-checker` | "check authority", "authority history", "revocation history" | Verify operating authority status and track authority change history |
| `searchcarriers-vetting-rules` | "vet this carrier", "vetting criteria", "pass/fail rules" | Apply custom vetting rules with configurable thresholds (min power units, max crash rate, etc.) |
| `searchcarriers-fraud-detector` | "fraud check", "red flags", "suspicious carrier" | Detect fraud indicators: chameleon carriers, new authorities post-revocation, address anomalies |

### Operations

| Skill | Trigger Phrases | Description |
|-------|----------------|-------------|
| `searchcarriers-bulk-processor` | "bulk lookup", "batch carriers", "process CSV" | Batch-process carrier lists from CSV with structured results |
| `searchcarriers-data-exporter` | "export data", "download report", "generate CSV" | Export carrier data in multiple formats (JSON, CSV, Markdown) |
| `searchcarriers-contact-verifier` | "verify contact", "check phone", "validate email" | Cross-reference carrier contact information against FMCSA records |
| `searchcarriers-tms-connector` | "sync TMS", "push to TMS", "TMS update" | Push/pull carrier data to TMS platforms on status changes |

---

## Tier Matrix

Features available at each SearchCarriers subscription tier:

| Feature | Free | Basic | Pro | Pro+ | SMB | Enterprise |
|---------|:----:|:-----:|:---:|:----:|:---:|:----------:|
| **Carrier Lookup** | x | x | x | x | x | x |
| **Search (DOT/MC/name)** | x | x | x | x | x | x |
| **SCAC Lookup** | x | x | x | x | x | x |
| **VIN Decoder** | - | - | x | x | x | x |
| **Entity Mapper** | - | - | x | x | x | x |
| **Carrier Profile** | - | x | x | x | x | x |
| **Safety Scorer** | x | x | x | x | x | x |
| **Inspection Analyzer** | - | - | x | x | x | x |
| **Compliance Monitor** | - | - | x | x | x | x |
| **Risk Scoring** | - | - | x | x | x | x |
| **Insurance Validator** | - | - | x | x | x | x |
| **Vetting Rules** | - | - | - | x | x | x |
| **Authority Checker** | x | x | x | x | x | x |
| **Fraud Detector** | - | - | x | x | x | x |
| **Vetting Reports** | - | - | x | x | x | x |
| **Carrier Comparison** | - | - | x | x | x | x |
| **Data Export** | - | - | x | x | x | x |
| **Carrier Watch** | - | - | - | x | x | x |
| **Alert Routing (Slack/Telegram)** | - | - | - | x | x | x |
| **Compliance Dashboard** | - | - | - | x | x | x |
| **Contact Verifier** | - | - | x | x | x | x |
| **Bulk Processor** | - | - | - | - | x | x |
| **TMS Sync** | - | - | - | - | - | x |
| **Webhook Management** | - | - | - | - | x | x |
| **Fleet Risk Dashboard** | - | - | - | - | - | x |
| **Automated Onboarding** | - | - | - | - | - | x |

Tier gating is enforced at three layers: MCP server startup (API key check), per-tool tier validation (returns upgrade URL if insufficient), and skill prerequisites (documented in each SKILL.md).

---

## API Reference Summary

| | |
|---|---|
| **Base URL** | `https://searchcarriers.com/api/v1` |
| **Auth** | `Authorization: Bearer {id}\|{token}` (Laravel Sanctum) |
| **Rate Limit** | ~3 req/s recommended, respect `Retry-After` header |
| **Pagination** | Laravel standard, max 1000 results |

### Key Endpoints

| Endpoint | Method | Path |
|----------|--------|------|
| Super Search | GET | `/api/v1/search` |
| SCAC Lookup | GET | `/api/v1/search/scac` |
| Inspections | GET | `/api/v1/company/{dot}/inspections` |
| Insurances | GET | `/api/v1/company/{dot}/insurances` |
| Authorities | GET | `/api/v1/company/{dot}/authorities` |
| OOS Orders | GET | `/api/v1/company/{dot}/out-of-service-orders` |
| Equipment | GET | `/api/v1/company/{dot}/equipment` |
| Vehicles | GET | `/api/v1/company/{dot}/vehicles` |
| Authority History | GET | `/api/v1/authority/{dot}/history` |
| Export | GET | `/api/v1/export` |
| Carrier Watch | GET/POST | `/api/v1/company/{dot}/watch` |

Full API documentation, schemas, and field references: **[API-DISCOVERY.md](API-DISCOVERY.md)**

---

## Premium Workflows

Paid add-on workflows that chain multiple plugins together for automated intelligence.

### Pro Tier

| Workflow | What It Does | Plugins Used |
|----------|-------------|--------------|
| Daily Vetting Digest | Auto-vet all watched carriers, email pass/review/fail summary | ops-reporter + watchdog |
| Inspection Alert Email | New inspection on a watched carrier triggers formatted email summary | watchdog |
| Risk Score Change Alerts | Push notification when a carrier's safety rating changes | risk-engine + watchdog |

### Pro+ Tier

| Workflow | What It Does | Plugins Used |
|----------|-------------|--------------|
| Slack Carrier Watch | Route all Carrier Watch alerts to Slack with formatted cards | watchdog |
| Telegram Bot Lookup | `/dot 12345` in Telegram returns carrier summary | carrier-intel + api-bridge |
| Compliance Dashboard Email | Weekly compliance report across all watched carriers | ops-reporter + watchdog |
| Insurance Lapse Alert | Instant Slack/email when insurance cancellation is detected | watchdog + risk-engine |

### SMB / Enterprise Tier

| Workflow | What It Does | Plugins Used |
|----------|-------------|--------------|
| Bulk Vetting Pipeline | Upload CSV of 500+ carriers, get back vetting report with pass/fail | api-bridge + risk-engine + ops-reporter |
| TMS Auto-Sync | Carrier status change auto-updates carrier record in TMS | api-bridge + watchdog |
| Fleet Risk Dashboard | Automated weekly fleet risk analysis pushed to Slack/email | carrier-intel + risk-engine + ops-reporter + watchdog |
| Competitive Intel | Monitor competitor carrier panels, alert on changes | carrier-intel + watchdog |
| Automated Onboarding | New carrier added to TMS triggers full vetting pipeline, results emailed to ops | api-bridge + risk-engine + ops-reporter |

---

## First 10 Minutes

What a new user does after cloning:

**Minute 0-1: Clone and setup.**

```bash
git clone https://github.com/intent-solutions-io/searchcarriers.git
cd searchcarriers && ./scripts/setup-dev.sh
```

The setup script installs dependencies, validates your environment, and confirms everything is wired correctly.

**Minute 1-2: Configure your API key.**

Get your key from [searchcarriers.com/settings/api](https://searchcarriers.com/settings/api), then:

```bash
export SEARCHCARRIERS_API_KEY="your_id|your_token"
```

Add it to your `.env` file for persistence (see `.env.example`).

**Minute 2-4: Run your first carrier lookup.**

Open Claude Code and try:

```
/sc-lookup Werner Enterprises
```

You should see carrier identity, contact info, fleet size, and operating authority pulled from 4M+ companies.

**Minute 4-6: Try a carrier profile.**

Get the full picture for a carrier by DOT number:

```
/sc-profile 69494
```

This pulls search results, insurance, authority status, and equipment data into a single view.

**Minute 6-8: Score a carrier's risk (Pro tier).**

```
/sc-risk 69494
```

The risk engine interprets raw safety data into a plain-language risk assessment with pass/review/fail recommendation.

**Minute 8-10: Generate a vetting report (Pro tier).**

```
/sc-report 69494
```

Produces a formatted vetting report combining carrier data, risk scores, and compliance status -- ready to share with your ops team.

**What's next:** Add carriers to your watch list with `/sc-watch`, set up Slack alerts, or bulk-process a CSV of carriers with `/sc-bulk`.

---

## Development

### Validate

Run the single validation script to check all plugins and skills:

```bash
./scripts/validate.sh --verbose
```

This validates:
- Plugin manifest (`plugin.json`) required fields
- SKILL.md frontmatter (name format, description length, allowed tools)
- No absolute paths in skills (must use `{baseDir}/`)
- Bash tool scoping (`Bash(python:*)` not raw `Bash`)
- Secret scanning

### Test

```bash
pytest -v
```

Tests cover plugin structure validation, skill spec compliance, and MCP server responses.

### Project Structure

```
searchcarriers/
├── plugins/                     # 5 Claude Code plugins
│   ├── searchcarriers-carrier-intel/    # Stackable: INPUT
│   ├── searchcarriers-risk-engine/      # Stackable: ANALYSIS
│   ├── searchcarriers-ops-reporter/     # Stackable: OUTPUT
│   ├── searchcarriers-watchdog/         # Standalone: MONITORING
│   └── searchcarriers-api-bridge/       # Standalone: INTEGRATION
├── skills/                      # 14 standalone skills
│   ├── search-discovery/        # 3 skills
│   ├── safety-compliance/       # 3 skills
│   ├── vetting-risk/            # 4 skills
│   └── operations/              # 4 skills
├── scripts/
│   ├── validate.sh              # Single validator
│   └── setup-dev.sh             # Onboarding script
├── templates/                   # 6-doc enterprise planning templates
├── inventory/                   # Plugin + skill tracking CSVs
├── tests/                       # pytest suite
├── API-DISCOVERY.md             # Full API reference
├── MASTER-BLUEPRINT.md          # Architecture decisions
├── CHANGELOG.md
├── VERSION                      # 0.1.0
└── LICENSE                      # BSL 1.1
```

### Contributing

Each plugin contains its own `docs/` directory with a 6-document enterprise planning set (Business Case, PRD, Architecture, User Journey, Technical Spec, Status). Start there to understand the design intent before making changes.

Skills follow the `/skill-creator` specification. Required sections in every SKILL.md:

```
## Overview
## Prerequisites        (include API tier requirement)
## Instructions         (use {baseDir}/ for file references)
## Examples             (real freight scenarios)
## Error Handling
## Resources
```

---

## Architecture Note

**Thin wrapper + thick intelligence.**

Our MCP servers are thin API callers. They hit SearchCarriers endpoints and return raw data. No business logic duplication. No data transformation. Thin.

Our skills are where the value lives. They teach Claude how to interpret raw FMCSA data ("is this carrier safe?" not just numbers), chain lookups into pipelines (search -> inspect -> assess -> report), apply custom vetting rules (min power units, max crash rate), format human-readable reports from 143-field carrier objects, and make pass/review/fail decisions that turn data into judgment.

The API gives you data. We give you intelligence.

---

## License

This project is licensed under the [Business Source License 1.1](LICENSE).

**Usage grant**: You may use, copy, and modify this software for development, testing, and internal evaluation. Production use requires an active [SearchCarriers](https://searchcarriers.com) subscription at the appropriate tier.

Copyright (c) 2026 Intent Solutions, LLC. All rights reserved.
