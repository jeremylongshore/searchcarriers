---
name: searchcarriers-tms-auto-sync
description: >-
  Sync carrier status changes from Carrier Watch to TMS platforms
  automatically. Use when integrating TMS with carrier monitoring.
allowed-tools: "Read,Grep,Bash(python:*)"
metadata:
  author: Jeremy Longshore <jeremy@intentsolutions.io>
  version: 0.1.0
  license: BUSL-1.1
  tier: enterprise
---

# TMS Auto-Sync -- Workflow Skill

## Overview

This workflow orchestrates automatic synchronization of carrier status changes detected by the Watchdog monitoring system into Transportation Management System (TMS) platforms. It coordinates two plugins: Watchdog (change detection) and API Bridge (TMS data export), creating a closed loop where carrier monitoring events automatically propagate to the systems that manage freight operations.

The pipeline follows this execution path:

```
get_alerts (Watchdog)
    |
    v
[Filter actionable changes]
    |
    v
[For each change]
    |-- tms_sync (API Bridge) -- export carrier data in TMS format
    |
    v
[Log sync results]
    |
    v
[On sync failure]
    |-- route_alert (Watchdog) -- notify operations team
```

Without this workflow, carrier status changes detected by the Watchdog sit in an alert queue until a human reviews them and manually updates the TMS. This workflow eliminates that lag, ensuring the TMS reflects the current state of every monitored carrier within minutes of a change occurring.

## Prerequisites

- **Minimum tier**: Enterprise (tms_sync requires Enterprise; Watchdog requires Pro Plus)
- `SEARCHCARRIERS_API_KEY` environment variable set with a valid Bearer token
- MCP servers running: `searchcarriers-watchdog`, `searchcarriers-api-bridge`
- API base URL: `https://searchcarriers.com/api/v1`
- Authentication format: `Authorization: Bearer {id}|{token}` (Laravel Sanctum)
- TMS integration configured: target TMS credentials, field mapping, and API endpoint
- At least one carrier on the watch list with active monitoring

## Instructions

### Stage 1: Retrieve Recent Alerts

Call `get_alerts` from the Watchdog plugin to pull recent carrier change alerts. Filter by time window and relevance to TMS synchronization.

**Time window options:**

| Window | Use Case | Expected Volume |
|--------|----------|-----------------|
| Last 1 hour | Frequent sync cycles (Enterprise default) | Low (0-5 alerts) |
| Last 6 hours | Standard sync cadence | Moderate (0-20 alerts) |
| Last 24 hours | Daily sync batch | Higher (0-50 alerts) |
| Since last sync | Resume from last successful sync timestamp | Variable |

**TMS-relevant alert types:**

Not all Watchdog alerts require a TMS sync. Filter to only these types:

| Alert Type | TMS Action | Priority |
|------------|-----------|----------|
| `carrier.status_change` | Update carrier status field (ACTIVE/INACTIVE/OOS) | CRITICAL -- affects load tendering |
| `carrier.insurance_change` | Update insurance fields (coverage type, amount, provider, dates) | HIGH -- affects compliance status |
| `carrier.authority_change` | Update authority fields (type, status, docket number) | HIGH -- affects legal operating scope |
| `carrier.safety_rating` | Update safety rating field | MEDIUM -- affects qualification tier |
| `carrier.oos_order` | Update OOS status, add compliance flag | CRITICAL -- carrier cannot operate |

**Discard these alert types** (not TMS-relevant):

- `compliance_drift` -- informational, no discrete field to update
- `fleet_size_change` -- typically refreshed on next full sync
- `mcs150_overdue` -- registration concern, not a TMS field

After filtering, sort alerts by priority (CRITICAL first, then HIGH, then MEDIUM) to ensure the most operationally impactful changes sync first.

### Stage 2: TMS Data Export

For each filtered alert, call `tms_sync` from the API Bridge plugin to export the carrier's current data in the TMS-specific format.

**TMS field mapping per alert type:**

| Alert Type | Fields to Sync | Transform |
|------------|---------------|-----------|
| `carrier.status_change` | `carrier_status` | Map SC status code to TMS value (A=Active, I=Inactive) |
| `carrier.insurance_change` | `liability_coverage`, `cargo_coverage`, `broker_bond` | Dollar amounts as numeric; dates as YYYY-MM-DD |
| `carrier.authority_change` | `authority_type`, `authority_status`, `mc_number` | Map authority codes to TMS values |
| `carrier.safety_rating` | `safety_rating` | Direct pass-through (SATISFACTORY/CONDITIONAL/UNSATISFACTORY) |
| `carrier.oos_order` | `carrier_status`, `oos_flag`, `oos_effective_date` | Set status to OOS; populate order details |

**Sync modes:**

| Mode | Behavior | When to Use |
|------|----------|-------------|
| Incremental | Only sync the fields that changed | Default for individual alert processing |
| Full | Sync all carrier fields regardless of what changed | After connectivity recovery or data integrity concern |
| Dry run | Generate the TMS payload without sending | Testing field mappings or new TMS integrations |

**TMS payload envelope:**

Each sync call produces a payload following the standard TMS field map defined in the API Bridge skill. The payload includes:

| Field | Content |
|-------|---------|
| `carrier_id` | DOT number (primary key for TMS record) |
| `sync_type` | `incremental` or `full` |
| `changed_fields` | Array of field names that changed |
| `timestamp` | ISO 8601 timestamp of the sync |
| `source_alert_id` | Alert ID that triggered the sync |
| `payload` | TMS-formatted carrier data object |

### Stage 3: Log Sync Results

After each `tms_sync` call, record the result for audit trail and operational visibility.

**Sync result statuses:**

| Status | Meaning | Action |
|--------|---------|--------|
| SUCCESS | TMS accepted the update | Log and continue |
| PARTIAL | TMS accepted some fields but rejected others | Log rejections; proceed to Stage 4 for rejected fields |
| REJECTED | TMS rejected the entire update | Proceed to Stage 4 |
| TIMEOUT | TMS did not respond within threshold | Retry once; if still timeout, proceed to Stage 4 |
| SKIPPED | Alert was duplicate or already synced | Log and continue |

**Sync log entry format:**

| Field | Content |
|-------|---------|
| `timestamp` | When the sync was attempted |
| `dot_number` | Carrier DOT |
| `alert_type` | Type of change that triggered sync |
| `alert_id` | Source alert identifier |
| `sync_status` | SUCCESS / PARTIAL / REJECTED / TIMEOUT / SKIPPED |
| `fields_synced` | Array of field names successfully synced |
| `fields_failed` | Array of field names that failed |
| `error_detail` | Error message if applicable |
| `duration_ms` | Sync call duration in milliseconds |

**Deduplication:**

Before syncing, check the log for the same `dot_number` + `alert_id` combination. If already synced with SUCCESS status, mark as SKIPPED. This prevents duplicate TMS updates if the workflow runs multiple times over the same time window.

### Stage 4: Failure Routing

For any sync that results in PARTIAL, REJECTED, or TIMEOUT status, call `route_alert` from the Watchdog plugin to notify the operations team.

**Failure notification content:**

| Field | Content |
|-------|---------|
| Subject | `[TMS Sync Failed] DOT {dot_number} -- {alert_type}` |
| Severity | Match the original alert priority (CRITICAL/HIGH/MEDIUM) |
| Body | Carrier name, DOT, what changed, what failed to sync, error detail |
| Action required | Manual TMS update needed for the failed fields |
| Deep link | SearchCarriers dashboard URL for the carrier |

**Routing channels:**

| Channel | When | Format |
|---------|------|--------|
| Slack | Default for all failures | Block Kit message with severity color bar |
| Email | CRITICAL failures always; others per configuration | Digest format with failure details |
| Webhook | Enterprise integrations that consume raw events | JSON payload following pipeline envelope standard |

**Escalation rules:**

| Condition | Escalation |
|-----------|------------|
| 3+ consecutive sync failures for the same carrier | Escalate severity by one level |
| 5+ total sync failures in a single run | Add aggregate failure summary to notification |
| CRITICAL alert sync failure | Immediate notification via all configured channels |
| TMS endpoint unreachable for all carriers | Halt sync; send system-level alert indicating TMS outage |

### Batch Execution Summary

After all alerts are processed, produce a summary report.

**Summary fields:**

| Metric | Calculation |
|--------|-------------|
| Alerts retrieved | Count from `get_alerts` |
| Alerts filtered (TMS-relevant) | Count after applying type filter |
| Syncs attempted | Count of `tms_sync` calls made |
| Syncs succeeded | Count of SUCCESS status |
| Syncs failed | Count of PARTIAL + REJECTED + TIMEOUT |
| Syncs skipped | Count of SKIPPED (duplicates) |
| Total fields synced | Sum of `fields_synced` lengths across all calls |
| Duration | Wall clock time for the entire batch |

## Examples

### Example 1: Routine Hourly Sync

Operations team runs the workflow on a 1-hour cycle.

1. `get_alerts` returns 3 alerts in the last hour: 1 insurance change, 1 status change, 1 fleet size change.
2. Filter: 2 TMS-relevant (insurance, status). Fleet size change discarded.
3. `tms_sync` for insurance change: SUCCESS -- `liability_coverage` and `cargo_coverage` updated.
4. `tms_sync` for status change: SUCCESS -- `carrier_status` updated to INACTIVE.
5. Summary: "2 alerts synced. 2/2 succeeded. 0 failures. 3 fields updated. Duration: 4s."

### Example 2: Sync Failure with Escalation

A carrier's authority is revoked, but the TMS rejects the update.

1. `get_alerts` returns 1 CRITICAL alert: authority revoked for DOT 1234567.
2. `tms_sync` for authority change: REJECTED -- TMS returns 422 (unknown authority_status value).
3. Log the failure with error detail.
4. `route_alert` sends CRITICAL notification to Slack and email: "TMS sync failed for DOT 1234567 -- authority revoked but TMS rejected update. Manual TMS update required."
5. Summary: "1 alert processed. 0/1 synced. 1 failure (REJECTED). Operations notified via Slack and email."

### Example 3: Recovery Sync After TMS Outage

TMS was down for 6 hours. Operator runs a catch-up sync.

1. `get_alerts` with "last 6 hours" window returns 12 alerts.
2. Filter: 9 TMS-relevant.
3. Deduplication check: 2 alerts are for the same carrier's insurance (cancel then reinstate). Both are synced in order.
4. `tms_sync` for all 9: 8 SUCCESS, 1 TIMEOUT.
5. Retry the TIMEOUT: SUCCESS on retry.
6. Summary: "9 alerts synced. 9/9 succeeded (1 required retry). 14 fields updated. Duration: 22s."

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No alerts found | No carrier changes in the time window | Normal -- report "0 alerts. No sync needed." |
| Watchdog MCP unavailable | `searchcarriers-watchdog` server not running | Report: "Watchdog MCP required for alert retrieval. Check server status." |
| API Bridge MCP unavailable | `searchcarriers-api-bridge` server not running | Report: "API Bridge MCP required for TMS sync. Check server status." |
| 403 tier restriction | User tier below Enterprise for tms_sync | State: "TMS Auto-Sync requires Enterprise tier. Watchdog alerts retrieved but sync unavailable." |
| TMS endpoint unreachable | Target TMS API is down or misconfigured | Halt syncs; route system-level alert; suggest checking TMS credentials and endpoint URL |
| TMS field mapping error | SC field does not map to TMS schema | Log the unmapped field; sync remaining fields as PARTIAL; notify operations |
| Duplicate alert processing | Same alert processed in overlapping time windows | Deduplication check prevents double-sync; log as SKIPPED |
| Rate limit (429) | SearchCarriers API rate limit exceeded | Pause for `Retry-After` duration; reduce sync frequency |
| Authentication failure (401) | Invalid or expired API key | Verify `SEARCHCARRIERS_API_KEY`; halt all syncs until resolved |

## Resources

- Watchdog plugin tools: `get_alerts`, `route_alert` -- `{baseDir}/plugins/searchcarriers-watchdog/SCHEMA.md`
- API Bridge plugin tools: `tms_sync`, `bulk_lookup` -- `{baseDir}/plugins/searchcarriers-api-bridge/SCHEMA.md`
- TMS field mapping reference: `{baseDir}/plugins/searchcarriers-api-bridge/skills/searchcarriers-api-bridge/SKILL.md`
- Watchdog alert types: `{baseDir}/plugins/searchcarriers-watchdog/skills/searchcarriers-watchdog/SKILL.md`
- Pipeline architecture: Watchdog (MONITORING) -> API Bridge (INTEGRATION) -> TMS
- Notification routing: Slack Block Kit, email digest, webhook envelope
- SearchCarriers API base: `https://searchcarriers.com/api/v1`
- Auth format: `Authorization: Bearer {id}|{token}` (Laravel Sanctum)
