/**
 * ConfirmModal — modal simple sin librerías externas.
 *
 * Props:
 *  - mode: "confirm" | "error" | "loading"
 *  - name: string (solo en mode="confirm")
 *  - errorMessage: string (solo en mode="error")
 *  - onAccept: () => void  (solo en mode="confirm")
 *  - onCancel: () => void  (confirm + error)
 */
export default function ConfirmModal({ mode, name, errorMessage, onAccept, onCancel }) {
    const overlay = {
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
    };

    const card = {
        backgroundColor: "#fff",
        borderRadius: "12px",
        padding: "32px 28px",
        maxWidth: "360px",
        width: "90%",
        textAlign: "center",
        boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
    };

    const btnRow = {
        display: "flex",
        gap: "12px",
        justifyContent: "center",
        marginTop: "24px",
    };

    const btnPrimary = {
        padding: "10px 28px",
        fontSize: "1rem",
        backgroundColor: "#007bff",
        color: "#fff",
        border: "none",
        borderRadius: "6px",
        cursor: "pointer",
    };

    const btnSecondary = {
        padding: "10px 28px",
        fontSize: "1rem",
        backgroundColor: "#6c757d",
        color: "#fff",
        border: "none",
        borderRadius: "6px",
        cursor: "pointer",
    };

    if (mode === "loading") {
        return (
            <div style={overlay}>
                <div style={card}>
                    <p style={{ fontSize: "1.1rem", margin: 0 }}>⏳ Procesando…</p>
                </div>
            </div>
        );
    }

    if (mode === "error") {
        return (
            <div style={overlay}>
                <div style={card}>
                    <p style={{ fontSize: "1.4rem", marginBottom: "8px" }}>⚠️</p>
                    <p style={{ fontSize: "1.05rem", color: "#c0392b", margin: "0 0 4px" }}>
                        {errorMessage}
                    </p>
                    <div style={btnRow}>
                        <button style={btnSecondary} onClick={onCancel}>
                            Nuevo escaneo
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // mode === "confirm"
    return (
        <div style={overlay}>
            <div style={card}>
                <p style={{ fontSize: "1.2rem", fontWeight: 600, margin: "0 0 8px" }}>
                    👋 Hola, {name}
                </p>
                <p style={{ fontSize: "1rem", color: "#555", margin: 0 }}>
                    ¿Deseas descargar tu gafete en PDF?
                </p>
                <div style={btnRow}>
                    <button style={btnPrimary} onClick={onAccept}>
                        Aceptar
                    </button>
                    <button style={btnSecondary} onClick={onCancel}>
                        Cancelar
                    </button>
                </div>
            </div>
        </div>
    );
}
