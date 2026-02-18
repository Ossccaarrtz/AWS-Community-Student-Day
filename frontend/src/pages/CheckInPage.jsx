import { useCallback, useRef, useState } from "react";
import QRScanner from "../components/qr/QRScanner";

export default function CheckInPage() {
    const [lastId, setLastId] = useState(null);
    const [status, setStatus] = useState("Esperando QR…");
    const [isProcessing, setIsProcessing] = useState(false);

    const resetTimerRef = useRef(null);

    const playBeep = () => {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;

            const ctx = new AudioContext();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.type = "sine";
            osc.frequency.value = 1000;
            gain.gain.setValueAtTime(0.12, ctx.currentTime);

            osc.start();
            osc.stop(ctx.currentTime + 0.12);

            // cerrar contexto para no acumular recursos
            setTimeout(() => {
                try {
                    ctx.close();
                } catch { }
            }, 250);
        } catch {
            // si el navegador bloquea audio, no pasa nada
        }
    };

    const scheduleStatusReset = () => {
        if (resetTimerRef.current) clearTimeout(resetTimerRef.current);
        resetTimerRef.current = setTimeout(() => {
            setStatus("Esperando siguiente QR…");
            setIsProcessing(false);
        }, 1500);
    };

    const handleQRResult = useCallback((text) => {
        // Evita que se procese más de un QR al mismo tiempo
        if (isProcessing) return;

        const attendeeId = (text ?? "").trim();
        if (!attendeeId) return;

        setIsProcessing(true);
        setLastId(attendeeId);
        setStatus("✅ QR leído correctamente");

        // feedback
        playBeep();
        if (navigator.vibrate) navigator.vibrate(120);

        console.log("✅ attendeeId:", attendeeId);

        // Próximo paso: check-in en backend
        // (de momento solo simulamos)
        // await checkIn(attendeeId);

        scheduleStatusReset();
    }, [isProcessing]);

    return (
        <div
            style={{
                minHeight: "100vh",
                padding: 40,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 24,
                backgroundColor: "#242424",
                color: "#ffffffde",
                fontFamily: "Inter, system-ui, Avenir, Helvetica, Arial, sans-serif",
            }}
        >
            <div style={{ maxWidth: 680, width: "100%", textAlign: "center" }}>
                <h1 style={{ fontSize: "2.5rem", marginBottom: 10, fontWeight: 700 }}>
                    Registro de asistencia
                </h1>

                <div
                    style={{
                        fontSize: "1.15rem",
                        color: status.includes("✅")
                            ? "#4ade80"
                            : status.includes("❌")
                                ? "#ff6b6b"
                                : "#aaa",
                        fontWeight: 500,
                        minHeight: "1.5em",
                    }}
                >
                    {status}
                </div>
            </div>

            {/* Importante: si estás "procesando", puedes mostrar overlay o simplemente ignorar lecturas */}
            <div style={{ width: "100%", display: "grid", justifyItems: "center" }}>
                <QRScanner onResult={handleQRResult} cooldownMs={1200} />

                {isProcessing && (
                    <div style={{ marginTop: 10, fontSize: 12, opacity: 0.7 }}>
                        Procesando…
                    </div>
                )}
            </div>

            {lastId && (
                <div
                    style={{
                        marginTop: 8,
                        padding: "16px 24px",
                        backgroundColor: "#1a1a1a",
                        borderRadius: 12,
                        border: "1px solid #555",
                        textAlign: "center",
                        maxWidth: 420,
                        width: "100%",
                    }}
                >
                    <div style={{ fontSize: "0.9rem", color: "#aaa", marginBottom: 4 }}>
                        Último ID leído
                    </div>
                    <div style={{ fontSize: "1.5rem", fontFamily: "monospace", fontWeight: "bold" }}>
                        {lastId}
                    </div>
                </div>
            )}
        </div>
    );
}
