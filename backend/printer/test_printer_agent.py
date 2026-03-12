"""
Test suite for the MCP Label Printer Agent.

Covers: discovery (simulation), rendering, preview, dry-run, logging.
Run:  python -m pytest printer/test_printer_agent.py -v
"""

from __future__ import annotations

import base64
import io
import json
import os
import tempfile

import pytest
from PIL import Image

from printer.config import ConnectionType, ErrorClass, PrintMode, DEFAULT_DPI
from printer.models import (
    DiscoverResult,
    LabelContent,
    LabelField,
    LabelSpec,
    PrinterCandidate,
    PrinterHint,
    PrintRequest,
    PrintResult,
)
from printer.discovery import discover_all, _keyword_score, _guess_vendor
from printer.renderer import render_label, generate_preview_base64, generate_raster_payload
from printer.executor import execute_print, _next_job_id
from printer.logger import log_job, read_recent_jobs, JOB_LOG_FILE


# ── Helpers ───────────────────────────────────────────────────────

def _sample_label() -> LabelSpec:
    return LabelSpec(
        width_in=3.0,
        height_in=2.0,
        dpi=203,
        copies=1,
        orientation="landscape",
        content=LabelContent(
            title="Carlos Méndez",
            subtitle="Empresa ABC",
            qr="https://ejemplo.com/checkin/123",
            barcode=None,
            fields=[
                LabelField(label="Cargo", value="Invitado"),
                LabelField(label="Folio", value="A-102"),
            ],
        ),
    )


def _sample_request(mode: PrintMode = PrintMode.PREVIEW_ONLY) -> PrintRequest:
    return PrintRequest(
        action="print_label",
        printer_hint=PrinterHint(),
        label=_sample_label(),
        mode=mode,
    )


# ── Discovery tests ──────────────────────────────────────────────


class TestDiscovery:
    def test_keyword_score_ribetec(self):
        assert _keyword_score("Ribetec XT-100 Label Printer") > 0

    def test_keyword_score_empty(self):
        assert _keyword_score("Some random text") == 0

    def test_guess_vendor_ribetec(self):
        assert _guess_vendor("Ribetec Printer LX") == "Ribetec"

    def test_guess_vendor_zebra(self):
        assert _guess_vendor("Zebra ZD420") == "Zebra"

    def test_guess_vendor_unknown(self):
        assert _guess_vendor("FooBar XYZ") == "unknown"

    def test_discover_all_returns_result(self):
        result = discover_all()
        assert isinstance(result, DiscoverResult)
        assert result.success is True
        # On machines without printers, we get 0 candidates + warning
        if len(result.candidates) == 0:
            assert any("simulación" in w.lower() or "simulation" in w.lower()
                       for w in result.warnings)

    def test_discover_all_with_unreachable_tcp(self):
        result = discover_all(tcp_ip="192.0.2.99", tcp_port=9100)
        assert isinstance(result, DiscoverResult)
        # Non-routable IP should produce a warning
        assert any("192.0.2.99" in w for w in result.warnings)


# ── Renderer tests ────────────────────────────────────────────────


class TestRenderer:
    def test_render_basic_label(self):
        label = _sample_label()
        result = render_label(label)
        assert result.image is not None
        assert isinstance(result.image, Image.Image)
        # Check dimensions (3 in × 203 dpi = 609 px, 2 in × 203 = 406 px)
        assert result.image.size == (609, 406)

    def test_render_with_default_dpi_warning(self):
        label = _sample_label()
        label.dpi = None
        result = render_label(label)
        assert any("dpi" in w.lower() for w in result.warnings)

    def test_render_with_qr(self):
        label = _sample_label()
        label.content.qr = "https://test.com/qr"
        result = render_label(label)
        assert result.image is not None

    def test_render_with_barcode(self):
        label = _sample_label()
        label.content.barcode = "1234567890"
        label.content.qr = None
        result = render_label(label)
        assert result.image is not None

    def test_render_overflow_warning(self):
        label = _sample_label()
        label.content.fields = [
            LabelField(label=f"Field{i}", value=f"Value {i}")
            for i in range(20)
        ]
        result = render_label(label)
        assert any("recortado" in w.lower() or "excede" in w.lower()
                    for w in result.warnings)

    def test_generate_preview_base64(self):
        label = _sample_label()
        result = render_label(label)
        b64 = generate_preview_base64(result.image)
        assert isinstance(b64, str)
        # Verify it's valid base64 that decodes to PNG
        data = base64.b64decode(b64)
        img = Image.open(io.BytesIO(data))
        assert img.format == "PNG"

    def test_generate_raster_payload(self):
        label = _sample_label()
        result = render_label(label)
        payload = generate_raster_payload(result.image)
        assert isinstance(payload, bytes)
        assert len(payload) > 0
        # Expected size: ceil(609/8) * 406 = 77 * 406 = 31262
        import math
        expected = math.ceil(609 / 8) * 406
        assert len(payload) == expected


# ── Executor tests ────────────────────────────────────────────────


class TestExecutor:
    def test_job_id_generation(self):
        id1 = _next_job_id()
        id2 = _next_job_id()
        assert id1.startswith("job_")
        assert id1 != id2

    def test_preview_only(self):
        req = _sample_request(PrintMode.PREVIEW_ONLY)
        result = execute_print(req, [])
        assert isinstance(result, PrintResult)
        assert result.success is True
        assert result.preview_generated is True
        assert result.preview_base64 is not None
        assert result.action == "preview_label"

    def test_dry_run_saves_file(self):
        req = _sample_request(PrintMode.DRY_RUN)
        result = execute_print(req, [])
        assert result.success is True
        assert result.payload_file is not None
        assert os.path.exists(result.payload_file)
        # Cleanup
        os.unlink(result.payload_file)

    def test_dry_run_with_candidates(self):
        candidates = [
            PrinterCandidate(
                name="Test Printer",
                connection_type=ConnectionType.SYSTEM_QUEUE,
                confidence_score=0.8,
                can_print_via_system_driver=True,
            )
        ]
        req = _sample_request(PrintMode.DRY_RUN)
        result = execute_print(req, candidates)
        assert result.success is True
        assert result.selected_printer is not None
        assert result.selected_printer.name == "Test Printer"
        # Cleanup
        if result.payload_file and os.path.exists(result.payload_file):
            os.unlink(result.payload_file)

    def test_simulation_when_no_printers(self):
        req = _sample_request(PrintMode.ACTUAL_PRINT)
        result = execute_print(req, [])
        assert result.success is True
        assert result.print_strategy.method == "simulation"
        assert result.payload_file is not None
        # Cleanup
        if result.payload_file and os.path.exists(result.payload_file):
            os.unlink(result.payload_file)


# ── Logger tests ──────────────────────────────────────────────────


class TestLogger:
    def test_log_job_writes_json(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test_jobs.log"
        monkeypatch.setattr("printer.logger.JOB_LOG_FILE", str(log_file))
        monkeypatch.setattr("printer.config.JOB_LOG_FILE", str(log_file))

        label = _sample_label()
        log_job(
            job_id="test_001",
            action="print_label",
            selected_printer="Test Printer",
            chosen_method="system_driver",
            label=label,
            transport="system_queue",
            result="ok",
            warnings=["test warning"],
        )

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8").strip()
        entry = json.loads(content)
        assert entry["job_id"] == "test_001"
        assert entry["result"] == "ok"
        assert "test warning" in entry["warnings"]

    def test_read_recent_jobs(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test_jobs.log"
        monkeypatch.setattr("printer.logger.JOB_LOG_FILE", str(log_file))

        # Write 3 entries
        for i in range(3):
            label = _sample_label()
            log_job(f"job_{i}", "test", None, "sim", label, "none", "ok")

        monkeypatch.setattr("printer.logger.JOB_LOG_FILE", str(log_file))
        jobs = read_recent_jobs(count=2)
        assert len(jobs) == 2
        assert jobs[-1]["job_id"] == "job_2"


# ── Integration test ──────────────────────────────────────────────


class TestIntegration:
    def test_full_flow_discover_render_dry_run(self):
        """End-to-end: discover → render → dry_run → save_job."""
        # 1. Discover
        discovery = discover_all()
        assert discovery.success

        # 2. Render preview
        label = _sample_label()
        render_result = render_label(label)
        assert render_result.image is not None

        # 3. Dry run
        req = _sample_request(PrintMode.DRY_RUN)
        result = execute_print(req, discovery.candidates)
        assert result.success
        assert result.job_id.startswith("job_")
        assert result.preview_generated

        # Cleanup
        if result.payload_file and os.path.exists(result.payload_file):
            os.unlink(result.payload_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
