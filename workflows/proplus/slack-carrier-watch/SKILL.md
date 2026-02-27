---
name: searchcarriers-slack-carrier-watch
description: >-
  Route all Carrier Watch alerts to Slack with formatted cards and
  severity-coded colors. Use when setting up Slack alert integration.
allowed-tools: "Read,Grep,Bash(python:*)"
metadata:
  author: "Jeremy Longshore <jeremy@intentsolutions.io>"
  version: 0.1.0
  license: BUSL-1.1
  tier: proplus
---

# Slack Carrier Watch -- Workflow Skill

## Overview

This workflow orchestrates the Watchdog plugin's alert retrieval and routing capabilities into a complete Slack notification pipeline. It pulls all pending alerts from the Carrier Watch system, categorizes them by severity, formats each alert as a Slack Block Kit card with severity-coded color bars, routes the formatted cards to the appropriate Slack channel, and produces a delivery summary.

The workflow crosses two plugin boundaries: **searchcarriers-watchdog** provides the `get_alerts` and `route_alert` MCP tools, while the Slack Block Kit formatting logic lives in this workflow's orchestration layer. The result is a hands-free alert-to-Slack pipeline that ensures no critical carrier change goes unnoticed in your team's Slack workspace.

**Pipeline position**: Watchdog (MONITORING) -> Slack Carrier Watch (WORKFLOW OUTPUT)

**Upstream plugins**: `searchcarriers-watchdog` (required), `searchcarriers-risk-engine` (optional, for enriched alert context)

## Prerequisites

- **Minimum tier**: Pro Plus
- MCP server `searchcarriers-watchdog` must be running and accessible.
- `SEARCHCARRIERS_API_KEY` environment variable set with a valid Pro Plus or Enterprise key.
- Slack integration must be configured in your SearchCarriers account at `searchcarriers.com/settings/notifications`. The integration requires a Slack incoming webhook URL or a Slack app with `chat:write` scope installed to your workspace.
- At least one carrier must be on the watch list. Use `/sc-watch add {DOT}` to add carriers before running this workflow.
- `python3` must be available in the execution environment.

## Instructions

### Step 1: Retrieve All Pending Alerts

Call the `get_alerts` MCP tool to pull all unrouted alerts from the Carrier Watch system. The tool accepts optional filters but this workflow retrieves the full set and categorizes locally.

```python
# Fetch all alerts from the watchdog system
# The get_alerts tool returns alerts sorted by timestamp (newest first)
# Each alert contains: alert_id, dot_number, carrier_name, alert_type,
#   severity, description, timestamp, routed (bool)

import json
from datetime import datetime, timedelta

# Call get_alerts with no filters to retrieve all pending alerts
# Filter parameters available: severity, since, carrier (DOT), limit
# For this workflow, we retrieve all unrouted alerts
alerts_params = {
    "since": (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d"),
    "limit": 200
}
```

If the response is empty, report: "No pending alerts. All watched carriers are stable." and stop.

If the response contains alerts, proceed to Step 2.

### Step 2: Categorize Alerts by Severity

Group retrieved alerts into three severity buckets. Each bucket maps to a Slack formatting profile.

```python
SEVERITY_PROFILES = {
    "critical": {
        "color": "#E01E5A",   # Red
        "emoji": ":rotating_light:",
        "mention": "<!channel>",
        "priority": 1
    },
    "high": {
        "color": "#ECB22E",   # Orange
        "emoji": ":warning:",
        "mention": "<!here>",
        "priority": 2
    },
    "medium": {
        "color": "#36C5F0",   # Blue
        "emoji": ":information_source:",
        "mention": "",
        "priority": 3
    }
}

def categorize_alerts(alerts):
    buckets = {"critical": [], "high": [], "medium": []}
    for alert in alerts:
        severity = alert.get("severity", "medium").lower()
        if severity not in buckets:
            severity = "medium"
        buckets[severity].append(alert)
    return buckets
```

Sort each bucket by timestamp (newest first). Critical alerts are always processed and routed first.

### Step 3: Format Each Alert as a Slack Block Kit Card

Transform each alert into a Slack Block Kit attachment with structured sections. The card format ensures consistent, scannable notifications across all alert types.

```python
def format_slack_card(alert, profile):
    """Build a Slack Block Kit attachment for a single alert."""
    severity = alert["severity"].upper()
    dot = alert["dot_number"]
    carrier = alert["carrier_name"]
    alert_type = alert["alert_type"].replace("_", " ").title()
    description = alert["description"]
    timestamp = alert["timestamp"]
    dashboard_url = f"https://searchcarriers.com/carrier/{dot}"

    attachment = {
        "color": profile["color"],
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{profile['emoji']} [{severity}] {alert_type}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Carrier:*\n{carrier}"},
                    {"type": "mrkdwn", "text": f"*DOT:*\n{dot}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                    {"type": "mrkdwn", "text": f"*Detected:*\n{timestamp}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Detail:*\n{description}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View in Dashboard"},
                        "url": dashboard_url,
                        "style": "primary"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"SearchCarriers Watchdog | Alert ID: {alert['alert_id']}"
                    }
                ]
            }
        ]
    }

    return attachment
```

**Alert type to description mapping** (used when the alert description needs enrichment):

| Alert Type | Slack Card Summary |
|---|---|
| Insurance Lapse | BIPD coverage cancelled or expired -- carrier cannot legally operate |
| Authority Revoked | FMCSA revoked operating authority -- cease all freight tenders |
| OOS Order Issued | Out-of-service order -- carrier must stop operations |
| Safety Downgrade | Safety rating downgraded -- review qualification status |
| Insurance Cancellation Pending | Coverage will lapse on {date} -- request replacement proof |
| New Crash Recorded | Fatal or injury crash added to record -- reassess risk |
| Compliance Drift | Compliance posture degraded since last check -- investigate |
| Authority Change | Operating authority status changed -- verify lane coverage |
| MCS-150 Overdue | Registration filing overdue -- potential FMCSA penalties |
| Fleet Size Change | Fleet size changed by more than 25% -- operational shift |

### Step 4: Route Formatted Alerts to Slack

Call the `route_alert` MCP tool for each alert, specifying `channel: "slack"`. Route in priority order: critical first, then high, then medium.

```python
def route_alerts_to_slack(categorized, format_fn):
    """Route all alerts to Slack in severity-priority order."""
    results = {"delivered": [], "failed": []}

    for severity in ["critical", "high", "medium"]:
        profile = SEVERITY_PROFILES[severity]
        alerts = categorized[severity]

        for alert in alerts:
            card = format_fn(alert, profile)

            # Call route_alert MCP tool
            # Parameters: alert_id, channel ("slack"), payload (Block Kit JSON)
            route_params = {
                "alert_id": alert["alert_id"],
                "channel": "slack",
                "payload": card,
                "mention": profile["mention"]
            }

            # On success, add to delivered list
            # On failure, add to failed list with error reason
            # The route_alert tool returns: status, channel, delivered_at, error
            try:
                # MCP tool call: route_alert(route_params)
                results["delivered"].append({
                    "alert_id": alert["alert_id"],
                    "severity": severity,
                    "carrier": alert["carrier_name"],
                    "dot": alert["dot_number"]
                })
            except Exception as e:
                results["failed"].append({
                    "alert_id": alert["alert_id"],
                    "severity": severity,
                    "carrier": alert["carrier_name"],
                    "error": str(e)
                })

    return results
```

If `route_alert` fails for a specific alert, log the failure and continue routing the remaining alerts. Do not abort the entire batch on a single failure.

If all routes fail, check the Slack integration configuration: "Slack routing failed for all alerts. Verify your Slack integration at searchcarriers.com/settings/notifications."

### Step 5: Generate the Delivery Summary

After all alerts have been routed (or attempted), produce a summary report for the user.

```
SLACK CARRIER WATCH -- ROUTING SUMMARY
Run at:     {timestamp}
Period:     {since} to {now}

ALERTS BY SEVERITY
  Critical:  {count} ({delivered}/{total} delivered)
  High:      {count} ({delivered}/{total} delivered)
  Medium:    {count} ({delivered}/{total} delivered)
  Total:     {total_count} alerts processed

DELIVERY STATUS
  Delivered: {delivered_count}
  Failed:    {failed_count}

{if failed_count > 0}
FAILED DELIVERIES
| Alert ID | Severity | Carrier | Error |
|----------|----------|---------|-------|
| {id}     | {sev}    | {name}  | {err} |
{end if}

NEXT STEPS
- Review critical alerts immediately in #carrier-alerts
- Run `/sc-risk {DOT}` for updated risk on flagged carriers
- Run `/sc-watch` to manage your watch list
```

## Examples

### Example 1: Daily Alert Routing

**User prompt**: "Send all Carrier Watch alerts to Slack"

1. Call `get_alerts` with `since: today` -- returns 7 alerts (2 critical, 3 high, 2 medium).
2. Categorize into severity buckets.
3. Format each as a Block Kit card with severity-coded colors.
4. Call `route_alert` for each alert with `channel: "slack"`.
5. Display summary: "7 alerts routed to Slack: 2 critical (red), 3 high (orange), 2 medium (blue). All delivered successfully."

### Example 2: Critical-Only Slack Push

**User prompt**: "Push only critical alerts to Slack"

1. Call `get_alerts` with `severity: "critical"` -- returns 1 alert (insurance lapse).
2. Format as Block Kit card with red (#E01E5A) color bar and @channel mention.
3. Route via `route_alert` with `channel: "slack"`.
4. Display: "1 critical alert routed to Slack: Insurance Lapse for DOT 1234567 (ACME TRUCKING LLC). @channel mention included."

### Example 3: Carrier-Specific Alert Review

**User prompt**: "Route all alerts for DOT 1234567 to Slack"

1. Call `get_alerts` with `carrier: 1234567` -- returns 3 alerts across severities.
2. Categorize and format each alert.
3. Route all three to Slack.
4. Display per-alert delivery confirmation with the carrier name and alert types.

### Example 4: No Pending Alerts

**User prompt**: "Send alerts to Slack"

1. Call `get_alerts` -- returns empty list.
2. Report: "No pending alerts found. All watched carriers are stable. Run `/sc-watch` to review your watch list."

## Error Handling

| Error | Cause | Resolution |
|---|---|---|
| MCP tool `get_alerts` not available | Watchdog server not running | Check `.mcp.json` and restart `searchcarriers-watchdog` MCP server |
| MCP tool `route_alert` not available | Watchdog server not running | Check `.mcp.json` and restart `searchcarriers-watchdog` MCP server |
| 401 Unauthorized | Invalid or expired API key | Verify `SEARCHCARRIERS_API_KEY` is set with a Pro Plus key |
| 403 Tier Restriction | Account tier below Pro Plus | State: "Slack Carrier Watch requires Pro Plus. Upgrade at searchcarriers.com/pricing." |
| Slack channel not configured | No webhook URL or Slack app installed | Direct user to searchcarriers.com/settings/notifications to configure Slack |
| Slack delivery timeout | Slack API unresponsive | Retry once after 5 seconds; on second failure, display alerts in console and suggest manual Slack post |
| Slack rate limit (429) | Too many messages sent to Slack | Batch remaining alerts into a single digest message instead of individual cards |
| No carriers on watch list | Watch list is empty | State: "No carriers being monitored. Run `/sc-watch add {DOT}` to start." |
| Partial delivery failure | Some alerts routed, others failed | Report delivered alerts, list failures with error details, suggest retrying failed alerts |
| Invalid Block Kit payload | Malformed card JSON | Log the raw alert data, skip the malformed card, continue with remaining alerts |

## Resources

- Watchdog plugin schema: `{baseDir}/plugins/searchcarriers-watchdog/SCHEMA.md`
- Watchdog skill: `{baseDir}/plugins/searchcarriers-watchdog/skills/searchcarriers-watchdog/SKILL.md`
- Watchdog MCP server: `{baseDir}/plugins/searchcarriers-watchdog/scripts/watchdog_mcp.py`
- Alert types and severities: `{baseDir}/plugins/searchcarriers-watchdog/commands/sc-alerts.md`
- Slack Block Kit reference: https://api.slack.com/block-kit
- Slack attachment colors: https://api.slack.com/reference/messaging/attachments
- Slack mention tokens: `<!channel>` (all members), `<!here>` (active members)
- Pipeline architecture: Carrier Intel (INPUT) -> Risk Engine (ANALYSIS) -> Ops Reporter (OUTPUT) + Watchdog (MONITORING)
- Notification settings: searchcarriers.com/settings/notifications
