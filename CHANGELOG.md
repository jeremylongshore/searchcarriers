# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-26

### Added

#### Foundation (Phase 1-2)
- Repository structure, CI/CD, core configuration
- 6-doc enterprise planning templates (Business Case through Status)
- Inventory tracking CSVs for plugins and skills
- Single validation script (`scripts/validate.sh`)
- Developer onboarding script (`scripts/setup-dev.sh`)
- GitHub Actions CI workflow (tiered: validate + test)
- API discovery documentation with 11 confirmed endpoints

#### 14 Standalone Skills (Phase 3)
- Search & Discovery: carrier-lookup (Free), vin-decoder (Pro), entity-mapper (Pro)
- Safety & Compliance: safety-scorer (Free), inspection-analyzer (Pro), compliance-monitor (Pro)
- Vetting & Risk: insurance-validator (Pro), authority-checker (Free), vetting-rules (Pro+), fraud-detector (Pro)
- Operations: bulk-processor (SMB), data-exporter (Pro), contact-verifier (Pro), tms-connector (Enterprise)

#### Stackable Pipeline (Phases 4-6)
- **searchcarriers-carrier-intel** (INPUT): 4 MCP tools (carrier_lookup, carrier_profile, entity_map, fleet_summary), auto-detect search type, slash commands (/sc-lookup, /sc-profile), carrier-analyst agent
- **searchcarriers-risk-engine** (ANALYSIS): 4 MCP tools (risk_score, vetting_check, insurance_check, compliance_audit), 7-factor risk scoring algorithm, configurable vetting rules with PASS/REVIEW/FAIL verdicts, slash commands (/sc-risk, /sc-vet), risk-analyst agent
- **searchcarriers-ops-reporter** (OUTPUT): 4 MCP tools (generate_report, generate_fleet, generate_compare, export_data), professional vetting reports, side-by-side carrier comparison, multi-format export (JSON/CSV/Markdown), slash commands (/sc-report, /sc-compare), ops-reporter agent
- Shared tier gating utility (`plugins/shared/tier_gate.py`)
- Pipeline output contracts (`_pipeline` envelope in all tool responses)

#### Standalone Plugins (Phases 7-8)
- **searchcarriers-watchdog** (MONITORING): 4 MCP tools (manage_watchlist, get_alerts, route_alert, monitor_compliance), multi-channel alert routing (Slack/Telegram/email/webhook), compliance drift detection, slash commands (/sc-watch, /sc-alerts), watchdog-monitor agent
- **searchcarriers-api-bridge** (INTEGRATION): 4 MCP tools (api_health, bulk_lookup, tms_sync, webhook_manage), batch processing up to 100 carriers, TMS field mapping (generic/McLeod/TMW/DAT), local webhook config, slash commands (/sc-api, /sc-bulk), integration-manager agent

#### Per-Plugin Enterprise Documentation
- Complete 6-doc set (Business Case, PRD, Architecture, User Journey, Technical Spec, Status) for all 5 plugins
- Embedded SKILL.md, agent definition, and SCHEMA.md per plugin
