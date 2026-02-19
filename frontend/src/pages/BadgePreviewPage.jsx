import { useState, useRef, useEffect } from "react";
import QRScanner from "../components/qr/QRScanner";
import { downloadPdfFromBase64 } from "../utils/pdfUtils";

export default function BadgePreviewPage() {
    const [scannedTicketId, setScannedTicketId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [cooldown, setCooldown] = useState(false);

    // Referencia para manejar el anti-duplicado in mediato sin depender del re-render
    const lastScannedTime = useRef(0);
    const lastScannedId = useRef(null);

    const API_URL = import.meta.env.VITE_API_URL;

    console.log("Render BadgePreviewPage. State:", { scannedTicketId, loading, error, cooldown });

    const handleScan = (decodedText) => {
        const now = Date.now();
        const text = String(decodedText).trim();

        console.log("Scanner raw:", decodedText, "Processed:", text);

        if (!text) return;

        // 1. Anti-duplicado (ref)
        if (
            text === lastScannedId.current &&
            now - lastScannedTime.current < 2000
        ) {
            console.log("Skipping duplicate:", text);
            return;
        }

        // 2. Si estamos descargando, ignorar
        if (loading) {
            console.log("Skipping due to loading state");
            return;
        }

        // Force update if different
        setScannedTicketId((prev) => {
            if (prev !== text) {
                console.log("Updating state to:", text);
                lastScannedId.current = text;
                lastScannedTime.current = now;
                return text;
            }
            return prev;
        });
        setError(null);
    };

    const handleGetBadge = async () => {
        if (!scannedTicketId) return;

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_URL}/badge`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ ticketId: scannedTicketId }),
            });

            if (response.ok) {
                const data = await response.json();
                if (data.pdfBase64) {
                    downloadPdfFromBase64(
                        data.pdfBase64,
                        `badge_${scannedTicketId}.pdf`,
                        true
                    );
                } else {
                    setError("Respuesta inválida del servidor (sin PDF)");
                }
            } else if (response.status === 404) {
                setError("Ticket ID no encontrado");
            } else if (response.status === 403) {
                setError("Sin permisos para ver este gafete");
            } else {
                setError(`Error del servidor: ${response.status}`);
            }
        } catch (err) {
            console.error(err);
            setError("Error de conexión al obtener el gafete");
        } finally {
            setLoading(false);
        }
    };

    const handleReset = () => {
        setScannedTicketId(null);
        setError(null);
        setLoading(false);
        lastScannedId.current = null;
    };

    return (
        <div style={{ padding: "20px", fontFamily: "sans-serif", textAlign: "center" }}>
            <h1>Kiosco de Gafetes</h1>

            {/* Si NO hay ticket escaneado, mostramos el scanner */}
            {!scannedTicketId ? (
                <div>
                    <p>Por favor, escanea tu código QR</p>
                    <QRScanner onResult={handleScan} />
                </div>
            ) : (
                /* Si YA hay ticket, mostramos la vista previa/acciones */
                <div style={{ marginTop: "20px" }}>
                    <div style={{
                        border: "2px solid #ccc",
                        padding: "20px",
                        borderRadius: "8px",
                        display: "inline-block",
                        backgroundColor: "#f9f9f9"
                    }}>
                        <h2>QR Leído</h2>
                        <p style={{ fontSize: "1.2rem", fontWeight: "bold" }}>
                            {scannedTicketId}
                        </p>

                        {error && (
                            <div style={{ color: "red", marginBottom: "15px" }}>
                                ⚠️ {error}
                            </div>
                        )}

                        <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
                            <button
                                onClick={handleGetBadge}
                                disabled={loading}
                                style={{
                                    padding: "10px 20px",
                                    fontSize: "1rem",
                                    backgroundColor: loading ? "#ccc" : "#007bff",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: loading ? "not-allowed" : "pointer"
                                }}
                            >
                                {loading ? "Procesando..." : "Ver/Descargar Gafete"}
                            </button>

                            <button
                                onClick={handleReset}
                                disabled={loading}
                                style={{
                                    padding: "10px 20px",
                                    fontSize: "1rem",
                                    backgroundColor: "#6c757d",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: loading ? "not-allowed" : "pointer"
                                }}
                            >
                                Escanear otro
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
