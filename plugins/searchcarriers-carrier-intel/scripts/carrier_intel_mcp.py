#!/usr/bin/env python3
"""SearchCarriers Carrier Intel MCP Server.

INPUT stage of the stackable pipeline:
  Carrier Intel (INPUT) -> Risk Engine (ANALYSIS) -> Ops Reporter (OUTPUT)

Thin wrapper around the SearchCarriers API. All four tools return structured
JSON; business logic and interpretation are delegated to Claude via skills.
"""

import asyncio
import json
import os
import sys
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Path setup: make the shared utilities importable regardless of cwd.
# ---------------------------------------------------------------------------
_PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from plugins.shared.tier_gate import TierError, check_tier  # noqa: E402

# ---------------------------------------------------------------------------
# MCP SDK
# ---------------------------------------------------------------------------
from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.types import TextContent, Tool  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
API_BASE = "https://searchcarriers.com/api/v1"
REQUEST_TIMEOUT = 15.0  # seconds
SCAC_PATTERN_MAX = 4
VIN_LENGTH = 17

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api_key() -> str:
    """Return the API key from the environment, raising on absence."""
    key = os.environ.get("SEARCHCARRIERS_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "SEARCHCARRIERS_API_KEY environment variable is not set. "
            "Set it before starting the MCP server."
        )
    return key


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def _error_payload(code: str, message: str, detail: Any = None) -> dict[str, Any]:
    """Build a structured error envelope returned as tool output."""
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if detail is not None:
        payload["error"]["detail"] = detail
    return payload


def _detect_search_type(query: str) -> tuple[str, str]:
    """Infer the SearchCarriers query parameter name and value from a raw query.

    Returns:
        A (param_name, value) pair ready for use as a GET parameter.

    Resolution order
    ----------------
    1. Pure digits                 -> dotNumber
    2. Starts with "MC" (case-ins) -> mcNumber  (strip the "MC" prefix)
    3. 17-char alphanumeric        -> vin
    4. 2-4 uppercase letters       -> SCAC endpoint (separate handling)
    5. Fallback                    -> superSearchTerm
    """
    stripped = query.strip()
    upper = stripped.upper()

    if stripped.isdigit():
        return ("dotNumber", stripped)

    if upper.startswith("MC") and upper[2:].isdigit():
        return ("mcNumber", stripped[2:])  # API expects the numeric portion

    if len(stripped) == VIN_LENGTH and stripped.isalnum():
        return ("vin", stripped)

    if (
        2 <= len(stripped) <= SCAC_PATTERN_MAX
        and stripped.isalpha()
        and stripped.isupper()
    ):
        return ("scac", stripped)

    return ("superSearchTerm", stripped)


async def _get(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a GET request and return a parsed JSON dict.

    All HTTP-level and network errors are caught and re-raised as plain
    ``RuntimeError`` with a human-readable message so callers can wrap them
    into structured error payloads.
    """
    try:
        response = await client.get(url, params=params)
    except httpx.TimeoutException:
        raise RuntimeError(f"Request to {url} timed out after {REQUEST_TIMEOUT}s")
    except httpx.RequestError as exc:
        raise RuntimeError(f"Network error reaching {url}: {exc}")

    if response.status_code == 200:
        return response.json()

    # Surface the Retry-After header when rate-limited.
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "unknown")
        raise RuntimeError(
            f"Rate limit hit (429). Retry after {retry_after} seconds."
        )

    status_messages = {
        401: "Invalid or missing API key (401). Check SEARCHCARRIERS_API_KEY.",
        403: "Access forbidden (403). Your tier may not cover this endpoint.",
        404: "Resource not found (404).",
    }
    msg = status_messages.get(
        response.status_code,
        f"Unexpected API response: HTTP {response.status_code}",
    )
    raise RuntimeError(msg)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def _carrier_lookup(arguments: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Search carriers by DOT, MC, name, VIN, SCAC, or location filters.

    Maps the caller's ``search_type`` (or auto-detects it) to the correct
    SearchCarriers query parameter and delegates entirely to the API.
    """
    query: str = arguments["query"]
    search_type: str = arguments.get("search_type", "auto") or "auto"
    state: str | None = arguments.get("state")
    city: str | None = arguments.get("city")
    page: int = int(arguments.get("page", 1))
    per_page: int = int(arguments.get("per_page", 10))

    # Determine query parameter name and value.
    if search_type in ("auto", "") or search_type is None:
        param_name, param_value = _detect_search_type(query)
    elif search_type == "dot":
        param_name, param_value = "dotNumber", query
    elif search_type == "mc":
        param_name, param_value = "mcNumber", query
    elif search_type == "name":
        param_name, param_value = "legalName", query
    elif search_type == "scac":
        param_name, param_value = "scac", query
    elif search_type == "vin":
        param_name, param_value = "vin", query
    else:
        param_name, param_value = "superSearchTerm", query

    # SCAC uses a dedicated endpoint.
    if param_name == "scac":
        url = f"{API_BASE}/search/scac"
        params: dict[str, Any] = {"scac": param_value}
    else:
        url = f"{API_BASE}/search"
        params = {param_name: param_value, "page": page, "per_page": per_page}

    if state:
        params["state"] = state.upper()
    if city:
        params["city"] = city

    async with httpx.AsyncClient(
        headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT
    ) as client:
        try:
            data = await _get(client, url, params=params)
        except RuntimeError as exc:
            return _error_payload("api_error", str(exc))

    return {
        "search_type_used": param_name,
        "query": query,
        "page": page,
        "per_page": per_page,
        "results": data,
    }


async def _carrier_profile(arguments: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Combine search, authority, and insurance data into one carrier profile.

    All three API calls run in parallel via ``asyncio.gather``.
    """
    dot: str = str(arguments["dot_number"]).strip()

    search_url = f"{API_BASE}/search"
    authorities_url = f"{API_BASE}/company/{dot}/authorities"
    insurances_url = f"{API_BASE}/company/{dot}/insurances"

    async with httpx.AsyncClient(
        headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT
    ) as client:
        search_task = _get(client, search_url, params={"dotNumber": dot})
        authorities_task = _get(client, authorities_url)
        insurances_task = _get(client, insurances_url)

        results = await asyncio.gather(
            search_task, authorities_task, insurances_task, return_exceptions=True
        )

    search_result, authorities_result, insurances_result = results

    def _unwrap(result: Any, label: str) -> Any:
        if isinstance(result, Exception):
            return _error_payload("api_error", f"{label}: {result}")
        return result

    carrier_data = _unwrap(search_result, "carrier search")
    authorities_data = _unwrap(authorities_result, "authorities")
    insurances_data = _unwrap(insurances_result, "insurances")

    return {
        "dot_number": dot,
        "carrier": carrier_data,
        "authorities": authorities_data,
        "insurances": insurances_data,
    }


async def _entity_map(arguments: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Discover companies related to a carrier via shared equipment VINs.

    Steps
    -----
    1. Fetch the carrier's own profile (seed carrier).
    2. Fetch equipment list and extract unique VINs.
    3. Search each VIN to find other companies that share the equipment.
    4. Deduplicate related carriers by DOT number and list which VINs they share.
    """
    dot: str = str(arguments["dot_number"]).strip()

    search_url = f"{API_BASE}/search"
    equipment_url = f"{API_BASE}/company/{dot}/equipment"

    async with httpx.AsyncClient(
        headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT
    ) as client:
        # Step 1 & 2: seed carrier + equipment in parallel.
        seed_task = _get(client, search_url, params={"dotNumber": dot})
        equipment_task = _get(client, equipment_url)

        seed_result, equipment_result = await asyncio.gather(
            seed_task, equipment_task, return_exceptions=True
        )

        if isinstance(seed_result, Exception):
            return _error_payload("api_error", f"Seed carrier lookup failed: {seed_result}")
        if isinstance(equipment_result, Exception):
            return _error_payload("api_error", f"Equipment fetch failed: {equipment_result}")

        # Extract VINs from the equipment payload.
        equipment_list: list[dict[str, Any]] = (
            equipment_result if isinstance(equipment_result, list)
            else equipment_result.get("data", equipment_result.get("results", []))
        )
        seen_vins: set[str] = set()
        for item in equipment_list:
            vin = item.get("vin") or item.get("VIN") or item.get("vehicleIdentificationNumber")
            if vin and isinstance(vin, str) and len(vin) == VIN_LENGTH:
                seen_vins.add(vin.upper())

        if not seen_vins:
            return {
                "dot_number": dot,
                "seed_carrier": seed_result,
                "equipment": equipment_list,
                "related_carriers": [],
                "note": "No valid VINs found in equipment list; no entity mapping possible.",
            }

        # Step 3: VIN searches in parallel (bounded by asyncio.gather).
        vin_tasks = {
            vin: _get(client, search_url, params={"vin": vin})
            for vin in seen_vins
        }
        vin_results: dict[str, Any] = {}
        for vin, coro in vin_tasks.items():
            try:
                vin_results[vin] = await coro
            except RuntimeError as exc:
                vin_results[vin] = {"error": str(exc)}

    # Step 4: Collate related carriers, deduplicating by DOT.
    related: dict[str, dict[str, Any]] = {}
    for vin, result in vin_results.items():
        if "error" in result:
            continue
        carriers_from_vin: list[dict[str, Any]] = (
            result if isinstance(result, list)
            else result.get("data", result.get("results", []))
        )
        for carrier in carriers_from_vin:
            carrier_dot = str(
                carrier.get("dotNumber")
                or carrier.get("dot_number")
                or carrier.get("dot")
                or ""
            )
            if not carrier_dot or carrier_dot == dot:
                continue  # Skip the seed carrier itself.
            if carrier_dot not in related:
                related[carrier_dot] = {
                    "dot": carrier_dot,
                    "name": carrier.get("legalName") or carrier.get("name") or "",
                    "shared_vins": [],
                }
            related[carrier_dot]["shared_vins"].append(vin)

    return {
        "dot_number": dot,
        "seed_carrier": seed_result,
        "equipment": equipment_list,
        "related_carriers": list(related.values()),
    }


async def _fleet_summary(arguments: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Return a combined fleet overview from the equipment and vehicles endpoints.

    Both calls run in parallel; the summary section tallies totals and
    aggregates equipment types for a quick overview without needing to parse
    the full lists.
    """
    dot: str = str(arguments["dot_number"]).strip()

    equipment_url = f"{API_BASE}/company/{dot}/equipment"
    vehicles_url = f"{API_BASE}/company/{dot}/vehicles"

    async with httpx.AsyncClient(
        headers=_auth_headers(api_key), timeout=REQUEST_TIMEOUT
    ) as client:
        equipment_task = _get(client, equipment_url)
        vehicles_task = _get(client, vehicles_url)

        equipment_result, vehicles_result = await asyncio.gather(
            equipment_task, vehicles_task, return_exceptions=True
        )

    def _to_list(result: Any, label: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Normalise an API result to a list; return (list, error_or_None)."""
        if isinstance(result, Exception):
            return [], _error_payload("api_error", f"{label}: {result}")
        if isinstance(result, list):
            return result, None
        # Unwrap common envelope shapes.
        for key in ("data", "results", "items"):
            if key in result:
                return result[key], None
        return [], None

    equipment_list, equipment_err = _to_list(equipment_result, "equipment")
    vehicles_list, vehicles_err = _to_list(vehicles_result, "vehicles")

    # Aggregate equipment types for the summary.
    type_counts: dict[str, int] = {}
    for item in equipment_list:
        eq_type = (
            item.get("equipmentType")
            or item.get("equipment_type")
            or item.get("type")
            or "unknown"
        )
        type_counts[str(eq_type)] = type_counts.get(str(eq_type), 0) + 1

    payload: dict[str, Any] = {
        "dot_number": dot,
        "equipment": equipment_list if not equipment_err else equipment_err,
        "vehicles": vehicles_list if not vehicles_err else vehicles_err,
        "summary": {
            "total_equipment": len(equipment_list),
            "total_vehicles": len(vehicles_list),
            "types": type_counts,
        },
    }
    return payload


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

_TOOL_DEFINITIONS: list[Tool] = [
    Tool(
        name="carrier_lookup",
        description=(
            "Search the SearchCarriers database for motor carriers by DOT number, "
            "MC number, legal name, VIN, SCAC code, or free-text term. "
            "Supports optional state and city filters. Returns paginated results. "
            "Min tier: free."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search term: DOT number, MC number (e.g. MC123456), "
                        "VIN (17-char), SCAC (2-4 uppercase letters), company name, "
                        "or any free-text term."
                    ),
                },
                "search_type": {
                    "type": "string",
                    "enum": ["auto", "dot", "mc", "name", "scac", "vin"],
                    "description": (
                        "Force a specific search mode. Defaults to 'auto' which "
                        "detects intent from the query string."
                    ),
                },
                "state": {
                    "type": "string",
                    "description": "Two-letter US state abbreviation to narrow results.",
                },
                "city": {
                    "type": "string",
                    "description": "City name to narrow results.",
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for paginated results (default: 1).",
                    "default": 1,
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page (default: 10).",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="carrier_profile",
        description=(
            "Fetch a full carrier profile by DOT number. Combines the base carrier "
            "record with operating authority status and insurance records into a single "
            "response. Makes three parallel API calls. Min tier: free."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "dot_number": {
                    "type": "string",
                    "description": "The carrier's USDOT number.",
                },
            },
            "required": ["dot_number"],
        },
    ),
    Tool(
        name="entity_map",
        description=(
            "Discover companies related to a carrier by finding other entities that "
            "share equipment VINs. Useful for exposing shell companies, affiliated "
            "fleets, or VIN re-use across carriers. Min tier: pro."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "dot_number": {
                    "type": "string",
                    "description": "The seed carrier's USDOT number.",
                },
            },
            "required": ["dot_number"],
        },
    ),
    Tool(
        name="fleet_summary",
        description=(
            "Return the equipment roster and vehicle list for a carrier, plus an "
            "aggregated summary of total counts and equipment types. Min tier: free."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "dot_number": {
                    "type": "string",
                    "description": "The carrier's USDOT number.",
                },
            },
            "required": ["dot_number"],
        },
    ),
]

# Map tool names to their implementation coroutines.
_TOOL_HANDLERS = {
    "carrier_lookup": _carrier_lookup,
    "carrier_profile": _carrier_profile,
    "entity_map": _entity_map,
    "fleet_summary": _fleet_summary,
}


async def serve() -> None:
    """Entry point: create the MCP server and run it over stdio."""
    # Fail fast if the API key is absent.
    try:
        api_key = _api_key()
    except RuntimeError as exc:
        print(f"[carrier-intel] Startup error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Read caller tier from environment (optional; defaults to "free").
    user_tier = os.environ.get("SEARCHCARRIERS_TIER", "free").strip().lower()

    server = Server("searchcarriers-carrier-intel")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return _TOOL_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        # Tier gate — returns a structured error payload on failure.
        try:
            check_tier(name, user_tier)
        except TierError as exc:
            result = _error_payload(
                "tier_insufficient",
                str(exc),
                {
                    "tool": exc.tool,
                    "required_tier": exc.required,
                    "current_tier": exc.current,
                    "upgrade_url": "https://searchcarriers.com/pricing",
                },
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            result = _error_payload("unknown_tool", f"No handler registered for tool '{name}'.")
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        try:
            result = await handler(arguments, api_key)
        except Exception as exc:  # Final safety net — should not reach here.
            result = _error_payload("internal_error", f"Unexpected error: {exc}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(serve())
