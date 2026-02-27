# Watchdog - Business Case

## Problem Statement

Carrier status changes silently. An insurance policy lapses. An operating authority gets revoked. A safety rating downgrades from Satisfactory to Conditional. These events happen every day across the 4 million+ motor carriers in the FMCSA database, and the brokerages that rely on those carriers find out too late -- usually after they have already tendered a load.

The typical discovery process looks like this. A broker dispatches a load to a carrier they used last month. The load moves. A claim happens. During the claims investigation, someone checks FMCSA and discovers the carrier's insurance lapsed two weeks before the pickup. The brokerage's contingent cargo policy may or may not cover it. The average cargo claim is $50,000. The legal and administrative cost of fighting it doubles that number.

This is not a data access problem. FMCSA records are public and SearchCarriers already aggregates them into a 4M+ carrier database with nightly syncs. The problem is that nobody is watching. A brokerage with 200 carriers on their approved panel cannot manually check each carrier's status every day. They check at onboarding, maybe at annual re-qualification, and hope nothing changes in between.

The freight industry calls this "set and forget" carrier management. It is the norm, and it is a liability.

## Target Customer

| Segment | Role | Pain Level | Frequency |
|---------|------|-----------|-----------|
| Freight brokers | Carrier management, load planning | Critical | Ongoing -- carrier panel changes daily |
| Third-party logistics (3PL) | Operations managers, compliance teams | Critical | Ongoing -- managing 50-500+ carrier panels |
| Shippers | Transportation procurement, vendor management | High | Monthly -- carrier re-qualification cycles |
| Compliance departments | Safety directors, regulatory compliance | Critical | Ongoing -- audit readiness requirements |
| Risk managers | Contingent liability, claims prevention | High | Weekly -- carrier risk monitoring |

The primary buyer is the operations manager or compliance lead at a mid-size 3PL or brokerage with 100 to 500 carriers on their approved panel. They are responsible for ensuring every carrier that touches their freight is authorized, insured, and safe -- every day, not just at onboarding. Today they have no automated way to do this. Carrier Watch on SearchCarriers.com already solves part of the problem through the web UI. This plugin makes that monitoring accessible through Claude Code, with programmable alert routing and compliance drift tracking.

## Market Size

- **TAM**: Same ~50,000 organizations that vet motor carriers (freight brokerages, 3PLs, shippers with dedicated transportation departments). Every organization that qualifies carriers also needs to monitor them. The monitoring TAM is identical to the vetting TAM.
- **SAM**: ~5,000-8,000 organizations currently paying for carrier monitoring tools (Carrier411 monitoring, Highway monitoring, DAT Carrier Watch, RMIS). These companies already understand the value of ongoing carrier surveillance and are willing to pay for it.
- **SOM**: SearchCarriers users who adopt Carrier Watch through the web UI and want CLI/automation access. Year 1 target: 50-150 Pro+ subscribers driven by Watchdog plugin adoption. The target is smaller than Carrier Intel (Free entry) because Pro+ is the highest tier gate and monitoring is a more specialized need.

The market opportunity is not in competing head-to-head with established monitoring platforms. It is in providing carrier monitoring to organizations that already use SearchCarriers for carrier research and want monitoring integrated into the same workflow. Watchdog converts existing SearchCarriers users from one-time lookup customers into ongoing monitoring subscribers.

## ROI Calculation

| Metric | Without Watchdog | With Watchdog | Impact |
|--------|-----------------|---------------|--------|
| Time to detect carrier status change | Days to months (next re-qualification cycle) | < 30 seconds (next alert poll) | Real-time awareness |
| Insurance lapse detection | At claim time (too late) | Same day as lapse | Prevents uninsured loads |
| Cargo claims from lapsed coverage | 2-5 per year at mid-size brokerage | Near zero (early warning) | $100K-$250K annual savings |
| Compliance audit preparation | 2-4 weeks (manual documentation) | Instant (compliance drift history) | Audit readiness on demand |
| Manual carrier status checks | 200 carriers x 15 min/quarter = 50 hours | Automated monitoring, zero manual checks | 50 hours saved per quarter |
| Alert response time | Hours to days (email buried in inbox) | Minutes (Slack/Telegram real-time) | Faster operational response |

For a brokerage that experiences one cargo claim per year from an undetected insurance lapse ($50K average), the Pro+ subscription at $99/month ($1,188/year) pays for itself 40 times over. Even preventing a single authority-related load rejection saves the cost of re-brokering a load ($500-$2,000 per incident).

## Competitive Positioning

| Capability | SearchCarriers Watchdog | Carrier411 Monitoring | Highway Monitoring | DAT Carrier Watch | RMIS |
|-----------|------------------------|----------------------|-------------------|-------------------|------|
| Watch list via CLI/terminal | Yes (Claude Code native) | No | No | No | No |
| Multi-channel alert routing | Yes (Slack, Telegram, email, webhook) | Email only | Email, in-app | Email, in-app | Email |
| Compliance drift over time | Yes (trend detection) | No | Limited | No | Yes (enterprise) |
| Programmable alert formatting | Yes (per-channel formatting) | No | No | No | API only |
| Real-time FMCSA data | Yes (nightly sync, intraday for critical) | Nightly batch | Real-time | Nightly | Daily |
| Pipeline integration | No (standalone -- works alongside pipeline plugins) | Standalone | Standalone | Standalone | Standalone |
| Price | $99/mo (Pro+) | $35/mo+ | $99/mo+ | Included with DAT | $200/mo+ |

**Key differentiator**: Watchdog is the only carrier monitoring tool that integrates into a developer workflow with programmable alert routing. A compliance manager can set up a watch list, configure Slack alerts for critical changes, and check compliance drift -- all from Claude Code. No browser tabs, no separate monitoring dashboards, no manual email filtering.

**Secondary differentiator**: Compliance drift monitoring. Most competitor tools send point-in-time alerts ("insurance lapsed"). Watchdog tracks changes over time, letting compliance teams see trends: is this carrier's safety record deteriorating? Have they had multiple insurance gaps? Is their MCS-150 chronically overdue? This longitudinal view is what auditors want.

## Revenue Model

Watchdog is a standalone monitoring plugin that drives Pro+ tier subscription revenue:

| Plugin Tool | Min Tier | Revenue Driver |
|------------|----------|----------------|
| `manage_watchlist` | Pro+ ($99/mo) | Gateway to monitoring -- users must add carriers before they get alerts |
| `get_alerts` | Pro+ ($99/mo) | Core value prop -- real-time change detection |
| `route_alert` | Pro+ ($99/mo) | Operational integration -- alerts in the tools teams already use |
| `monitor_compliance` | Pro+ ($99/mo) | Enterprise value -- audit readiness and trend analysis |

**Conversion funnel**: Users enter through Carrier Intel (Free), adopt risk scoring (Pro), and discover they need ongoing monitoring when they realize that a one-time vetting check is not enough. The question "what if this carrier's status changes after I vet them?" is Watchdog's entry point. Pro+ includes Watchdog alongside custom vetting rules from Risk Engine, making the tier upgrade compelling for organizations that need both assessment and monitoring.

**Retention driver**: Watch lists are sticky. Once a compliance team builds a 200-carrier watch list with configured alert routing, switching to a competitor means rebuilding the entire monitoring setup. The operational dependency on daily alerts creates strong retention.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Alert fatigue | High | Medium -- too many low-priority alerts cause users to ignore them | Alert categorization (critical/warning/info), configurable thresholds, digest mode for non-critical changes |
| Alert delivery reliability | Medium | High -- missed critical alert defeats the purpose | Format-only architecture (user's delivery infrastructure handles reliability), retry guidance in docs |
| Data freshness lag | Medium | Medium -- 24-48 hour FMCSA sync delay means some changes are not instant | Document sync frequency, timestamp all alerts, set expectations that this is nightly-batch monitoring not real-time FMCSA polling |
| Carrier Watch API availability | Medium | High -- Watchdog depends on SearchCarriers Carrier Watch API | Retry logic, clear error messages, status page link |
| False positive alerts | Low | Medium -- alerting on changes that did not actually happen | Validate change data against carrier profile, include before/after values in alerts |
| Regulatory concern about automated monitoring | Low | Low -- monitoring public FMCSA data is standard industry practice | All data is public record; document that Watchdog monitors, it does not surveil |
