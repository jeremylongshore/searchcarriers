---
name: sc-alerts
description: View recent Carrier Watch alerts and route to channels
allowed-tools: "Bash(python:*),Read"
---

# /sc-alerts -- Carrier Watch Alerts

When the user runs `/sc-alerts [options]`, display recent monitoring alerts and optionally
route them to notification channels.

## Parse the Input

Optional flags:

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--carrier` | `<DOT>` | (all) | Filter alerts to a specific carrier |
| `--since` | `<YYYY-MM-DD>` | 30 days ago | Show alerts from this date forward |
| `--severity` | `critical`, `high`, `medium`, `all` | `all` | Filter by alert severity |
| `--route` | `slack`, `email` | (none) | Route displayed alerts to a channel |
| `--limit` | `<number>` | 50 | Maximum number of alerts to display |

If no flags are provided, display all alerts from the last 30 days across all watched carriers.

## Execute the Query

### View Alerts

Call the `alert_query` MCP tool with the parsed filter parameters. The tool returns alerts
sorted by timestamp (newest first), each containing: alert ID, DOT number, carrier name,
alert type, severity, description, and timestamp.

### Route Alerts

If `--route` is specified, call the `alert_route` MCP tool after retrieving alerts. Pass the
alert IDs and the target channel. The tool sends formatted alert notifications to the
specified channel and returns delivery confirmation.

## Display Results

### Alert List

```
CARRIER WATCH ALERTS
Period:     {start_date} to {end_date}
Filter:     {filter_description}
Total:      {count} alert(s)

| # | Severity | DOT     | Carrier              | Type              | Date       |
|---|----------|---------|----------------------|-------------------|------------|
| 1 | CRITICAL | 1234567 | ACME TRUCKING LLC    | Insurance Lapse   | 2026-02-25 |
| 2 | HIGH     | 3456789 | ROAD RUNNER TRANSPORT| Safety Downgrade  | 2026-02-24 |
| 3 | MEDIUM   | 1234567 | ACME TRUCKING LLC    | MCS-150 Overdue   | 2026-02-20 |
| 4 | MEDIUM   | 2345678 | FAST FREIGHT INC     | Authority Change  | 2026-02-18 |
```

### Alert Detail

For each alert, expand with a detail block when fewer than 10 alerts are displayed:

```
[CRITICAL] Insurance Lapse -- DOT 1234567
  Carrier:    ACME TRUCKING LLC
  Detected:   2026-02-25 14:30:00 UTC
  Detail:     BIPD insurance policy cancelled effective 2026-02-25.
              Carrier no longer meets federal insurance requirements.
  Action:     Suspend freight tenders immediately. Contact carrier for
              proof of replacement coverage.
```

For 10 or more alerts, show the summary table only and suggest: "Run `/sc-alerts --carrier {DOT}` to see full details for a specific carrier."

### Alert Types

| Type | Trigger | Default Severity |
|------|---------|-----------------|
| Insurance Lapse | Active BIPD or cargo policy cancelled or expired | CRITICAL |
| Authority Revoked | Operating authority status changed to REVOKED | CRITICAL |
| OOS Order | Company, driver, or vehicle out-of-service order issued | CRITICAL |
| Safety Downgrade | Safety rating changed to CONDITIONAL or UNSATISFACTORY | HIGH |
| Insurance Cancellation Pending | Future cancellation date detected on active policy | HIGH |
| Authority Change | Any authority status change (active/inactive/pending) | MEDIUM |
| MCS-150 Overdue | MCS-150 filing date exceeds 2-year threshold | MEDIUM |
| Fleet Size Change | Power units or driver count changed significantly (>25%) | MEDIUM |
| New Crash Recorded | FMCSA crash record added for the carrier | HIGH |
| Compliance Drift | Composite compliance posture degraded since last check | MEDIUM |

### Route Confirmation

When `--route` is used, display confirmation after delivery:

```
ALERT ROUTING
Channel:    {channel_type}
Delivered:  {count} alert(s)
Target:     {channel_target}
Status:     Delivered successfully at {timestamp}
```

If routing fails, display the alerts normally and report: "Alert routing to {channel} failed: {error}. Alerts displayed above for manual review."

### No Alerts

If the query returns zero alerts: "No alerts found for the specified filters. Your watched carriers have no flagged changes in the selected period."

## Follow-Up Actions

After displaying alerts, offer contextual next steps:

- **If CRITICAL alerts exist**: "Run `/sc-risk {DOT}` to reassess risk for flagged carriers. Consider suspending freight tenders until issues are resolved."
- **If HIGH alerts exist**: "Run `/sc-vet {DOT}` to re-evaluate carrier qualification status."
- **Route alerts**: "Run `/sc-alerts --route slack` to send these alerts to your Slack channel."
- **Manage watch list**: "Run `/sc-watch` to view or modify your monitored carriers."

## Error Handling

- **No watched carriers**: "No carriers on the watch list. Run `/sc-watch add {DOT}` to start monitoring."
- **Invalid date format**: "Date must be in YYYY-MM-DD format. Example: `/sc-alerts --since 2026-02-01`."
- **Invalid DOT (--carrier)**: "DOT number must be 7-digit numeric. Use `/sc-lookup` to find the correct DOT."
- **Carrier not watched**: "DOT {dot_number} is not on your watch list. Run `/sc-watch add {DOT}` to start monitoring."
- **Tier insufficient (403)**: "Carrier Watch alerts require a Pro Plus subscription. Upgrade at searchcarriers.com/pricing."
- **API authentication (401)**: "API authentication failed. Check that SEARCHCARRIERS_API_KEY is set and valid."
- **Route channel not configured**: "Slack/email channel not configured. Set up routing in your SearchCarriers account at searchcarriers.com/settings/notifications."
- **API timeout**: Retry once. On second failure: "Alert query timed out. Try narrowing the date range or filtering by carrier."
