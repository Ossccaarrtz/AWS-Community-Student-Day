import { useEffect, useRef } from "react";
import { Html5Qrcode } from "html5-qrcode";

// ✅ Fuera del componente — sobrevive los remounts de StrictMode
let globalScanner = null;
let isStarting = false;

export default function QRScanner({ onResult }) {
    const onResultRef = useRef(onResult);
    onResultRef.current = onResult; // siempre actualizado sin re-trigger del effect

    useEffect(() => {
        // Si ya hay un scanner activo o está iniciando, no hacer nada
        if (globalScanner || isStarting) return;
        isStarting = true;

        const scanner = new Html5Qrcode("qr-reader");

        Html5Qrcode.getCameras()
            .then((devices) => {
                if (!devices.length) throw new Error("No se encontró cámara");

                const cam =
  // 1) Preferir integrada
  devices.find(d => /integrated|hd webcam|webcam|camera/i.test(d.label)) ||
  // 2) Si existiera una trasera (en laptop casi nunca)
  devices.find(d => /back|rear|environment/i.test(d.label)) ||
  // 3) Fallback: la primera (no la última)
  devices[0];

                return scanner.start(
                    cam.id,
                    { fps: 10, qrbox: { width: 250, height: 250 } },
                    (text) => onResultRef.current?.(text),
                    () => { }
                );
            })
            .then(() => {
                globalScanner = scanner;
                isStarting = false;
            })
            .catch((err) => {
                console.error("QR Scanner error:", err);
                isStarting = false;
            });

        return () => {
            // Cleanup real — solo cuando navegas fuera, no en StrictMode remount
            if (globalScanner) {
                globalScanner
                    .stop()
                    .catch(() => { })
                    .finally(() => {
                        globalScanner = null;
                        isStarting = false;
                    });
            }
        };
    }, []); // ✅ sin dependencias — el ref mantiene onResult actualizado

    return (
        <div
            id="qr-reader"
            style={{ width: "100%", maxWidth: 400, margin: "0 auto" }}
        />
    );
}