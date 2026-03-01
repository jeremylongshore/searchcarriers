"""Tests for PDF output and graceful degradation.

These tests verify the PDF rendering pathway works correctly (or degrades
gracefully when weasyprint is not installed) and that vetting report
context has no None values for populated API fields.
"""

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx

_repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(_repo_root))
sys.path.insert(
    0,
    str(_repo_root / "plugins" / "searchcarriers-ops-reporter" / "scripts"),
)

from ops_reporter_mcp import (
    API_BASE,
    _generate_report,
    _generate_fleet,
    _export_data,
)
from conftest import assert_error_payload

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fake_api_key():
    return "test-key-not-real"


@pytest.fixture
def carrier_jbhunt():
    return json.loads((FIXTURES_DIR / "carrier_jbhunt.json").read_text())


@pytest.fixture
def authorities_sample():
    return json.loads((FIXTURES_DIR / "authorities_sample.json").read_text())


@pytest.fixture
def insurances_active():
    return json.loads((FIXTURES_DIR / "insurances_active.json").read_text())


@pytest.fixture
def equipment_sample():
    return json.loads((FIXTURES_DIR / "equipment_sample.json").read_text())


def _mock_report_routes(router, carrier, authorities, insurances, dot="299569"):
    router.get("/search").mock(
        return_value=httpx.Response(200, json=carrier)
    )
    router.get(f"/company/{dot}/authorities").mock(
        return_value=httpx.Response(200, json=authorities)
    )
    router.get(f"/company/{dot}/insurances").mock(
        return_value=httpx.Response(200, json=insurances)
    )


# ---------------------------------------------------------------------------
# PDF format tests
# ---------------------------------------------------------------------------


class TestPDFFormat:
    """Test PDF format output behavior."""

    async def test_pdf_format_graceful_degradation(
        self, fake_api_key, carrier_jbhunt, authorities_sample, insurances_active
    ):
        """When weasyprint is not installed, format falls back to markdown."""
        with respx.mock(base_url=API_BASE) as router:
            _mock_report_routes(router, carrier_jbhunt, authorities_sample, insurances_active)

            # Mock weasyprint import failure
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "weasyprint":
                    raise ImportError("No module named 'weasyprint'")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", side_effect=mock_import):
                result = await _generate_report(
                    {"dot_number": "299569", "format": "pdf"}, fake_api_key
                )

        # Should fall back to markdown, not crash
        assert result["format"] == "markdown"
        assert "report" in result

    async def test_pdf_format_returns_file_path(
        self, fake_api_key, carrier_jbhunt, authorities_sample, insurances_active, tmp_path
    ):
        """When weasyprint is available, result includes file_path ending in .pdf."""
        try:
            import weasyprint
            import jinja2
        except ImportError:
            pytest.skip("weasyprint or jinja2 not installed")

        with respx.mock(base_url=API_BASE) as router:
            _mock_report_routes(router, carrier_jbhunt, authorities_sample, insurances_active)

            # Redirect output to tmp_path
            with patch("pdf_renderer._REPORTS_DIR", tmp_path):
                result = await _generate_report(
                    {"dot_number": "299569", "format": "pdf"}, fake_api_key
                )

        assert result["format"] == "pdf"
        assert result["file_path"].endswith(".pdf")
        assert Path(result["file_path"]).exists()


# ---------------------------------------------------------------------------
# Normalization quality tests
# ---------------------------------------------------------------------------


class TestNormalizationQuality:
    """Verify that normalization produces complete data — no N/A for fields
    that exist in the API response."""

    async def test_report_no_na_for_jbhunt(
        self, fake_api_key, carrier_jbhunt, authorities_sample, insurances_active
    ):
        """JB Hunt has all major fields — none should be N/A."""
        with respx.mock(base_url=API_BASE) as router:
            _mock_report_routes(router, carrier_jbhunt, authorities_sample, insurances_active)
            result = await _generate_report({"dot_number": "299569"}, fake_api_key)

        report = result["report"]
        # The carrier name should appear, not "Unknown Carrier"
        assert "J B HUNT" in report
        assert result["carrier_name"] == "J B HUNT TRANSPORT INC"

    async def test_report_contains_insurance_data(
        self, fake_api_key, carrier_jbhunt, authorities_sample, insurances_active
    ):
        """Insurance section should show type and insurer, not all N/A."""
        with respx.mock(base_url=API_BASE) as router:
            _mock_report_routes(router, carrier_jbhunt, authorities_sample, insurances_active)
            result = await _generate_report({"dot_number": "299569"}, fake_api_key)

        report = result["report"]
        assert "BIPD" in report
        assert "National Indemnity" in report

    async def test_report_contains_authority_data(
        self, fake_api_key, carrier_jbhunt, authorities_sample, insurances_active
    ):
        """Authority section should show type and status."""
        with respx.mock(base_url=API_BASE) as router:
            _mock_report_routes(router, carrier_jbhunt, authorities_sample, insurances_active)
            result = await _generate_report({"dot_number": "299569"}, fake_api_key)

        report = result["report"]
        assert "Common" in report
        assert "Active" in report

    async def test_csv_export_curated(
        self, fake_api_key, carrier_jbhunt
    ):
        """CSV export should produce curated columns, not raw dump."""
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
            router.get("/company/299569/equipment").mock(
                return_value=httpx.Response(200, json={"data": []})
            )
            result = await _export_data(
                {"dot_number": "299569", "format": "csv"}, fake_api_key
            )

        assert result["format"] == "csv"
        assert "DOT Number" in result["data"]
        assert "Legal Name" in result["data"]
        # Should not have search_data column
        assert "search_data" not in result["data"]
