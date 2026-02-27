---
name: searchcarriers-compliance-dashboard
description: >-
  Generate a weekly compliance report across all watched carriers with
  drift tracking and email delivery. Use when auditing compliance.
allowed-tools: "Read,Grep,Bash(python:*)"
metadata:
  author: "Jeremy Longshore <jeremy@intentsolutions.io>"
  version: 0.1.0
  license: BUSL-1.1
  tier: proplus
---

# Compliance Dashboard Email -- Workflow Skill

## Overview

This workflow orchestrates three plugins into a comprehensive weekly compliance reporting pipeline. It retrieves the full carrier watch list, runs a compliance audit on each carrier through the Risk Engine, monitors compliance drift through the Watchdog, generates a formatted dashboard report through the Ops Reporter, aggregates individual carrier results into a single consolidated dashboard, and delivers the final report via email.

Compliance drift is insidious. A carrier that was fully qualified six months ago may have silently accumulated MCS-150 staleness, authority anomalies, or insurance filing gaps. This workflow surfaces those changes systematically so your compliance team can act before regulatory issues become operational emergencies.

**Cross-plugin orchestration**: This workflow bridges three plugins:
- **searchcarriers-watchdog** -- provides `manage_watchlist` (carrier roster) and `monitor_compliance` (drift detection) and `route_alert` (email delivery)
- **searchcarriers-risk-engine** -- provides `compliance_audit` (per-carrier regulatory audit)
- **searchcarriers-ops-reporter** -- provides `generate_report` (formatted report output) and `export_data` (structured data export)

**Pipeline position**: Watchdog (MONITORING) + Risk Engine (ANALYSIS) + Ops Reporter (OUTPUT) -> Compliance Dashboard (WORKFLOW)

## Prerequisites

- **Minimum tier**: Pro Plus
- MCP servers `searchcarriers-watchdog`, `searchcarriers-risk-engine`, and `searchcarriers-ops-reporter` must all be running and accessible.
- `SEARCHCARRIERS_API_KEY` environment variable set with a valid Pro Plus or Enterprise key.
- At least one carrier must be on the watch list. Use `/sc-watch add {DOT}` to populate.
- Email delivery must be configured at `searchcarriers.com/settings/notifications` with a valid recipient address.
- `python3` must be available in the execution environment.

## Instructions

### Step 1: Retrieve the Full Watch List

Call the `manage_watchlist` MCP tool with `action: "list"` to retrieve all monitored carriers. Unlike the Insurance Lapse Alert workflow, this dashboard includes carriers in ALL monitoring states to provide a complete compliance picture.

```python
import json
from datetime import datetime, timedelta
from collections import Counter

# Call manage_watchlist(action="list")
# Returns: carriers[], each with dot_number, carrier_name, monitoring_state,
#   added_date, alert_count

def get_full_watchlist(response):
    carriers = response.get("carriers", [])

    by_state = {
        "ACTIVE": [],
        "PAUSED": [],
        "STALE": [],
        "BASELINE": []
    }

    for c in carriers:
        state = c.get("monitoring_state", "ACTIVE")
        by_state.setdefault(state, []).append(c)

    return carriers, by_state
```

All carriers are included in the dashboard regardless of state. PAUSED and STALE carriers are flagged with their state in the report so the compliance team can decide whether to resume or remove them.

### Step 2: Run Compliance Audit for Each Carrier

For each carrier on the watch list, call the `compliance_audit` MCP tool from the Risk Engine plugin. This tool evaluates MCS-150 filing currency, authority standing, insurance compliance, and registration completeness, then assigns a letter grade (A through F).

```python
# compliance_audit returns per carrier via _pipeline.data:
#   grade: A | B | C | D | F
#   mcs150_current: bool
#   mcs150_age_months: int
#   authority_clean: bool
#   insurance_compliant: bool
#   registration_complete: bool
#   issues: list of {dimension, severity, description}

GRADE_WEIGHTS = {
    "A": 4,  # Fully compliant
    "B": 3,  # Minor issues
    "C": 2,  # Moderate issues
    "D": 1,  # Serious non-compliance
    "F": 0   # Critical non-compliance
}

def run_compliance_audits(carriers):
    results = []

    for carrier in carriers:
        dot = carrier["dot_number"]
        name = carrier["carrier_name"]
        state = carrier.get("monitoring_state", "ACTIVE")

        audit = {
            "dot_number": dot,
            "carrier_name": name,
            "monitoring_state": state,
            "compliance": None,
            "error": None
        }

        # Skip STALE carriers -- their data may be unreliable
        if state == "STALE":
            audit["error"] = "Skipped: monitoring state is STALE"
            results.append(audit)
            continue

        try:
            # MCP call: compliance_audit(dot_number=dot)
            # audit["compliance"] = response["_pipeline"]["data"]
            pass
        except Exception as e:
            audit["error"] = str(e)

        results.append(audit)

    return results
```

Process carriers sequentially to respect API rate limits. For watch lists with more than 20 carriers, add a 500ms delay between calls to avoid 429 rate limits.

### Step 3: Monitor Compliance Drift for Each Carrier

For each carrier that has a previous baseline (not in BASELINE state), call the `monitor_compliance` MCP tool from the Watchdog plugin. This tool compares the current compliance posture against the baseline captured when monitoring began, producing a drift score across five dimensions.

```python
# monitor_compliance returns:
#   composite_drift_score: int (0-15)
#   drift_status: STABLE | DRIFTING | DEGRADING | CRITICAL_DRIFT
#   dimensions: {
#     insurance_posture: {score: 0-3, detail: str},
#     authority_standing: {score: 0-3, detail: str},
#     safety_rating: {score: 0-3, detail: str},
#     filing_currency: {score: 0-3, detail: str},
#     operational_profile: {score: 0-3, detail: str}
#   }

DRIFT_THRESHOLDS = {
    "STABLE":         {"min": 0,  "max": 2,  "action": "No action required"},
    "DRIFTING":       {"min": 3,  "max": 5,  "action": "Review carrier status"},
    "DEGRADING":      {"min": 6,  "max": 9,  "action": "Re-evaluate qualification"},
    "CRITICAL_DRIFT": {"min": 10, "max": 15, "action": "Immediate review required"}
}

def check_drift(carriers, audit_results):
    drift_results = []

    for carrier in carriers:
        state = carrier.get("monitoring_state", "ACTIVE")

        # Skip carriers without a baseline
        if state == "BASELINE":
            drift_results.append({
                "dot_number": carrier["dot_number"],
                "carrier_name": carrier["carrier_name"],
                "drift": None,
                "note": "Baseline pending -- first comparison not yet available"
            })
            continue

        if state == "STALE":
            drift_results.append({
                "dot_number": carrier["dot_number"],
                "carrier_name": carrier["carrier_name"],
                "drift": None,
                "note": "Stale monitoring -- drift unavailable"
            })
            continue

        try:
            # MCP call: monitor_compliance(dot_number=carrier["dot_number"])
            # drift_results.append({...with drift data...})
            pass
        except Exception as e:
            drift_results.append({
                "dot_number": carrier["dot_number"],
                "carrier_name": carrier["carrier_name"],
                "drift": None,
                "note": f"Drift check failed: {str(e)}"
            })

    return drift_results
```

### Step 4: Generate Per-Carrier Compliance Sections

For each carrier with a successful audit, call the `generate_report` MCP tool from the Ops Reporter plugin to produce a formatted compliance section. Request only the compliance-relevant sections to keep the dashboard focused.

```python
# generate_report is called with a focused section list
# We request only: carrier_profile, authority_insurance, safety_compliance
# The full vetting report is not needed for the compliance dashboard

def generate_carrier_sections(audit_results, drift_results):
    sections = []

    for audit, drift in zip(audit_results, drift_results):
        if audit["error"]:
            sections.append({
                "dot_number": audit["dot_number"],
                "carrier_name": audit["carrier_name"],
                "section": None,
                "error": audit["error"]
            })
            continue

        # MCP call: generate_report(
        #   dot_number=audit["dot_number"],
        #   sections=["carrier_profile", "authority_insurance", "safety_compliance"],
        #   format="markdown"
        # )

        # Combine audit grade, issues, and drift into a unified section
        section = {
            "dot_number": audit["dot_number"],
            "carrier_name": audit["carrier_name"],
            "grade": audit["compliance"]["grade"],
            "issues": audit["compliance"].get("issues", []),
            "drift_status": drift.get("drift", {}).get("drift_status", "N/A") if drift.get("drift") else "N/A",
            "drift_score": drift.get("drift", {}).get("composite_drift_score", 0) if drift.get("drift") else 0,
            "dimensions": drift.get("drift", {}).get("dimensions", {}) if drift.get("drift") else {},
            "report_section": None  # populated by generate_report response
        }

        sections.append(section)

    return sections
```

### Step 5: Aggregate into the Compliance Dashboard

Combine all per-carrier sections into a single dashboard document with executive summary, grade distribution, drift overview, per-carrier detail, and action items.

```
WEEKLY COMPLIANCE DASHBOARD
Generated:    {timestamp}
Period:       {week_start} to {week_end}
Carriers:     {total_count} monitored ({active} active, {paused} paused, {stale} stale)

EXECUTIVE SUMMARY
  Fleet compliance GPA:  {weighted_average_grade} (scale: 4.0 = A, 0.0 = F)
  Carriers at risk:      {count_grade_D_or_F}
  Drift warnings:        {count_drifting_or_worse}
  Action items:          {total_action_items}

GRADE DISTRIBUTION
| Grade | Count | Carriers |
|-------|-------|----------|
| A     | {n}   | {carrier_names} |
| B     | {n}   | {carrier_names} |
| C     | {n}   | {carrier_names} |
| D     | {n}   | {carrier_names} |
| F     | {n}   | {carrier_names} |

COMPLIANCE DRIFT OVERVIEW
| Status         | Count | Action Required |
|----------------|-------|-----------------|
| STABLE         | {n}   | None |
| DRIFTING       | {n}   | Review carrier status |
| DEGRADING      | {n}   | Re-evaluate qualification |
| CRITICAL DRIFT | {n}   | Immediate review required |

TOP ISSUES (sorted by severity)
| # | Severity | DOT     | Carrier              | Issue                         |
|---|----------|---------|----------------------|-------------------------------|
| 1 | CRITICAL | {dot}   | {name}               | {issue_description}           |
| 2 | HIGH     | {dot}   | {name}               | {issue_description}           |
| ...                                                                              |

CARRIER DETAIL
{for each carrier, sorted by grade ascending (worst first)}
---
DOT {dot_number} -- {carrier_name}
  Compliance Grade:    {grade}
  Drift Status:        {drift_status} (score: {drift_score}/15)
  MCS-150 Current:     {yes/no} ({age} months)
  Authority Clean:     {yes/no}
  Insurance Compliant: {yes/no}
  Registration:        {complete/incomplete}

  Issues:
  {for each issue}
  - [{severity}] {description}
  {end for}

  Drift Dimensions:
  | Dimension            | Score | Detail |
  |----------------------|-------|--------|
  | Insurance Posture    | {0-3} | {detail} |
  | Authority Standing   | {0-3} | {detail} |
  | Safety Rating        | {0-3} | {detail} |
  | Filing Currency      | {0-3} | {detail} |
  | Operational Profile  | {0-3} | {detail} |
{end for}

{if paused_carriers}
PAUSED CARRIERS (not actively monitored)
| DOT     | Carrier              | Paused Since |
|---------|----------------------|--------------|
| {dot}   | {name}               | {date}       |
Consider resuming or removing these carriers.
{end if}

{if stale_carriers}
STALE CARRIERS (check failures)
| DOT     | Carrier              | Stale Since |
|---------|----------------------|-------------|
| {dot}   | {name}               | {date}      |
Investigate connectivity: `/sc-watch refresh {DOT}`
{end if}

ACTION ITEMS
{numbered list of recommended actions, derived from findings}
1. [CRITICAL] DOT {dot} -- {action_description}
2. [HIGH] DOT {dot} -- {action_description}
...

REPORT FOOTER
Generated by SearchCarriers Compliance Dashboard Workflow v0.1.0
Next scheduled report: {next_week_date}
Manage watch list: /sc-watch | View alerts: /sc-alerts
```

```python
def calculate_fleet_gpa(sections):
    """Calculate weighted average compliance grade across all carriers."""
    total_weight = 0
    total_score = 0

    for section in sections:
        if section.get("grade"):
            score = GRADE_WEIGHTS.get(section["grade"], 0)
            total_score += score
            total_weight += 1

    if total_weight == 0:
        return "N/A"

    gpa = total_score / total_weight
    return f"{gpa:.2f}"
```

### Step 6: Deliver the Dashboard via Email

Call the `route_alert` MCP tool from the Watchdog plugin with `channel: "email"` to deliver the completed dashboard. The dashboard is sent as a formatted HTML email with the markdown report rendered.

```python
def deliver_dashboard(dashboard_content, export_data=None):
    """Route the completed dashboard via email."""

    # Primary delivery: formatted dashboard email
    email_params = {
        "alert_id": f"compliance_dashboard_{datetime.utcnow().strftime('%Y%m%d')}",
        "channel": "email",
        "payload": {
            "subject": f"[SearchCarriers] Weekly Compliance Dashboard -- {datetime.utcnow().strftime('%Y-%m-%d')}",
            "body": dashboard_content,
            "format": "markdown",
            "priority": "normal"
        }
    }

    # MCP call: route_alert(email_params)

    # Optional: attach CSV export for spreadsheet analysis
    if export_data:
        # MCP call: export_data(format="csv", data=export_data)
        # Attach CSV to the email payload
        pass

    return {"status": "delivered", "channel": "email"}
```

Optionally, also call `export_data` from Ops Reporter with `format: "csv"` to attach a machine-readable compliance matrix to the email for import into spreadsheets or compliance tracking systems.

## Examples

### Example 1: Weekly Compliance Report

**User prompt**: "Generate the weekly compliance dashboard and email it"

1. Call `manage_watchlist` -- returns 15 carriers (13 active, 1 paused, 1 stale).
2. Run `compliance_audit` on 14 carriers (skip stale) -- grades: 5 A, 4 B, 3 C, 1 D, 1 F.
3. Run `monitor_compliance` on 13 active carriers -- 10 stable, 2 drifting, 1 degrading.
4. Call `generate_report` for compliance sections on each carrier.
5. Aggregate into dashboard: GPA 2.73, 2 carriers at risk (D and F), 3 drift warnings.
6. Route via `route_alert` with `channel: "email"`.
7. Display: "Compliance dashboard generated and emailed. Fleet GPA: 2.73. 2 carriers at risk. 3 drift warnings. See email for full detail."

### Example 2: Compliance Audit Only (No Email)

**User prompt**: "Run compliance audit on all watched carriers"

1. Retrieve watch list and run compliance audits.
2. Generate the dashboard report and display it inline.
3. Do not route via email.
4. Offer: "Run this workflow with `--email` to deliver the dashboard to your configured email address."

### Example 3: Single Carrier Compliance Deep Dive

**User prompt**: "Show compliance detail for DOT 1234567"

1. Verify DOT 1234567 is on the watch list.
2. Run `compliance_audit` for that single carrier -- grade C with 3 issues.
3. Run `monitor_compliance` -- drift status DRIFTING (score 4/15).
4. Display the carrier detail section from the dashboard format.
5. Suggest: "Run `/sc-risk 1234567` for full risk assessment or `/sc-vet 1234567` to check qualification status."

### Example 4: Dashboard with CSV Export

**User prompt**: "Generate compliance dashboard with spreadsheet export"

1. Run the full workflow (Steps 1-5).
2. Call `export_data` with `format: "csv"` containing the compliance matrix (DOT, name, grade, drift status, issues count, MCS-150 age, authority status, insurance status).
3. Deliver dashboard email with CSV attachment.
4. Display: "Dashboard emailed with CSV attachment. 15 carriers audited. CSV contains the compliance matrix for spreadsheet import."

### Example 5: Carriers at Risk Only

**User prompt**: "Which watched carriers are out of compliance?"

1. Retrieve watch list and run compliance audits.
2. Filter to carriers with grade D or F.
3. Display only the at-risk carriers with their issues.
4. Display: "2 of 15 watched carriers are at risk. DOT 1234567 (grade D): MCS-150 overdue, authority anomaly. DOT 2345678 (grade F): revoked authority, no active insurance."

## Error Handling

| Error | Cause | Resolution |
|---|---|---|
| MCP tool `manage_watchlist` not available | Watchdog server not running | Check `.mcp.json` and restart `searchcarriers-watchdog` MCP server |
| MCP tool `compliance_audit` not available | Risk Engine server not running | Check `.mcp.json` and restart `searchcarriers-risk-engine` MCP server |
| MCP tool `monitor_compliance` not available | Watchdog server not running | Check `.mcp.json` and restart `searchcarriers-watchdog` MCP server |
| MCP tool `generate_report` not available | Ops Reporter server not running | Check `.mcp.json` and restart `searchcarriers-ops-reporter` MCP server |
| MCP tool `export_data` not available | Ops Reporter server not running | Check `.mcp.json` and restart `searchcarriers-ops-reporter` MCP server |
| 401 Unauthorized | Invalid or expired API key | Verify `SEARCHCARRIERS_API_KEY` is set with a Pro Plus key |
| 403 Tier Restriction | Account tier below Pro Plus | State: "Compliance Dashboard requires Pro Plus. Upgrade at searchcarriers.com/pricing." |
| Empty watch list | No carriers being monitored | State: "No carriers on watch list. Run `/sc-watch add {DOT}` to start monitoring." |
| Compliance audit fails for one carrier | API error or invalid DOT | Log error, skip carrier, continue; note skipped carriers in dashboard |
| All compliance audits fail | API outage or auth failure | Abort workflow; state: "Compliance audits failed for all carriers. Verify API key and connectivity." |
| Drift check fails for one carrier | Baseline not yet captured | Note in dashboard: "Drift unavailable -- baseline pending" |
| Email delivery failure | Email not configured or SMTP error | Display dashboard inline; state: "Email delivery failed. Configure email at searchcarriers.com/settings/notifications." |
| Report generation fails | Ops Reporter returned error | Fall back to raw audit data; generate simplified dashboard without formatted sections |
| Rate limit (429) | Too many concurrent API calls | Add 500ms delay between carriers; for 50+ carriers, batch in groups of 10 |
| Dashboard too large | 50+ carriers produce excessive output | Paginate carrier detail section; include executive summary and top issues in email, link to full report |
| Export format error | CSV generation failed | Deliver dashboard without attachment; note: "CSV export failed. Dashboard delivered without attachment." |

## Resources

- Watchdog plugin schema: `{baseDir}/plugins/searchcarriers-watchdog/SCHEMA.md`
- Watchdog skill: `{baseDir}/plugins/searchcarriers-watchdog/skills/searchcarriers-watchdog/SKILL.md`
- Risk Engine plugin schema: `{baseDir}/plugins/searchcarriers-risk-engine/SCHEMA.md`
- Risk Engine skill: `{baseDir}/plugins/searchcarriers-risk-engine/skills/searchcarriers-risk-engine/SKILL.md`
- Ops Reporter plugin schema: `{baseDir}/plugins/searchcarriers-ops-reporter/SCHEMA.md`
- Ops Reporter skill: `{baseDir}/plugins/searchcarriers-ops-reporter/skills/searchcarriers-ops-reporter/SKILL.md`
- Compliance audit grades: A (fully compliant) through F (critical non-compliance)
- Drift scoring: 0-2 STABLE, 3-5 DRIFTING, 6-9 DEGRADING, 10-15 CRITICAL DRIFT
- Pipeline architecture: Carrier Intel (INPUT) -> Risk Engine (ANALYSIS) -> Ops Reporter (OUTPUT) + Watchdog (MONITORING)
- FMCSA MCS-150 filing requirements: biennial update, 49 CFR 390.19
- Notification settings: searchcarriers.com/settings/notifications
