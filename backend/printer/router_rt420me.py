from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel

from .config import PrintMode
from .models import PrintRequest, PrinterHint, LabelSpec, LabelContent, LabelField
from .executor import execute_print
from .discovery import discover_all

router = APIRouter(prefix="/printer/test/rt420me", tags=["printer_test_rt420me"])


class TestRequest(BaseModel):
    mode: PrintMode = PrintMode.PREVIEW_ONLY
    ip: Optional[str] = None
    printer_name: Optional[str] = None


def _get_base_spec() -> LabelSpec:
    return LabelSpec(
        width_in=3.0,
        height_in=2.0,
        dpi=203,
        orientation="landscape"
    )


def _run_test(req: TestRequest, spec: LabelSpec, copies: int = 1):
    spec.copies = copies
    
    hint = PrinterHint(
        name=req.printer_name,
        ip=req.ip,
        connection_type="usb" if not req.ip else "tcp"
    )
    
    print_req = PrintRequest(
        action="test_rt420me",
        printer_hint=hint,
        label=spec,
        mode=req.mode
    )
    
    discovery = discover_all(tcp_ip=req.ip)
    
    result = execute_print(print_req, discovery.candidates)
    
    if discovery.warnings:
        result.warnings = discovery.warnings + result.warnings
        
    return result


@router.post("/simple")
def test_simple(req: TestRequest):
    spec = _get_base_spec()
    spec.content = LabelContent(
        title="TEST RT-420ME",
        subtitle="Prueba de texto simple",
    )
    return _run_test(req, spec)


@router.post("/qr")
def test_qr(req: TestRequest):
    spec = _get_base_spec()
    spec.content = LabelContent(
        title="TEST QR",
        subtitle="Validacion de legibilidad",
        qr="{ 'id': 'test-12345', 'mode': 'rt420me' }"
    )
    return _run_test(req, spec)


@router.post("/barcode")
def test_barcode(req: TestRequest):
    spec = _get_base_spec()
    spec.content = LabelContent(
        title="TEST BARCODE",
        subtitle="Code128",
        barcode="RT420ME12345"
    )
    return _run_test(req, spec)


@router.post("/event_label")
def test_event_label(req: TestRequest):
    spec = _get_base_spec()
    spec.content = LabelContent(
        title="Juan Perez",
        subtitle="Director de Innovacion",
        qr="https://ejemplo.com/vcard/juan-perez",
        fields=[
            LabelField(label="Empresa", value="Tech Corp"),
            LabelField(label="Rol", value="Speaker")
        ]
    )
    return _run_test(req, spec)


@router.post("/stress")
def test_stress(req: TestRequest):
    spec = _get_base_spec()
    spec.content = LabelContent(
        title="STRESS TEST",
        subtitle="Imprimiendo 5 copias",
        fields=[
            LabelField(label="Copia", value="1 a 5 de Stress")
        ]
    )
    return _run_test(req, spec, copies=5)
