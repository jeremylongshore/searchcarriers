---
name: searchcarriers-vetting-rules
description: >-
  Applies configurable carrier qualification rules to produce pass/fail/review vetting
  decisions with detailed reports. Use when running a full vetting check or building custom qualification criteria.
allowed-tools: "Read,Grep,Bash(curl:*),Bash(python:*)"
metadata:
  author: "Jeremy Longshore <jeremy@intentsolutions.io>"
  version: 1.0.0
  license: BUSL-1.1
  tier: proplus
---

# Vetting Rules Engine

## Overview

Carrier vetting is the process of determining whether a motor carrier meets the safety, legal, and operational standards required to haul freight. Every shipper and broker has their own criteria — some require Satisfactory safety ratings only, others accept Conditional; some demand 50-truck minimums, others work with owner-operators; some refuse carriers under 2 years old, others will take new entrants with clean records.

This skill is the orchestration layer. It pulls data from multiple SearchCarriers API endpoints, runs each data point against a configurable rule set, and produces a structured vetting report with a clear PASS / FAIL / REVIEW WITH EXCEPTIONS verdict. It supports default rules, custom rules files, and inline rule overrides.

## Prerequisites

- **Minimum tier**: Pro+
- Environment variable `SEARCHCARRIERS_API_KEY` must be set with a valid Pro+-tier API key.
- The carrier's DOT number must be known. If only an MC number or name is available, use the `/search` endpoint first.
- `curl` and `python3` must be available in the execution environment.
- Optional: A custom rules file at `{baseDir}/rules/default-rules.json` for persistent rule configuration.

## Instructions

### Step 1: Load the Rule Set

Check for a custom rules file first. If none exists, use the default rules. If the user specifies inline overrides, merge them on top.

```bash
# Check for custom rules file
cat {baseDir}/rules/default-rules.json 2>/dev/null
```

**Default Rule Set** (used when no custom file exists):

```json
{
  "rules": {
    "active_status": {
      "enabled": true,
      "required_status": "A",
      "on_fail": "FAIL",
      "description": "Carrier must have active FMCSA status"
    },
    "operating_authority": {
      "enabled": true,
      "required_types": ["common"],
      "required_status": "authorized",
      "on_fail": "FAIL",
      "description": "Carrier must have active operating authority"
    },
    "insurance_active": {
      "enabled": true,
      "require_bipd": true,
      "on_fail": "FAIL",
      "description": "Carrier must have active BIPD insurance"
    },
    "insurance_minimum": {
      "enabled": true,
      "minimum_bipd": 1000000,
      "on_fail": "FAIL",
      "description": "BIPD insurance must meet minimum coverage"
    },
    "mcs150_current": {
      "enabled": true,
      "max_age_months": 24,
      "on_fail": "REVIEW",
      "description": "MCS-150 must be filed within 24 months"
    },
    "safety_rating": {
      "enabled": true,
      "pass_ratings": ["S", "Satisfactory"],
      "review_ratings": ["C", "Conditional"],
      "fail_ratings": ["U", "Unsatisfactory"],
      "none_action": "REVIEW",
      "description": "Safety rating must be Satisfactory or Conditional"
    },
    "authority_age": {
      "enabled": true,
      "minimum_months": 18,
      "on_fail": "REVIEW",
      "description": "Authority should be at least 18 months old"
    },
    "no_prior_revocation": {
      "enabled": true,
      "on_fail": "REVIEW",
      "description": "Carrier should not have prior revocation history"
    },
    "fleet_size": {
      "enabled": true,
      "minimum_power_units": 1,
      "on_fail": "REVIEW",
      "description": "Carrier must meet minimum fleet size"
    },
    "oos_rate": {
      "enabled": true,
      "max_vehicle_oos_pct": 30,
      "max_driver_oos_pct": 30,
      "on_fail": "REVIEW",
      "description": "Out-of-service rate must be below threshold"
    },
    "hazmat_compliance": {
      "enabled": true,
      "only_if_hazmat": true,
      "require_no_hazmat_violations": true,
      "on_fail": "FAIL",
      "description": "Hazmat carriers must have no hazmat violations"
    }
  },
  "verdict_logic": {
    "any_fail": "FAIL",
    "any_review_no_fail": "REVIEW WITH EXCEPTIONS",
    "all_pass": "PASS"
  }
}
```

If the user provides inline overrides, merge them. For example: "vet with 50 unit minimum and Satisfactory only" means set `fleet_size.minimum_power_units` to 50 and remove "Conditional" from `safety_rating.pass_ratings`, moving it to `safety_rating.fail_ratings`.

### Step 2: Gather All Required Data

Fetch data from multiple endpoints. Make these calls in sequence to handle dependencies.

```bash
# 1. Get carrier base record (143 fields)
curl -s -H "Authorization: Bearer $SEARCHCARRIERS_API_KEY" \
  "https://searchcarriers.com/api/v1/search?dotNumber={dot}"

# 2. Get insurance records
curl -s -H "Authorization: Bearer $SEARCHCARRIERS_API_KEY" \
  "https://searchcarriers.com/api/v1/company/{dot}/insurances?perPage=50"

# 3. Get authority status
curl -s -H "Authorization: Bearer $SEARCHCARRIERS_API_KEY" \
  "https://searchcarriers.com/api/v1/company/{dot}/authorities"

# 4. Get authority history
curl -s -H "Authorization: Bearer $SEARCHCARRIERS_API_KEY" \
  "https://searchcarriers.com/api/v1/authority/{dot}/history?perPage=50"

# 5. Get inspections (for OOS rate and violations)
curl -s -H "Authorization: Bearer $SEARCHCARRIERS_API_KEY" \
  "https://searchcarriers.com/api/v1/company/{dot}/inspections?perPage=50"

# 6. Get out-of-service orders
curl -s -H "Authorization: Bearer $SEARCHCARRIERS_API_KEY" \
  "https://searchcarriers.com/api/v1/company/{dot}/out-of-service-orders?perPage=50"
```

### Step 3: Execute Each Rule

Run every enabled rule against the gathered data. For each rule, produce a result object:

```python
import json
from datetime import datetime, timedelta

def execute_rules(carrier, insurance, authority, authority_history, inspections, oos_orders, rules):
    results = []

    # Rule 1: Active Status
    if rules['active_status']['enabled']:
        status = carrier.get('status_code', '')
        results.append({
            "rule": "active_status",
            "description": rules['active_status']['description'],
            "expected": f"status_code = '{rules['active_status']['required_status']}'",
            "actual": f"status_code = '{status}'",
            "verdict": "PASS" if status == rules['active_status']['required_status']
                       else rules['active_status']['on_fail']
        })

    # Rule 2: Operating Authority
    if rules['operating_authority']['enabled']:
        auth_status = authority.get('common_authority_status', '')
        is_authorized = auth_status.lower() == rules['operating_authority']['required_status']
        results.append({
            "rule": "operating_authority",
            "description": rules['operating_authority']['description'],
            "expected": f"common_authority_status = '{rules['operating_authority']['required_status']}'",
            "actual": f"common_authority_status = '{auth_status}'",
            "verdict": "PASS" if is_authorized else rules['operating_authority']['on_fail']
        })

    # Rule 3: Insurance Active
    if rules['insurance_active']['enabled']:
        active_bipd = [i for i in insurance
                       if i.get('insurance_status', '').lower() == 'active'
                       and ('bipd' in i.get('insurance_type', '').lower()
                            or 'bodily' in i.get('insurance_type', '').lower())]
        results.append({
            "rule": "insurance_active",
            "description": rules['insurance_active']['description'],
            "expected": "At least one active BIPD policy",
            "actual": f"{len(active_bipd)} active BIPD policies found",
            "verdict": "PASS" if len(active_bipd) > 0 else rules['insurance_active']['on_fail']
        })

    # Rule 4: Insurance Minimum
    if rules['insurance_minimum']['enabled']:
        max_bipd = 0
        for ins in insurance:
            if (ins.get('insurance_status', '').lower() == 'active'
                and ('bipd' in ins.get('insurance_type', '').lower()
                     or 'bodily' in ins.get('insurance_type', '').lower())):
                amt = ins.get('coverage_amount', 0)
                if isinstance(amt, str):
                    amt = int(amt.replace(',', '').replace('$', ''))
                max_bipd = max(max_bipd, amt)
        required = rules['insurance_minimum']['minimum_bipd']
        results.append({
            "rule": "insurance_minimum",
            "description": rules['insurance_minimum']['description'],
            "expected": f"BIPD >= ${required:,}",
            "actual": f"BIPD = ${max_bipd:,}",
            "verdict": "PASS" if max_bipd >= required else rules['insurance_minimum']['on_fail']
        })

    # Rule 5: MCS-150 Current
    if rules['mcs150_current']['enabled']:
        mcs_date_str = carrier.get('mcs150_date', '')
        if mcs_date_str:
            mcs_date = datetime.strptime(mcs_date_str, '%Y-%m-%d')
            age_months = (datetime.now() - mcs_date).days / 30
            max_age = rules['mcs150_current']['max_age_months']
            results.append({
                "rule": "mcs150_current",
                "description": rules['mcs150_current']['description'],
                "expected": f"MCS-150 filed within {max_age} months",
                "actual": f"MCS-150 filed {int(age_months)} months ago ({mcs_date_str})",
                "verdict": "PASS" if age_months <= max_age else rules['mcs150_current']['on_fail']
            })
        else:
            results.append({
                "rule": "mcs150_current",
                "description": rules['mcs150_current']['description'],
                "expected": f"MCS-150 filed within {rules['mcs150_current']['max_age_months']} months",
                "actual": "No MCS-150 date on record",
                "verdict": rules['mcs150_current']['on_fail']
            })

    # Rule 6: Safety Rating
    if rules['safety_rating']['enabled']:
        rating = carrier.get('safety_rating', '')
        rating_date = carrier.get('safety_rating_date', 'N/A')
        if not rating or rating.lower() == 'none':
            verdict = rules['safety_rating']['none_action']
        elif rating in rules['safety_rating']['pass_ratings']:
            verdict = "PASS"
        elif rating in rules['safety_rating']['review_ratings']:
            verdict = "REVIEW"
        elif rating in rules['safety_rating']['fail_ratings']:
            verdict = "FAIL"
        else:
            verdict = "REVIEW"
        results.append({
            "rule": "safety_rating",
            "description": rules['safety_rating']['description'],
            "expected": f"Rating in {rules['safety_rating']['pass_ratings']}",
            "actual": f"Rating = '{rating}' (as of {rating_date})",
            "verdict": verdict
        })

    # Rule 7: Authority Age
    if rules['authority_age']['enabled']:
        add_date_str = carrier.get('add_date', '')
        if add_date_str:
            add_date = datetime.strptime(add_date_str, '%Y-%m-%d')
            age_months = (datetime.now() - add_date).days / 30
            min_months = rules['authority_age']['minimum_months']
            results.append({
                "rule": "authority_age",
                "description": rules['authority_age']['description'],
                "expected": f"Authority age >= {min_months} months",
                "actual": f"Authority age = {int(age_months)} months (since {add_date_str})",
                "verdict": "PASS" if age_months >= min_months else rules['authority_age']['on_fail']
            })
        else:
            results.append({
                "rule": "authority_age",
                "description": rules['authority_age']['description'],
                "expected": f"Authority age >= {rules['authority_age']['minimum_months']} months",
                "actual": "No add_date on record",
                "verdict": rules['authority_age']['on_fail']
            })

    # Rule 8: No Prior Revocation
    if rules['no_prior_revocation']['enabled']:
        revoke_flag = carrier.get('prior_revoke_flag', 'N')
        prev_dot = carrier.get('prior_revoke_dot_number', '')
        results.append({
            "rule": "no_prior_revocation",
            "description": rules['no_prior_revocation']['description'],
            "expected": "prior_revoke_flag = 'N'",
            "actual": f"prior_revoke_flag = '{revoke_flag}'" +
                      (f" (prev DOT: {prev_dot})" if prev_dot else ""),
            "verdict": "PASS" if revoke_flag != 'Y' else rules['no_prior_revocation']['on_fail']
        })

    # Rule 9: Fleet Size
    if rules['fleet_size']['enabled']:
        units = carrier.get('power_units', 0)
        if isinstance(units, str):
            units = int(units) if units.isdigit() else 0
        min_units = rules['fleet_size']['minimum_power_units']
        results.append({
            "rule": "fleet_size",
            "description": rules['fleet_size']['description'],
            "expected": f"power_units >= {min_units}",
            "actual": f"power_units = {units}",
            "verdict": "PASS" if units >= min_units else rules['fleet_size']['on_fail']
        })

    # Rule 10: OOS Rate
    if rules['oos_rate']['enabled']:
        total_inspections = len(inspections) if inspections else 0
        vehicle_oos = sum(1 for i in inspections if i.get('vehicle_oos', False)) if inspections else 0
        driver_oos = sum(1 for i in inspections if i.get('driver_oos', False)) if inspections else 0

        veh_pct = (vehicle_oos / total_inspections * 100) if total_inspections > 0 else 0
        drv_pct = (driver_oos / total_inspections * 100) if total_inspections > 0 else 0

        max_veh = rules['oos_rate']['max_vehicle_oos_pct']
        max_drv = rules['oos_rate']['max_driver_oos_pct']

        passed = veh_pct <= max_veh and drv_pct <= max_drv
        results.append({
            "rule": "oos_rate",
            "description": rules['oos_rate']['description'],
            "expected": f"Vehicle OOS <= {max_veh}%, Driver OOS <= {max_drv}%",
            "actual": f"Vehicle OOS = {veh_pct:.1f}% ({vehicle_oos}/{total_inspections}), "
                      f"Driver OOS = {drv_pct:.1f}% ({driver_oos}/{total_inspections})",
            "verdict": "PASS" if passed else rules['oos_rate']['on_fail']
        })

    # Rule 11: Hazmat Compliance
    if rules['hazmat_compliance']['enabled']:
        hm_ind = carrier.get('hm_ind', 'N')
        if rules['hazmat_compliance']['only_if_hazmat'] and hm_ind != 'Y':
            results.append({
                "rule": "hazmat_compliance",
                "description": rules['hazmat_compliance']['description'],
                "expected": "N/A (carrier does not haul hazmat)",
                "actual": f"hm_ind = '{hm_ind}'",
                "verdict": "PASS"
            })
        else:
            hazmat_violations = []
            for insp in (inspections or []):
                for v in insp.get('violations', []):
                    if 'hazmat' in v.get('description', '').lower() or \
                       'hm' in v.get('group', '').lower():
                        hazmat_violations.append(v)

            results.append({
                "rule": "hazmat_compliance",
                "description": rules['hazmat_compliance']['description'],
                "expected": "No hazmat violations",
                "actual": f"{len(hazmat_violations)} hazmat violations found",
                "verdict": "PASS" if len(hazmat_violations) == 0
                           else rules['hazmat_compliance']['on_fail']
            })

    return results
```

### Step 4: Calculate the Overall Verdict

Apply the verdict logic from the rule set:

```python
def calculate_verdict(results, verdict_logic):
    verdicts = [r['verdict'] for r in results]

    if 'FAIL' in verdicts:
        overall = verdict_logic.get('any_fail', 'FAIL')
        fail_rules = [r for r in results if r['verdict'] == 'FAIL']
        reason = f"Failed {len(fail_rules)} rule(s): " + \
                 ", ".join(r['rule'] for r in fail_rules)
    elif 'REVIEW' in verdicts:
        overall = verdict_logic.get('any_review_no_fail', 'REVIEW WITH EXCEPTIONS')
        review_rules = [r for r in results if r['verdict'] == 'REVIEW']
        reason = f"{len(review_rules)} rule(s) require review: " + \
                 ", ".join(r['rule'] for r in review_rules)
    else:
        overall = verdict_logic.get('all_pass', 'PASS')
        reason = "All rules passed"

    return overall, reason
```

### Step 5: Generate the Vetting Report

Produce a comprehensive, structured vetting report:

```
========================================
CARRIER VETTING REPORT
========================================
DOT Number: {dot_number}
Carrier: {legal_name}
DBA: {dba_name}
MC Number: {mc_number}
Report Date: {today}
Rule Set: {default / custom file path / inline}

CARRIER SNAPSHOT
  Status: {status_code} ({status_description})
  Operation: {carrier_operation}
  Fleet: {power_units} power units, {total_drivers} drivers
  Safety Rating: {safety_rating} ({safety_rating_date})
  Hazmat: {hm_ind}
  Officers: {company_officers}

========================================
RULE RESULTS
========================================

  [1] ACTIVE STATUS                    {PASS/FAIL/REVIEW}
      Expected: status_code = 'A'
      Actual:   status_code = '{value}'

  [2] OPERATING AUTHORITY              {PASS/FAIL/REVIEW}
      Expected: common_authority_status = 'authorized'
      Actual:   common_authority_status = '{value}'

  [3] INSURANCE ACTIVE                 {PASS/FAIL/REVIEW}
      Expected: At least one active BIPD policy
      Actual:   {count} active BIPD policies found

  [4] INSURANCE MINIMUM                {PASS/FAIL/REVIEW}
      Expected: BIPD >= ${minimum}
      Actual:   BIPD = ${actual}

  [5] MCS-150 CURRENT                  {PASS/FAIL/REVIEW}
      Expected: Filed within 24 months
      Actual:   Filed {X} months ago

  [6] SAFETY RATING                    {PASS/FAIL/REVIEW}
      Expected: Satisfactory or Conditional
      Actual:   {rating}

  [7] AUTHORITY AGE                    {PASS/FAIL/REVIEW}
      Expected: >= 18 months
      Actual:   {X} months

  [8] NO PRIOR REVOCATION              {PASS/FAIL/REVIEW}
      Expected: prior_revoke_flag = 'N'
      Actual:   prior_revoke_flag = '{value}'

  [9] FLEET SIZE                       {PASS/FAIL/REVIEW}
      Expected: >= {minimum} power units
      Actual:   {count} power units

  [10] OOS RATE                        {PASS/FAIL/REVIEW}
       Expected: Vehicle OOS <= 30%, Driver OOS <= 30%
       Actual:   Vehicle OOS = {X}%, Driver OOS = {Y}%

  [11] HAZMAT COMPLIANCE               {PASS/FAIL/REVIEW}
       Expected: No hazmat violations
       Actual:   {count} violations found

========================================
VERDICT
========================================
  Rules Passed:  {count}/{total}
  Rules Failed:  {count}/{total}
  Rules Review:  {count}/{total}

  OVERALL: {PASS / FAIL / REVIEW WITH EXCEPTIONS}
  Reason: {explanation}

========================================
NOTES
========================================
  [Any additional context, warnings, or recommendations]
```

### Custom Rules Examples

Users can override default rules inline. Parse their request and modify the rule set:

| User Says | Rule Modification |
|-----------|-------------------|
| "require 50 power units minimum" | Set `fleet_size.minimum_power_units` = 50 |
| "Satisfactory only, no Conditional" | Remove "Conditional" from `safety_rating.pass_ratings`, add to `fail_ratings` |
| "ignore fleet size" | Set `fleet_size.enabled` = false |
| "max 20% OOS rate" | Set `oos_rate.max_vehicle_oos_pct` = 20, `oos_rate.max_driver_oos_pct` = 20 |
| "must have cargo insurance" | Add a new rule checking for active cargo insurance |
| "authority must be 3+ years" | Set `authority_age.minimum_months` = 36 |
| "$5M insurance minimum" | Set `insurance_minimum.minimum_bipd` = 5000000 |

Always echo back the interpreted rule changes to the user before running the vetting so they can confirm.

## Examples

### Standard vetting run

**User prompt**: "Vet DOT 12345"

Load default rules, fetch all data from the 6 API endpoints, execute all 11 rules, produce the full vetting report with PASS/FAIL/REVIEW verdict.

### Vetting with custom requirements

**User prompt**: "Vet this carrier with 50 unit minimum and no conditional ratings"

Acknowledge the custom requirements: "Running vetting with modified rules: fleet_size.minimum_power_units = 50, safety_rating moved Conditional to fail_ratings." Then execute the full vetting with the modified rule set.

### Vetting by company name

**User prompt**: "Run full vetting on Pacific Transport"

First search by name: `/search?legalName=PACIFIC%20TRANSPORT`. If multiple results, present them and ask the user to confirm the correct carrier. Then run the full vetting on the confirmed DOT number.

### Batch vetting

**User prompt**: "Vet these 3 carriers: DOT 12345, DOT 67890, DOT 11111"

Run the full vetting for each carrier sequentially. Produce individual reports for each, then a summary table:

```
BATCH VETTING SUMMARY
| DOT    | Carrier Name      | Verdict              | Failed Rules |
|--------|-------------------|----------------------|--------------|
| 12345  | ABC Trucking      | PASS                 | —            |
| 67890  | XYZ Logistics     | FAIL                 | insurance    |
| 11111  | Quick Freight     | REVIEW W/ EXCEPTIONS | authority_age|
```

## Error Handling

| Error | Cause | Resolution |
|---|---|---|
| `401 Unauthorized` | Invalid or expired API key | Verify `SEARCHCARRIERS_API_KEY` is set with Pro+-tier access |
| `404 Not Found` | DOT number does not exist | Verify the DOT number; try searching by name or MC number |
| `429 Too Many Requests` | Rate limit exceeded (vetting hits 6 endpoints) | Implement sequential calls with brief pauses between endpoints |
| Custom rules file not found | `{baseDir}/rules/default-rules.json` does not exist | Fall back to built-in default rules; inform the user |
| Partial data | One endpoint returns data, another returns empty | Run rules against available data; mark unavailable checks as REVIEW with "insufficient data" note |
| Inspection data missing | No inspections on record (common for very new carriers) | Set OOS rate to 0/0 and mark OOS rule as REVIEW with "no inspection data available" |
| Multiple search results | Name search returns multiple carriers | Present all matches with DOT, name, city, state and ask user to confirm the correct carrier |

When any API call fails during a vetting run, do not abort the entire process. Execute remaining rules with available data and clearly mark which rules could not be evaluated. A partial vetting report is more useful than no report.

## Resources

- FMCSA Safety Fitness Determination: 49 CFR Part 385
- FMCSA Safety Rating Methodology: https://csa.fmcsa.dot.gov
- National OOS Rate Averages: Published annually by CVSA (Commercial Vehicle Safety Alliance)
- MCS-150 Filing Requirements: 49 CFR 390.19
- SearchCarriers API Documentation: `{baseDir}/docs/api-reference.md`
- Default rules configuration: `{baseDir}/rules/default-rules.json`
- Custom rules examples: `{baseDir}/rules/examples/`
- FMCSA SAFER System: https://safer.fmcsa.dot.gov
