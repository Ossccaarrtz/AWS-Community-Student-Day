import requests
import json
import sys
import time
from typing import Optional

API_BASE = "http://localhost:8000"

def get_printers():
    print("Buscando impresoras disponibles...")
    try:
        res = requests.post(f"{API_BASE}/printer/discover", json={}, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("candidates", [])
    except Exception as e:
        print(f"Error detectando impresoras: {e}")
        return []

def select_printer(printers) -> Optional[dict]:
    if not printers:
        print("No se encontraron impresoras.")
        return None
    
    print("\nImpresoras disponibles:")
    for i, p in enumerate(printers):
        print(f"[{i+1}] {p['name']} (Tipo: {p['connection_type']}, Detalles: {p['transport_details']})")
    
    while True:
        try:
            choice = input("\nSeleccione la impresora (0 para cancelar): ")
            idx = int(choice)
            if idx == 0: return None
            if 1 <= idx <= len(printers):
                return printers[idx-1]
            print("Seleccion no valida.")
        except ValueError:
            print("Ingrese un numero valido.")

def run_test(endpoint: str, name: str, printer: dict, mode: str = "print"):
    print(f"\n--- Ejecutando {name} ---")
    payload = {
        "mode": mode,
        "printer_name": printer["name"],
        "ip": None
    }
    
    if printer["connection_type"] == "tcp":
        # Extract IP from transport_details roughly assuming "ip=XXX"
        try:
            import re
            m = re.search(r"ip=([^\s,]+)", printer["transport_details"])
            if m: payload["ip"] = m.group(1)
        except Exception:
            pass
            
    try:
        res = requests.post(f"{API_BASE}/printer/test/rt420me/{endpoint}", json=payload, timeout=15)
        res.raise_for_status()
        data = res.json()
        print(f"Resultado: {'EXITO' if data['success'] else 'FALLO'}")
        
        diag = data.get("diagnostics", {})
        print(f"Job ID: {data.get('job_id')}")
        if data.get("payload_file"): print(f"Payload: {data['payload_file']}")
        if diag.get("metadata_file"): print(f"Metadata: {diag['metadata_file']}")
        
        if not data["success"]:
            print(f"Error: {data.get('error_message')}")
            
        if data.get("warnings"):
            print("Advertencias:")
            for w in data["warnings"]: print(f" - {w}")
            
    except Exception as e:
        print(f"Error de conexion con el backend: {e}")

def main():
    print("==================================================")
    print(" SUITE DE VALIDACION - RIBETEC RT-420ME")
    print("==================================================")
    
    try:
        requests.get(f"{API_BASE}/health", timeout=3)
    except Exception:
        print("ERROR: El backend no esta corriendo interactivo.")
        print("Asegurese de iniciar el backend en http://localhost:8000")
        sys.exit(1)
        
    print("\nModo de prueba:")
    print("[1] PREVIEW SOLO (no genera archivos .prn)")
    print("[2] DRY RUN (genera .prn y valida pipeline sin imprimir)")
    print("[3] IMPRESION REAL (envia a la impresora física)")
    
    mode_map = {"1": "preview_only", "2": "dry_run", "3": "actual_print"}
    
    choice = input("Seleccione el modo [1-3]: ")
    mode = mode_map.get(choice, "preview_only")
    print(f"Modo seleccionado: {mode}")

    printers = get_printers()
    selected = select_printer(printers)
    
    if not selected:
        print("Abortando pruebas.")
        sys.exit(0)
        
    print(f"\nImpresora seleccionada: {selected['name']}")
    input("Presione ENTER para comenzar las pruebas...")
    
    tests = [
        ("simple", "TEST 1 - Texto Simple"),
        ("qr", "TEST 2 - Codigo QR"),
        ("barcode", "TEST 3 - Codigo de Barras"),
        ("event_label", "TEST 4 - Gafete de Evento Completo"),
    ]
    
    for ep, name in tests:
        run_test(ep, name, selected, mode)
        time.sleep(1) # breve pausa entre impresiones
    
    ans = input("\n¿Ejecutar TEST 5 - Stress test (5 etiquetas seguidas)? (s/N): ")
    if ans.lower() == 's':
        run_test("stress", "TEST 5 - Stress Test", selected, mode)

    print("\n--------------------------------------------------")
    print(" PRUEBAS FINALIZADAS")
    print("--------------------------------------------------")
    print("Por favor revise la consola por si hubo advertencias.")
    print("Los archivos de diagnostico (.prn, .png, .json) se generaron en la carpeta 'printer_jobs/'")
    print("del backend. Consulte el Test Guide para mas detalles de como interpretarlos y reportar.")
    print("--------------------------------------------------")


if __name__ == "__main__":
    main()
