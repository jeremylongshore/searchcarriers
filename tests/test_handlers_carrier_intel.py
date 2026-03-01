"""Integration tests for carrier_intel_mcp handler functions.

Tests exercise the actual handler logic with respx intercepting HTTP calls
at the transport layer. No real API calls are made unless marked @integration.
"""

import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

_repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(_repo_root))
sys.path.insert(
    0,
    str(_repo_root / "plugins" / "searchcarriers-carrier-intel" / "scripts"),
)

from carrier_intel_mcp import (  # noqa: E402
    API_BASE,
    _carrier_lookup,
    _carrier_profile,
    _entity_map,
    _fleet_summary,
)
from conftest import assert_error_payload  # noqa: E402


# ---------------------------------------------------------------------------
# _carrier_lookup
# ---------------------------------------------------------------------------


class TestCarrierLookup:
    """Tests for the carrier_lookup handler."""

    async def test_auto_detect_dot(self, fake_api_key, carrier_jbhunt):
        """Pure digits auto-detected as dotNumber."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            result = await _carrier_lookup({"query": "299569"}, fake_api_key)

        assert result["search_type_used"] == "dotNumber"
        assert result["query"] == "299569"
        assert "results" in result

    async def test_auto_detect_scac(self, fake_api_key, carrier_jbhunt):
        """2-4 uppercase letters auto-detected as SCAC; hits /search/scac."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search/scac").mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            result = await _carrier_lookup({"query": "JBHT"}, fake_api_key)

        assert result["search_type_used"] == "scac"

    async def test_explicit_search_type(self, fake_api_key, carrier_jbhunt):
        """Explicit search_type='name' bypasses auto-detection."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            result = await _carrier_lookup(
                {"query": "JB Hunt", "search_type": "name"}, fake_api_key
            )

        assert result["search_type_used"] == "legalName"

    async def test_state_filter(self, fake_api_key, carrier_jbhunt):
        """State filter is passed through and uppercased."""
        with respx.mock(base_url=API_BASE) as router:
            route = router.get("/search").mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            result = await _carrier_lookup(
                {"query": "299569", "state": "ar"}, fake_api_key
            )

        assert "results" in result
        # Verify the state param was sent (uppercased)
        assert route.calls[0].request.url.params["state"] == "AR"

    async def test_api_401_error(self, fake_api_key):
        """401 response produces an error payload."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(401, json={"error": "unauthorized"})
            )
            result = await _carrier_lookup({"query": "299569"}, fake_api_key)

        assert_error_payload(result, "api_error")
        assert "401" in result["error"]["message"]

    async def test_rate_limit_429(self, fake_api_key):
        """429 response produces an error payload with retry info."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(
                    429, headers={"Retry-After": "5"}, json={}
                )
            )
            result = await _carrier_lookup({"query": "299569"}, fake_api_key)

        assert_error_payload(result, "api_error")
        assert "429" in result["error"]["message"]


# ---------------------------------------------------------------------------
# _carrier_profile
# ---------------------------------------------------------------------------


class TestCarrierProfile:
    """Tests for the carrier_profile handler."""

    async def test_happy_path(
        self, fake_api_key, carrier_jbhunt, authorities_sample, insurances_active
    ):
        """Three parallel calls assembled into profile."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            router.get("/company/299569/authorities").mock(
                return_value=httpx.Response(200, json=authorities_sample)
            )
            router.get("/company/299569/insurances").mock(
                return_value=httpx.Response(200, json=insurances_active)
            )
            result = await _carrier_profile(
                {"dot_number": "299569"}, fake_api_key
            )

        assert result["dot_number"] == "299569"
        assert "carrier" in result
        assert "authorities" in result
        assert "insurances" in result
        # carrier should be the raw search envelope
        assert "data" in result["carrier"]

    async def test_search_failure(self, fake_api_key):
        """Search failure produces error payload in carrier field."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(500, json={})
            )
            router.get("/company/999/authorities").mock(
                return_value=httpx.Response(200, json={"data": []})
            )
            router.get("/company/999/insurances").mock(
                return_value=httpx.Response(200, json={"data": []})
            )
            result = await _carrier_profile({"dot_number": "999"}, fake_api_key)

        assert result["dot_number"] == "999"
        # The carrier field should contain an error payload (gather returns exceptions)
        assert "error" in result["carrier"]

    async def test_partial_failure_authorities(
        self, fake_api_key, carrier_jbhunt, insurances_active
    ):
        """Authorities 500 is wrapped as error; search + insurances succeed."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            router.get("/company/299569/authorities").mock(
                return_value=httpx.Response(500, json={})
            )
            router.get("/company/299569/insurances").mock(
                return_value=httpx.Response(200, json=insurances_active)
            )
            result = await _carrier_profile(
                {"dot_number": "299569"}, fake_api_key
            )

        # Search should succeed
        assert "data" in result["carrier"]
        # Authorities should be error payload
        assert "error" in result["authorities"]
        # Insurances should succeed
        assert "data" in result["insurances"]

    async def test_whitespace_strip(self, fake_api_key, carrier_jbhunt):
        """Leading/trailing whitespace in dot_number is stripped."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            router.get("/company/299569/authorities").mock(
                return_value=httpx.Response(200, json={"data": []})
            )
            router.get("/company/299569/insurances").mock(
                return_value=httpx.Response(200, json={"data": []})
            )
            result = await _carrier_profile(
                {"dot_number": "  299569  "}, fake_api_key
            )

        assert result["dot_number"] == "299569"


# ---------------------------------------------------------------------------
# _entity_map
# ---------------------------------------------------------------------------


class TestEntityMap:
    """Tests for the entity_map handler."""

    async def test_no_vins_empty_related(self, fake_api_key, carrier_jbhunt):
        """Equipment with no valid VINs returns empty related_carriers."""
        equipment_no_vins = {"data": [{"make": "Freightliner"}]}
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            router.get("/company/299569/equipment").mock(
                return_value=httpx.Response(200, json=equipment_no_vins)
            )
            result = await _entity_map(
                {"dot_number": "299569"}, fake_api_key
            )

        assert result["related_carriers"] == []
        assert "note" in result

    async def test_vin_finds_related_carrier(
        self, fake_api_key, carrier_jbhunt, equipment_sample
    ):
        """VIN search discovers a related carrier."""
        related_carrier = {
            "data": [
                {
                    "dotNumber": "888888",
                    "legalName": "RELATED CARRIER LLC",
                }
            ]
        }
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search", params__contains={"dotNumber": "299569"}).mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            router.get("/company/299569/equipment").mock(
                return_value=httpx.Response(200, json=equipment_sample)
            )
            # All VIN searches return the related carrier
            router.get("/search", params__contains={"vin": "1HGCM82633A004352"}).mock(
                return_value=httpx.Response(200, json=related_carrier)
            )
            router.get("/search", params__contains={"vin": "3AKJHHDR5NSMP4821"}).mock(
                return_value=httpx.Response(200, json=related_carrier)
            )
            router.get("/search", params__contains={"vin": "1JJV532D8KL456789"}).mock(
                return_value=httpx.Response(200, json=related_carrier)
            )
            result = await _entity_map(
                {"dot_number": "299569"}, fake_api_key
            )

        assert len(result["related_carriers"]) >= 1
        related = result["related_carriers"][0]
        assert related["dot"] == "888888"
        assert related["name"] == "RELATED CARRIER LLC"
        assert len(related["shared_vins"]) >= 1

    async def test_seed_carrier_excluded(
        self, fake_api_key, carrier_jbhunt, equipment_sample
    ):
        """Seed carrier's own DOT is excluded from related_carriers."""
        # VIN search returns the seed carrier itself
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search", params__contains={"dotNumber": "299569"}).mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            router.get("/company/299569/equipment").mock(
                return_value=httpx.Response(200, json=equipment_sample)
            )
            # VIN searches return only the seed carrier
            for vin in ["1HGCM82633A004352", "3AKJHHDR5NSMP4821", "1JJV532D8KL456789"]:
                router.get("/search", params__contains={"vin": vin}).mock(
                    return_value=httpx.Response(200, json=carrier_jbhunt)
                )
            result = await _entity_map(
                {"dot_number": "299569"}, fake_api_key
            )

        assert result["related_carriers"] == []

    async def test_equipment_fetch_failure(self, fake_api_key, carrier_jbhunt):
        """Equipment fetch failure returns error payload."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/search").mock(
                return_value=httpx.Response(200, json=carrier_jbhunt)
            )
            router.get("/company/299569/equipment").mock(
                return_value=httpx.Response(500, json={})
            )
            result = await _entity_map(
                {"dot_number": "299569"}, fake_api_key
            )

        assert_error_payload(result, "api_error")


# ---------------------------------------------------------------------------
# _fleet_summary
# ---------------------------------------------------------------------------


class TestFleetSummary:
    """Tests for the fleet_summary handler."""

    async def test_summary_counts(self, fake_api_key, equipment_sample):
        """Summary tallies equipment types correctly (2 trucks + 1 trailer)."""
        vehicles = {"data": [{"id": 1}, {"id": 2}]}
        with respx.mock(base_url=API_BASE) as router:
            router.get("/company/299569/equipment").mock(
                return_value=httpx.Response(200, json=equipment_sample)
            )
            router.get("/company/299569/vehicles").mock(
                return_value=httpx.Response(200, json=vehicles)
            )
            result = await _fleet_summary(
                {"dot_number": "299569"}, fake_api_key
            )

        assert result["dot_number"] == "299569"
        assert result["summary"]["total_equipment"] == 3
        assert result["summary"]["total_vehicles"] == 2
        assert result["summary"]["types"]["Truck Tractor"] == 2
        assert result["summary"]["types"]["Trailer"] == 1

    async def test_equipment_error_propagated(self, fake_api_key):
        """Equipment fetch error is propagated in the equipment field."""
        vehicles = {"data": []}
        with respx.mock(base_url=API_BASE) as router:
            router.get("/company/299569/equipment").mock(
                return_value=httpx.Response(500, json={})
            )
            router.get("/company/299569/vehicles").mock(
                return_value=httpx.Response(200, json=vehicles)
            )
            result = await _fleet_summary(
                {"dot_number": "299569"}, fake_api_key
            )

        # Equipment field should be an error payload
        assert "error" in result["equipment"]
        # Summary should reflect 0 equipment
        assert result["summary"]["total_equipment"] == 0


# ---------------------------------------------------------------------------
# Live integration test (opt-in)
# ---------------------------------------------------------------------------


class TestCarrierLookupLive:
    """Live API tests — only run when SEARCHCARRIERS_API_KEY is set."""

    @pytest.mark.integration
    async def test_structural_response(self, live_api_key):
        """Real API response has expected structure."""
        result = await _carrier_lookup({"query": "299569"}, live_api_key)

        assert "results" in result
        assert result["search_type_used"] == "dotNumber"
        assert result["query"] == "299569"
