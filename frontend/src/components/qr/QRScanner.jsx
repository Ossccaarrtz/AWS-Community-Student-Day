import { useEffect, useRef } from "react";
import { Html5Qrcode } from "html5-qrcode";

// ✅ Fuera del componente — sobrevive los remounts de StrictMode
let globalScanner = null;
let isStarting = false;
let activeDeviceId = null; // deviceId que está corriendo actualmente

/**
 * QRScanner — lector de QR con soporte para selección de cámara.
 *
 * Props:
 *  - onResult:  (text: string) => void  — callback al decodificar un QR
 *  - deviceId:  string | null           — deviceId de la cámara a usar.
 *              Si es null/undefined, usa facingMode "environment" como fallback.
 *
 * Cuando deviceId cambia, el scanner se detiene y reinicia con la nueva cámara
 * (hot-swap).
 */
export default function QRScanner({ onResult, deviceId }) {
    const onResultRef = useRef(onResult);
    onResultRef.current = onResult; // siempre actualizado sin re-trigger del effect

    useEffect(() => {
        // Si no hay deviceId aún (hook still loading), no iniciar
        if (!deviceId) return;

        // Si ya corre con el mismo deviceId, no hacer nada
        if (globalScanner && activeDeviceId === deviceId && !isStarting) return;

        // ── Helper: iniciar scanner con el deviceId dado ─────────────────
        const startScanner = async () => {
            // Evitar inicios paralelos
            if (isStarting) return;
            isStarting = true;

            // Si hay un scanner activo, detenerlo primero (hot-swap)
            if (globalScanner) {
                try {
                    await globalScanner.stop();
                } catch (_) { /* ya detenido */ }
                globalScanner = null;
                activeDeviceId = null;
            }

            const scanner = new Html5Qrcode("qr-reader");
            const config = { fps: 10, qrbox: { width: 250, height: 250 } };
            const onSuccess = (text) => onResultRef.current?.(text);
            const onFailure = () => { };

            try {
                // Intentar con exact deviceId
                await scanner.start(
                    { deviceId: { exact: deviceId } },
                    config,
                    onSuccess,
                    onFailure
                );
                globalScanner = scanner;
                activeDeviceId = deviceId;
            } catch (exactErr) {
                // Fallback: sin 'exact' (algunos navegadores no lo soportan)
                try {
                    await scanner.start(
                        { deviceId: deviceId },
                        config,
                        onSuccess,
                        onFailure
                    );
                    globalScanner = scanner;
                    activeDeviceId = deviceId;
                } catch (fallbackErr) {
                    console.error("[QRScanner] No se pudo iniciar la cámara:", fallbackErr);
                }
            }

            isStarting = false;
        };

        startScanner();

        return () => {
            // Cleanup — solo cuando el componente se desmonta de verdad
            if (globalScanner) {
                globalScanner
                    .stop()
                    .catch(() => { })
                    .finally(() => {
                        globalScanner = null;
                        activeDeviceId = null;
                        isStarting = false;
                    });
            }
        };
    }, [deviceId]);

    return (
        <div
            id="qr-reader"
            style={{ width: "100%", maxWidth: 400, margin: "0 auto" }}
        />
    );
}