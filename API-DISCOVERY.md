# SearchCarriers API Discovery Notes

**Date**: 2026-02-26
**Base URL**: `https://searchcarriers.com/api/v1`
**Auth**: `Authorization: Bearer {id}|{token}` (Laravel Sanctum)
**Status**: 11 endpoints confirmed, risk-factors + vetting still missing

## Confirmed Endpoints (11)

### Search (3 endpoints)

#### GET /api/v1/search (Super Search)
| Param | Type | Notes |
|-------|------|-------|
| `superSearchTerm` | string | Fuzzy search across name, DOT, MC, etc. |
| `dotNumber` | string | Exact DOT lookup (returns 0 or 1 result) |
| `legalName` | string | Company name search |
| `mcNumber` | string | MC number search (e.g., "MC 1672915") |
| `state` | string | State filter (e.g., "TX") |
| `city` | string | City filter |
| `zipCode` | string | ZIP code filter |
| `vin` | string | VIN search (related companies) |
| `carrierOperation` | string | Operation type ("A" = authorized) |
| `status` | string | Status code ("A" = active) |
| `perPage` | int | Results per page (default: 10) |
| `page` | int | Page number |

Pagination: Laravel standard. Total capped at 1000.

#### GET /api/v1/search/scac (SCAC Lookup)
| Param | Type | Notes |
|-------|------|-------|
| `scac` | string | SCAC code (e.g., "HJBT") |

Returns: `{ code, name, company }` (company is linked carrier or null)

#### GET /api/v1/search?vin= (Related Companies by VIN)
Uses the main search endpoint with `vin` parameter.

### Company Details (7 endpoints)

#### GET /api/v1/company/{dot}/insurances
Paginated. Returns insurance records.
Schema: (returned empty for test carrier - need carrier with active insurance)

#### GET /api/v1/company/{dot}/inspections
Paginated. Returns inspection history with violations and per-unit data.
Schema (58+ fields):
- `inspection_id`, `dot_number`, `report_state`, `report_number`
- `insp_date`, `insp_start_time`, `insp_end_time`, `insp_level_id`
- `location`, `location_desc`, `county_code_state`, `county_code`
- `viol_total`, `oos_total`, `driver_viol_total`, `driver_oos_total`
- `vehicle_viol_total`, `vehicle_oos_total`, `hazmat_viol_total`, `hazmat_oos_total`
- `gross_comb_veh_wt`, `post_acc_ind`, `alcohol_control_sub`, `drug_intrdctn_search`
- `insp_carrier_name`, `insp_carrier_street/city/state/zip_code`
- `violations` (list): `{ part_no, part_no_section, violation_description, ... }`
- `per_units` (list): per-vehicle unit data
- `company` (dict): embedded carrier object

#### GET /api/v1/company/{dot}/authorities
Returns authority status records.
Schema:
- `dot_number`, `docket_number`
- `broker_authority_status`, `contract_authority_status`, `common_authority_status`
- `sub_types`: `{ passenger: bool, property: bool, household_goods: bool }`
- `status_since_date`

#### GET /api/v1/company/{dot}/out-of-service-orders
Paginated. OOS order history.

#### GET /api/v1/company/{dot}/equipment
Equipment/VIN detail.
Schema:
- `type`, `sub_type`, `vin`, `license_state`, `license_number`
- `make`, `model`, `company_vehicle_number`, `year`
- `vin_errors` (bool), `gvwr`, `trim`, `length`

#### GET /api/v1/company/{dot}/vehicles
Vehicle list (simpler than equipment).
Schema:
- `type`, `vin`, `license_plate_state`, `license_plate_number`
- `make`, `company_vehicle_number`

#### GET /api/v1/company/{dot}/watch
GET: Returns current watch status for carrier (data: [])
POST: Adds carrier to watchlist. Returns `{ message: "Company watches updated successfully" }`

### Inspection (2 endpoints)

#### GET /api/v1/inspections (Search)
| Param | Type | Notes |
|-------|------|-------|
| `dot_number` | string | DOT number |

Paginated. Same schema as company/{dot}/inspections.

#### Inspection Details
Endpoint path: NOT FOUND YET. Listed in API docs but couldn't discover route.

### Authority (1 endpoint)

#### GET /api/v1/authority/{dot}/history
Paginated. Authority status change history.

### Export (1 endpoint)

#### GET /api/v1/export
Bulk export carriers.
| Param | Type | Required |
|-------|------|----------|
| `dot_numbers[]` | array | Yes |
| `file_format` | string | Yes |

Returns carrier data array directly (not paginated).

### Company Watches (3 endpoints)

#### GET /api/v1/company/{dot}/watch
Check watch status for a carrier.

#### POST /api/v1/company/{dot}/watch
Add carrier to watchlist.

#### DELETE /api/v1/company/{dot}/watch (assumed)
Remove carrier from watchlist. (Not tested yet)

## Carrier Object Schema (143 fields)

### Identity
- `id` (int), `dot_number` (str), `docket_numbers` (list), `legal_name` (str), `dba_name` (str)
- `dun_bradstreet_no` (str), `scac` (str|null)
- `status_code` (str: A=Active), `add_date` (datetime), `mcs150_date` (datetime)

### Contact
- `phone`, `fax`, `cell_phone`, `email_address` (all str)

### Physical Address
- `phy_street`, `phy_city`, `phy_state`, `phy_zip`, `phy_country`, `phy_cnty`

### Mailing Address
- `carrier_mailing_street`, `_city`, `_state`, `_zip`, `_country`, `_cnty`

### Fleet/Equipment
- `power_units` (int), `truck_units`, `bus_units`, `total_cars` (str)
- `fleetsize` (str: 0/A/B/C/D/E/F), `total_drivers`, `total_cdl` (str)
- `own{truck,tract,trail,coach,...}` (owned equipment counts)
- `trm{truck,tract,...}` (term-leased), `trp{truck,...}` (trip-leased)

### Operations
- `carrier_operation` (str), `operation_classifications` (list)
- `carship` (list: Carrier/Broker/Shipper), `hm_ind` (hazmat Y/N)
- `interstate_beyond/within_100_miles`, `intrastate_beyond/within_100_miles`

### Safety
- `safety_rating`, `safety_rating_date`, `review_type`, `review_date`, `review_id`
- `recordable_crash_rate`, `mcsipstep`, `mcsipdate`

### Cargo Types (30 fields, "X" if carried)
- `crgo_genfreight` through `crgo_cargoothr` + `crgo_cargoothr_desc`
- `cargo_carried` (list: summary)

### Other
- `company_officers` (list of str), `prior_revoke_flag/dot_number`
- `created_at`, `updated_at`

## Rate Limiting
- Use `Retry-After` header, exponential backoff
- Cache responses (5 min TTL recommended)
- Max ~3 requests/second recommended
- Implement request queue for high-volume apps

## Still Missing (from API Reference)

### Risk Factors
- `GET Risk Factors` - 404 on all tested patterns. May be:
  - Different API version
  - Tier-gated (returns 404 instead of 403?)
  - Different route naming

### Vetting Engine
- `GET Company Vetting Report` - 404 on all tested patterns

### Other Missing
- `GET Insurances` (company/{dot}/insurances works but returned empty)
- `GET Service Areas` - not found
- `GET Company Physical Geo Location` - not found
- `GET Inspection Details` (by inspection_id) - not found
- Remaining "+3 more" under Company Details
- Remaining "+4 more" under Company Details (7 total, found 7 including watch)

## Questions for Garret
1. What are the exact routes for risk-factors and vetting-report?
2. Are these tier-gated? What error does a free account get?
3. Service Areas and Geo Location endpoints - what are the paths?
4. Inspection Details by inspection_id - what's the route?
5. DELETE /company/{dot}/watch - confirm route
6. What file_format values does export accept? (json, csv, xlsx?)
7. Full list of Company Watches endpoints (3 listed in docs)
