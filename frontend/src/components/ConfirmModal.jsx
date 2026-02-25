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

const styles = `
@keyframes cm-spin {
  to { transform: rotate(360deg); }
}
@keyframes cm-fadein {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.cm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(2px);
}
.cm-card {
  background: #1e1e1e;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 36px 32px;
  max-width: 380px;
  width: 90%;
  text-align: center;
  box-shadow: 0 16px 48px rgba(0,0,0,0.5);
  animation: cm-fadein 0.2s ease;
  font-family: Inter, system-ui, Helvetica, Arial, sans-serif;
  color: rgba(255,255,255,0.87);
}
.cm-card--error {
  border-top: 3px solid #c0392b;
}
.cm-card--confirm {
  border-top: 3px solid #3d8a5e;
}
.cm-title {
  margin: 0 0 8px;
  font-size: 1.2rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: rgba(255,255,255,0.92);
}
.cm-subtitle {
  margin: 0;
  font-size: 0.95rem;
  color: rgba(255,255,255,0.5);
  line-height: 1.5;
}
.cm-error-msg {
  margin: 0;
  font-size: 0.95rem;
  color: #e57373;
  line-height: 1.5;
}
.cm-loading-text {
  margin: 16px 0 0;
  font-size: 0.95rem;
  color: rgba(255,255,255,0.5);
}
.cm-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: rgba(255,255,255,0.6);
  border-radius: 50%;
  animation: cm-spin 0.75s linear infinite;
  margin: 0 auto;
}
.cm-btn-row {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 28px;
}
.cm-btn {
  padding: 10px 24px;
  font-size: 0.9rem;
  font-family: inherit;
  font-weight: 500;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
  letter-spacing: 0.01em;
}
.cm-btn:hover  { opacity: 0.85; }
.cm-btn:active { transform: scale(0.97); }
.cm-btn--primary {
  background: #2e7d52;
  color: #fff;
}
.cm-btn--ghost {
  background: rgba(255,255,255,0.07);
  color: rgba(255,255,255,0.65);
}
.cm-btn--ghost-danger {
  background: rgba(192,57,43,0.15);
  color: #e57373;
}
`;

function InjectStyles() {
    if (typeof document !== "undefined" && !document.getElementById("cm-styles")) {
        const tag = document.createElement("style");
        tag.id = "cm-styles";
        tag.textContent = styles;
        document.head.appendChild(tag);
    }
    return null;
}

export default function ConfirmModal({ mode, name, errorMessage, onAccept, onCancel }) {
    InjectStyles();

    if (mode === "loading") {
        return (
            <div className="cm-overlay">
                <div className="cm-card">
                    <div className="cm-spinner" />
                    <p className="cm-loading-text">Procesando…</p>
                </div>
            </div>
        );
    }

    if (mode === "error") {
        return (
            <div className="cm-overlay">
                <div className="cm-card cm-card--error">
                    <p className="cm-title">No se pudo completar</p>
                    <p className="cm-error-msg">{errorMessage}</p>
                    <div className="cm-btn-row">
                        <button className="cm-btn cm-btn--ghost-danger" onClick={onCancel}>
                            Nuevo escaneo
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // mode === "confirm"
    return (
        <div className="cm-overlay">
            <div className="cm-card cm-card--confirm">
                <p className="cm-title">Bienvenido, {name}</p>
                <p className="cm-subtitle">¿Deseas descargar tu gafete en PDF?</p>
                <div className="cm-btn-row">
                    <button className="cm-btn cm-btn--primary" onClick={onAccept}>
                        Descargar gafete
                    </button>
                    <button className="cm-btn cm-btn--ghost" onClick={onCancel}>
                        Cancelar
                    </button>
                </div>
            </div>
        </div>
    );
}
