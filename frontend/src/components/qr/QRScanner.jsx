import { useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";

export default function QRScanner({ onResult }) {
    const videoRef = useRef(null);
    const startedRef = useRef(false);

    const [status, setStatus] = useState("Iniciando cámara…");
    const [error, setError] = useState("");

    useEffect(() => {
        console.log('🔵 QRScanner useEffect ejecutándose');

        // En dev, StrictMode monta/desmonta y corre effects 2 veces: evita doble inicio
        if (startedRef.current) {
            console.log('⚠️ QRScanner ya iniciado, evitando doble inicio');
            return;
        }
        startedRef.current = true;

        const reader = new BrowserMultiFormatReader();
        let cancelled = false;
        let controlsRef = null;

        console.log('🔵 Iniciando scanner...');

        (async () => {
            try {
                console.log('🔵 Listando dispositivos de video...');
                const devices = await BrowserMultiFormatReader.listVideoInputDevices();
                console.log('🔵 Dispositivos encontrados:', devices);

                if (!devices || devices.length === 0) {
                    throw new Error("No se detectó ninguna cámara en este dispositivo.");
                }

                setStatus("Escaneando…");
                console.log('🔵 Iniciando decodificación desde cámara...');

                controlsRef = await reader.decodeFromVideoDevice(
                    devices[0].deviceId,
                    videoRef.current,
                    (result, err) => {
                        if (cancelled) return;
                        if (result) {
                            console.log('✅ QR decodificado:', result.getText());
                            onResult?.(result.getText());
                        }
                        if (err && err.name !== 'NotFoundException') {
                            console.error('❌ Error durante decodificación:', err);
                        }
                    }
                );
                console.log('🔵 Scanner activo y escaneando');
            } catch (e) {
                console.error('❌ Error al iniciar scanner:', e);
                if (cancelled) return;
                setError(e?.message || "No se pudo iniciar la cámara.");
                setStatus("");
            }
        })();

        return () => {
            console.log('🔴 QRScanner cleanup ejecutándose');
            cancelled = true;

            // Detener el stream de video
            if (videoRef.current && videoRef.current.srcObject) {
                const stream = videoRef.current.srcObject;
                const tracks = stream.getTracks();
                tracks.forEach(track => {
                    console.log('🔴 Deteniendo track:', track.kind);
                    track.stop();
                });
                videoRef.current.srcObject = null;
            }

            // Si el reader tiene método stopContinuousDecode, úsalo
            if (controlsRef && typeof controlsRef.stop === 'function') {
                console.log('🔴 Llamando controls.stop()');
                controlsRef.stop();
            }
        };
    }, [onResult]);

    return (
        <div style={{ display: "grid", gap: 12, justifyItems: "center" }}>
            {status && <div>{status}</div>}

            {error ? (
                <div style={{
                    padding: 20,
                    border: "1px solid #535353",
                    borderRadius: 12,
                    backgroundColor: '#1a1a1a',
                    maxWidth: 420,
                    width: '100%'
                }}>
                    <b>Scanner no disponible</b>
                    <div style={{ marginTop: 6 }}>{error}</div>
                    <div style={{ marginTop: 12, fontSize: 12, opacity: 0.7 }}>
                        Prueba en tu teléfono abriendo la app por la IP de tu PC (Vite con <code>--host</code>).
                    </div>
                </div>
            ) : (
                <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    style={{
                        width: "100%",
                        maxWidth: 420,
                        borderRadius: 12,
                        border: "2px solid #535353",
                        boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                    }}
                />
            )}
        </div>
    );
}
