---
name: searchcarriers-watchdog
description: >-
  Monitor carrier watch lists, view alerts, route notifications, and track
  compliance drift. Use when managing carrier monitoring.
allowed-tools: "Read,Grep,Bash(python:*)"
metadata:
  author: "Jeremy Longshore <jeremy@intentsolutions.io>"
  version: 0.1.0
  license: BUSL-1.1
  tier: proplus
---

# Carrier Watchdog -- Embedded Skill

## Overview

This skill provides the monitoring intelligence layer for the searchcarriers Watchdog plugin. It teaches you how to manage carrier watch lists, interpret monitoring alerts, route notifications to appropriate channels, track compliance drift over time, and escalate critical changes that affect carrier qualification status.

The Watchdog plugin operates as a STANDALONE monitoring layer alongside the core pipeline (Carrier Intel -> Risk Engine -> Ops Reporter). It consumes data from all three pipeline stages and produces proactive alerts when monitored carriers exhibit changes that affect risk posture, compliance standing, or operational capability.

## Prerequisites

- **Minimum tier**: Pro Plus
- MCP server `searchcarriers-watchdog` must be running and accessible
- `SEARCHCARRIERS_API_KEY` environment variable set with a valid key
- Upstream plugins should be available for full analysis: `searchcarriers-carrier-intel`, `searchcarriers-risk-engine`, `searchcarriers-ops-reporter`
- Familiarity with FMCSA terminology (DOT, MC, OOS, BIPD, MCS-150)

## Instructions

### Watch List Management

The watch list is the carrier roster actively monitored for changes. Each entry stores the DOT number, carrier name, monitoring start date, alert preferences, and historical alert count.

**Adding Carriers**

When adding a carrier via `watchlist_manage`, the tool validates the DOT against FMCSA records and captures a baseline snapshot of the carrier's current status, insurance, safety rating, authority, and compliance posture. This baseline is used for drift detection on subsequent checks.

Watch list limits by tier:

| Tier | Max Carriers | Check Frequency | Alert Channels |
|------|-------------|-----------------|----------------|
| Pro Plus | 50 | Every 6 hours | Slack, Email |
| Enterprise | Unlimited | Every 1 hour | Slack, Email, Webhook, SMS |

**Removing Carriers**

Removing a carrier stops active monitoring but retains historical alerts for 90 days. The baseline snapshot is archived for reference. Re-adding the same carrier within 90 days restores the previous alert history.

**Monitoring State**

Each watched carrier has a monitoring state:

| State | Meaning |
|-------|---------|
| ACTIVE | Monitoring is running normally; checks execute on schedule |
| PAUSED | Monitoring temporarily suspended by user; no alerts generated |
| STALE | Last check failed 3+ consecutive times; investigate connectivity or carrier data issues |
| BASELINE | Initial snapshot captured; first comparison pending |

### Alert Types and Severity

Alerts are generated when a monitored carrier's current data diverges from the baseline or previous check. Each alert type has a default severity, but severity can escalate based on context.

**Critical Alerts (Immediate Action Required)**

| Alert Type | Trigger | Implication |
|------------|---------|-------------|
| Insurance Lapse | Active BIPD policy cancelled or expired with no replacement | Carrier cannot legally operate for-hire; suspend freight tenders immediately |
| Authority Revoked | Operating authority changed to REVOKED status | FMCSA has taken enforcement action; carrier cannot operate under revoked authority |
| OOS Order Issued | Company-level out-of-service order detected | FMCSA has ordered carrier to cease operations; do not tender any freight |

**High Alerts (Review Within 24 Hours)**

| Alert Type | Trigger | Implication |
|------------|---------|-------------|
| Safety Downgrade | Rating changed from SATISFACTORY to CONDITIONAL or UNSATISFACTORY | Safety deficiencies identified; re-evaluate qualification status |
| Insurance Cancellation Pending | Future cancellation date detected on active policy | Coverage will lapse; contact carrier for replacement proof before effective date |
| New Crash Recorded | FMCSA crash record added (fatal or injury) | Reassess risk score; may affect OOS rates and qualification |
| Compliance Grade Drop | Compliance audit grade dropped by 2+ levels (e.g., B to D) | Regulatory posture deteriorating; investigate root cause |

**Medium Alerts (Review Within 7 Days)**

| Alert Type | Trigger | Implication |
|------------|---------|-------------|
| Authority Change | Any authority status transition (not revocation) | May affect carrier's legal operating scope; verify authorities still cover your lanes |
| MCS-150 Overdue | Filing date exceeded 2-year threshold | Registration data may be stale; carrier may face FMCSA penalties |
| Fleet Size Change | Power units or drivers changed by more than 25% | Operational capacity shift; may indicate growth, downsizing, or data correction |
| Compliance Drift | Composite compliance posture degraded by 1 level since baseline | Gradual deterioration trend; monitor for further decline |
| OOS Rate Increase | Vehicle or driver OOS rate increased above national average threshold | Inspection performance declining; equipment or driver compliance concerns |

### Compliance Drift Interpretation

Compliance drift measures how a carrier's regulatory posture changes over time relative to the baseline captured when monitoring began. Drift is calculated across five dimensions:

| Dimension | Baseline Metric | Drift Trigger |
|-----------|----------------|---------------|
| Insurance Posture | Coverage types, amounts, active status | Any policy cancelled, reduced, or pending cancellation |
| Authority Standing | All authority types and statuses | Any authority deactivated, revoked, or new authority pending |
| Safety Rating | FMCSA safety rating and date | Rating downgraded or OOS rates increased above thresholds |
| Filing Currency | MCS-150 filing date | Filing age exceeds 24 months without update |
| Operational Profile | Fleet size, driver count, operation type | Significant changes (>25%) in operational capacity |

**Drift Severity Calculation**

Drift severity is cumulative. Each dimension contributes a drift score:

| Drift Level | Score | Meaning |
|-------------|-------|---------|
| STABLE | 0 | No change from baseline in this dimension |
| MINOR | 1 | Small change, not operationally significant |
| MODERATE | 2 | Notable change, warrants review |
| SIGNIFICANT | 3 | Major change, affects qualification posture |

The composite drift score is the sum across all five dimensions:

| Composite Score | Drift Status | Recommended Action |
|----------------|-------------|-------------------|
| 0-2 | STABLE | No action required; continue monitoring |
| 3-5 | DRIFTING | Review carrier status; consider re-running `/sc-risk` |
| 6-9 | DEGRADING | Re-evaluate qualification; run full pipeline assessment |
| 10-15 | CRITICAL DRIFT | Immediate review; suspend freight tenders pending assessment |

### Notification Routing

Alerts can be routed to external channels for real-time notification. Routing is configured per-account and can be overridden per-carrier.

**Slack Integration**

Alerts are formatted as Slack Block Kit messages with severity-coded color bars:

| Severity | Color | Mention |
|----------|-------|---------|
| CRITICAL | Red (#E01E5A) | @channel |
| HIGH | Orange (#ECB22E) | @here |
| MEDIUM | Blue (#36C5F0) | (no mention) |

Slack messages include: carrier name, DOT, alert type, severity, description, and a deep link to the SearchCarriers dashboard for the carrier.

**Email Integration**

Alerts are batched and sent as digest emails at configurable intervals:

| Digest Frequency | Use Case |
|-----------------|----------|
| Immediate | CRITICAL alerts only; sent within 5 minutes |
| Hourly | HIGH alerts rolled up into hourly digest |
| Daily | MEDIUM alerts collected into daily summary at configured time |

Email subjects follow the format: `[SearchCarriers {severity}] {alert_type} -- DOT {dot_number} {legal_name}`

**Webhook Integration (Enterprise)**

Raw alert payloads delivered as JSON POST to a configured endpoint. The payload follows the pipeline envelope format:

```json
{
  "_pipeline": {
    "source": "searchcarriers-watchdog",
    "tool": "alert_route",
    "version": "0.1.0",
    "dot_number": 1234567,
    "timestamp": "2026-02-26T14:30:00Z",
    "tier": "enterprise",
    "data": {
      "alert_id": "alt_abc123",
      "alert_type": "insurance_lapse",
      "severity": "critical",
      "carrier_name": "ACME TRUCKING LLC",
      "description": "BIPD insurance policy cancelled.",
      "recommended_action": "Suspend freight tenders."
    }
  }
}
```

### Watch List Maintenance Best Practices

- **Regular review**: Audit the watch list monthly. Remove carriers you no longer do business with to keep alert volume manageable.
- **Baseline refresh**: After a carrier resolves flagged issues, reset the baseline via `watchlist_manage` with `action: "refresh"` to clear accumulated drift.
- **Severity tuning**: If a carrier consistently generates medium alerts that are not actionable (e.g., fleet size fluctuations for a growing carrier), adjust per-carrier alert thresholds rather than removing from the watch list.
- **Cross-reference with pipeline**: When a critical or high alert fires, always re-run the full pipeline (`/sc-report {DOT}`) for a current assessment before making qualification changes.

## Examples

### Example 1: Adding a Carrier to Watch List

User asks: "Watch DOT 1234567"

1. Call `watchlist_manage` with `action: "add"`, `dot_number: 1234567`
2. Tool validates the DOT, captures baseline snapshot
3. Display add confirmation with carrier details and monitoring status
4. Suggest `/sc-alerts --carrier 1234567` to view any existing alerts

### Example 2: Reviewing Critical Alerts

User asks: "Show me critical alerts"

1. Call `alert_query` with `severity: "critical"`
2. Display alerts with full detail blocks (fewer than 10 expected for critical)
3. For each critical alert, suggest immediate action and the relevant command
4. Offer to route alerts: `/sc-alerts --severity critical --route slack`

### Example 3: Compliance Drift Investigation

User asks: "Why is DOT 1234567 showing drift?"

1. Call `alert_query` with `carrier: 1234567`, `type: "compliance_drift"`
2. Display the drift breakdown across all five dimensions
3. Identify which dimensions are contributing to drift
4. Suggest: "Run `/sc-risk 1234567` for an updated risk assessment" or "Run `/sc-vet 1234567` to re-check qualification status"

### Example 4: Routing Alerts to Slack

User asks: "Send today's alerts to Slack"

1. Call `alert_query` with `since: today` to retrieve current alerts
2. Call `alert_route` with retrieved alert IDs and `channel: "slack"`
3. Display routing confirmation with delivery status
4. Note any delivery failures and suggest checking Slack integration settings

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| MCP tool not available | Server not started or misconfigured | Check `.mcp.json` config and restart the MCP server |
| 401 from API | Invalid or missing API key | Verify `SEARCHCARRIERS_API_KEY` is set and valid |
| 403 tier restriction | User tier below Pro Plus | State: "Carrier Watch requires Pro Plus tier. Upgrade at searchcarriers.com/pricing." |
| 404 carrier not found | DOT number not in FMCSA database | Suggest searching by name via `/sc-lookup` |
| Watch list full | Carrier limit reached for tier | Remove inactive carriers or upgrade tier for higher limits |
| Route channel not configured | Slack/email integration not set up | Direct user to searchcarriers.com/settings/notifications |
| Stale monitoring state | 3+ consecutive check failures | Investigate API connectivity; carrier may have been removed from FMCSA database |
| Baseline missing | Carrier added before baseline capture was implemented | Run `watchlist_manage` with `action: "refresh"` to capture a new baseline |

## Resources

- Plugin configuration: `{baseDir}/.claude-plugin/plugin.json`
- MCP server source: `{baseDir}/scripts/watchdog_mcp.py`
- Carrier Intel skill (upstream): `searchcarriers-carrier-intel`
- Risk Engine skill (upstream): `searchcarriers-risk-engine`
- Ops Reporter skill (upstream): `searchcarriers-ops-reporter`
- Pipeline architecture: Carrier Intel (INPUT) -> Risk Engine (ANALYSIS) -> Ops Reporter (OUTPUT) + Watchdog (MONITORING)
- FMCSA insurance minimums: 49 CFR Part 387
- National OOS benchmarks: vehicle ~20%, driver ~5%
- Slack Block Kit reference: api.slack.com/block-kit
- Webhook payload format: pipeline envelope standard (see Ops Reporter SKILL.md)
