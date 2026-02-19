import { useState, useRef, useEffect, useCallback } from "react";
import QRScanner from "../components/qr/QRScanner";
import ConfirmModal from "../components/ConfirmModal";
import { downloadPdfFromBase64 } from "../utils/pdfUtils";

const API_URL = import.meta.env.VITE_API_URL;

// ─── Constantes de anti-duplicado ─────────────────────────────────────────────
const COOLDOWN_MS = 2000;

/**
 * Extrae el ticketId del texto crudo del QR.
 * Soporta:
 *   - Texto plano:  "TKT-2026-MKVIV4CK-D9C4FB27"
 *   - URL path:     "https://example.com/checkin/TKT-2026-MKVIV4CK-D9C4FB27"
 *   - URL query:    "https://example.com/?ticketId=TKT-2026-MKVIV4CK-D9C4FB27"
 *   - JSON:         '{"ticketId":"TKT-2026-MKVIV4CK-D9C4FB27"}'
 */
function extractTicketId(raw) {
    const text = String(raw || "").trim();
    if (!text) return null;

    // 1. Intentar parsear como JSON
    try {
        const obj = JSON.parse(text);
        const val = obj?.ticketId || obj?.ticket_id || obj?.id;
        if (val) return String(val).trim();
    } catch (_) { /* no es JSON */ }

    // 2. Intentar parsear como URL
    try {
        const url = new URL(text);
        // Primero: query param ?ticketId=...
        const qp = url.searchParams.get("ticketId") || url.searchParams.get("ticket_id");
        if (qp) return qp.trim();
        // Segundo: último segmento del path
        const segments = url.pathname.split("/").filter(Boolean);
        if (segments.length) return segments[segments.length - 1].trim();
    } catch (_) { /* no es URL válida */ }

    // 3. Texto plano: devolver tal cual
    return text;
}

export default function CheckInPage() {
    // null | "loading" | "confirm" | "error"
    const [modalMode, setModalMode] = useState(null);
    const [modalData, setModalData] = useState(null); // { name, pdfBase64, ticketId }
    const [errorMsg, setErrorMsg] = useState("");

    // ── Refs anti-race-condition ──────────────────────────────────────────────
    /**
     * lockRef: true mientras hay una petición en curso o en cooldown.
     * Evitamos depender de estado (que puede estar desactualizado en el closure
     * del callback de html5-qrcode).
     */
    const lockRef = useRef(false);
    const lastIdRef = useRef(null);
    const lastTimeRef = useRef(0);
    const cooldownTimerRef = useRef(null);
    const abortRef = useRef(null);  // AbortController activo
    const mountedRef = useRef(true);  // evitar setState después de unmount

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            // Cancelar petición en vuelo
            abortRef.current?.abort();
            // Limpiar cooldown timer
            if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
        };
    }, []);

    // ── Helpers ───────────────────────────────────────────────────────────────
    const reset = useCallback(() => {
        if (!mountedRef.current) return;
        abortRef.current?.abort();
        if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
        lockRef.current = false;
        lastIdRef.current = null;
        lastTimeRef.current = 0;
        setModalMode(null);
        setModalData(null);
        setErrorMsg("");
    }, []);

    const showError = useCallback((msg) => {
        if (!mountedRef.current) return;
        lockRef.current = false; // liberar lock para permitir nuevo escaneo tras cerrar
        setErrorMsg(msg);
        setModalMode("error");
    }, []);

    // ── Fetch badge ───────────────────────────────────────────────────────────
    const fetchBadge = useCallback(async (ticketId) => {
        // Crear AbortController para esta petición
        const controller = new AbortController();
        abortRef.current = controller;

        if (mountedRef.current) setModalMode("loading");

        try {
            const response = await fetch(`${API_URL}/badge`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ticketId }),
                signal: controller.signal,
            });

            if (!mountedRef.current) return;

            if (response.ok) {
                const data = await response.json();
                setModalData({ name: data.name, pdfBase64: data.pdfBase64, ticketId });
                setModalMode("confirm");
                // Mantener lockRef=true mientras el modal está abierto; se libera en reset()
            } else {
                let detail = "";
                try {
                    const errBody = await response.json();
                    detail = errBody?.detail ? ` — ${errBody.detail}` : "";
                } catch (_) { /* no-op */ }

                if (response.status === 404) {
                    showError("Ticket no encontrado");
                } else if (response.status === 403) {
                    showError("Sin permisos");
                } else {
                    showError(`Error del servidor (${response.status})${detail}`);
                }
            }
        } catch (err) {
            if (!mountedRef.current) return;
            if (err.name === "AbortError") return; // petición cancelada intencionalmente
            showError("Error de red al contactar el servidor");
        }
    }, [showError]);

    // ── Callback para QRScanner ───────────────────────────────────────────────
    const handleScan = useCallback((decodedText) => {
        // Debug: ver qué contiene el QR exactamente
        console.log("[QR raw]", JSON.stringify(decodedText));

        const ticketId = extractTicketId(decodedText);
        console.log("[QR extracted ticketId]", ticketId);

        if (!ticketId) return;

        const now = Date.now();

        // Anti-duplicado: lock activo (loading/modal/cooldown)
        if (lockRef.current) return;

        // Anti-duplicado: mismo ticketId en ventana de 2 s
        if (ticketId === lastIdRef.current && now - lastTimeRef.current < COOLDOWN_MS) return;

        // Adquirir lock
        lockRef.current = true;
        lastIdRef.current = ticketId;
        lastTimeRef.current = now;

        // Iniciar petición con el ID limpio
        fetchBadge(ticketId);
    }, [fetchBadge]);

    // ── Handlers modal ────────────────────────────────────────────────────────
    const handleAccept = useCallback(() => {
        if (modalData?.pdfBase64 && modalData?.ticketId) {
            downloadPdfFromBase64(
                modalData.pdfBase64,
                `badge_${modalData.ticketId}.pdf`,
                false
            );
        }
        reset();
    }, [modalData, reset]);

    const handleCancel = useCallback(() => {
        reset();
    }, [reset]);

    // ── Render ────────────────────────────────────────────────────────────────
    return (
        <div style={{ padding: "20px", fontFamily: "sans-serif", textAlign: "center" }}>
            <h1>Kiosco de Gafetes</h1>

            <p style={{ color: "#555" }}>
                {modalMode ? "Procesando…" : "Acerca el código QR de tu ticket a la cámara"}
            </p>

            {/* El scanner siempre está montado; onResult se mantiene actualizado por ref */}
            <QRScanner onResult={handleScan} />

            {/* Modal superpuesto */}
            {modalMode && (
                <ConfirmModal
                    mode={modalMode}
                    name={modalData?.name}
                    errorMessage={errorMsg}
                    onAccept={handleAccept}
                    onCancel={handleCancel}
                />
            )}
        </div>
    );
}
