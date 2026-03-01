"""Integration tests for watchdog_mcp handler functions.

Tests exercise the actual handler logic with respx intercepting HTTP calls
at the transport layer. No real API calls are made.
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
    str(_repo_root / "plugins" / "searchcarriers-watchdog" / "scripts"),
)

from watchdog_mcp import (  # noqa: E402
    API_BASE,
    _get_alerts,
    _manage_watchlist,
    _monitor_compliance,
)
from conftest import assert_error_payload  # noqa: E402


# ---------------------------------------------------------------------------
# _manage_watchlist
# ---------------------------------------------------------------------------


class TestManageWatchlist:
    """Tests for the manage_watchlist handler."""

    async def test_invalid_action_error(self, fake_api_key):
        """Invalid action returns structured error."""
        result = await _manage_watchlist(
            {"action": "invalid"}, fake_api_key
        )
        assert_error_payload(result, "invalid_action")

    async def test_list_returns_carriers(self, fake_api_key):
        """action=list returns carrier list."""
        watchlist_data = {
            "data": [
                {
                    "id": "w1",
                    "dotNumber": "299569",
                    "carrierName": "J B HUNT TRANSPORT INC",
                }
            ]
        }
        with respx.mock(base_url=API_BASE) as router:
            router.get("/carrier-watch").mock(
                return_value=httpx.Response(200, json=watchlist_data)
            )
            result = await _manage_watchlist(
                {"action": "list"}, fake_api_key
            )

        assert result["action"] == "list"
        assert result["result"] == "listed"
        assert result["watchlist_count"] == 1
        assert len(result["carriers"]) == 1

    async def test_add_missing_dot_error(self, fake_api_key):
        """action=add without dot_number returns error."""
        result = await _manage_watchlist(
            {"action": "add"}, fake_api_key
        )
        assert_error_payload(result, "missing_parameter")

    async def test_add_returns_added(self, fake_api_key):
        """action=add with dot_number returns 'added' result."""
        with respx.mock(base_url=API_BASE) as router:
            router.post("/carrier-watch").mock(
                return_value=httpx.Response(
                    201,
                    json={"carrierName": "J B HUNT TRANSPORT INC", "dotNumber": "299569"},
                )
            )
            # Follow-up GET for count
            router.get("/carrier-watch").mock(
                return_value=httpx.Response(
                    200,
                    json={"data": [{"id": "w1", "dotNumber": "299569"}]},
                )
            )
            result = await _manage_watchlist(
                {"action": "add", "dot_number": "299569"}, fake_api_key
            )

        assert result["action"] == "add"
        assert result["result"] == "added"
        assert result["dot_number"] == "299569"

    async def test_required_keys(self, fake_api_key):
        """List response has all required keys."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/carrier-watch").mock(
                return_value=httpx.Response(200, json={"data": []})
            )
            result = await _manage_watchlist(
                {"action": "list"}, fake_api_key
            )

        for key in ("action", "watchlist_count", "result", "carriers", "_pipeline"):
            assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# _get_alerts
# ---------------------------------------------------------------------------


class TestGetAlerts:
    """Tests for the get_alerts handler."""

    async def test_returns_alert_list(self, fake_api_key):
        """Alerts endpoint returns categorized list."""
        alerts_data = {
            "data": [
                {
                    "alertType": "insurance_change",
                    "dotNumber": "299569",
                    "carrierName": "J B HUNT",
                    "summary": "Insurance policy updated",
                    "timestamp": "2026-02-28T12:00:00Z",
                    "severity": "warning",
                }
            ]
        }
        with respx.mock(base_url=API_BASE) as router:
            router.get("/carrier-watch/alerts").mock(
                return_value=httpx.Response(200, json=alerts_data)
            )
            result = await _get_alerts({}, fake_api_key)

        assert result["alert_count"] == 1
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["_category"] == "insurance_change"
        assert "categories" in result

    async def test_empty_alerts(self, fake_api_key):
        """Empty alerts returns zero count."""
        with respx.mock(base_url=API_BASE) as router:
            router.get("/carrier-watch/alerts").mock(
                return_value=httpx.Response(200, json={"data": []})
            )
            result = await _get_alerts({}, fake_api_key)

        assert result["alert_count"] == 0
        assert result["alerts"] == []


# ---------------------------------------------------------------------------
# _monitor_compliance
# ---------------------------------------------------------------------------


class TestMonitorCompliance:
    """Tests for the monitor_compliance handler."""

    async def test_returns_compliance_structure(
        self, fake_api_key, carrier_jbhunt, authorities_sample, insurances_active
    ):
        """Returns compliance structure with checks list."""
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
            result = await _monitor_compliance(
                {"dot_number": "299569"}, fake_api_key
            )

        for key in ("dot_number", "compliance_status", "checks", "drift_items", "_pipeline"):
            assert key in result, f"Missing key: {key}"

        assert result["compliance_status"] in ("compliant", "drift", "critical")
        assert isinstance(result["checks"], list)
        assert len(result["checks"]) >= 4  # At least 4 checks always run

        # Each check has required fields
        for check in result["checks"]:
            assert "check" in check
            assert "status" in check
            assert check["status"] in ("pass", "fail")
            assert "message" in check
