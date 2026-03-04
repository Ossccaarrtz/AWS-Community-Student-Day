/**
 * CameraSelector — dropdown para elegir cámara de escaneo.
 *
 * Props:
 *  - cameras:          Array<{deviceId, label}>
 *  - selectedId:       string | null
 *  - onSelect:         (deviceId: string) => void
 *  - permissionDenied: boolean
 *  - noCameras:        boolean
 *  - onRetry:          () => void
 */

const selectorStyles = `
.cs-wrapper {
  max-width: 400px;
  margin: 0 auto 16px;
  font-family: Inter, system-ui, Helvetica, Arial, sans-serif;
}
.cs-select {
  width: 100%;
  padding: 10px 14px;
  font-size: 0.9rem;
  font-family: inherit;
  color: rgba(255,255,255,0.87);
  background: #1e1e1e;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  outline: none;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23999' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  transition: border-color 0.15s;
}
.cs-select:hover,
.cs-select:focus {
  border-color: rgba(255,255,255,0.3);
}
.cs-label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.8rem;
  color: rgba(255,255,255,0.45);
  text-align: left;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.cs-msg {
  padding: 12px 14px;
  font-size: 0.9rem;
  color: #e57373;
  background: rgba(192,57,43,0.1);
  border: 1px solid rgba(192,57,43,0.25);
  border-radius: 8px;
  text-align: center;
}
.cs-msg--info {
  color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.08);
}
.cs-retry-btn {
  margin-top: 10px;
  padding: 8px 20px;
  font-size: 0.85rem;
  font-family: inherit;
  font-weight: 500;
  color: #fff;
  background: #2e7d52;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
}
.cs-retry-btn:hover { opacity: 0.85; }
.cs-retry-btn:active { transform: scale(0.97); }
`;

function InjectSelectorStyles() {
    if (typeof document !== "undefined" && !document.getElementById("cs-styles")) {
        const tag = document.createElement("style");
        tag.id = "cs-styles";
        tag.textContent = selectorStyles;
        document.head.appendChild(tag);
    }
    return null;
}

export default function CameraSelector({
    cameras,
    selectedId,
    onSelect,
    permissionDenied,
    noCameras,
    onRetry,
}) {
    InjectSelectorStyles();

    // ── Permiso denegado ─────────────────────────────────────────────────
    if (permissionDenied) {
        return (
            <div className="cs-wrapper">
                <div className="cs-msg">
                    Permiso de cámara denegado. Habilita el acceso a la cámara en la
                    configuración de tu navegador.
                    <br />
                    <button className="cs-retry-btn" onClick={onRetry}>
                        Reintentar
                    </button>
                </div>
            </div>
        );
    }

    // ── Sin cámaras ─────────────────────────────────────────────────────
    if (noCameras) {
        return (
            <div className="cs-wrapper">
                <div className="cs-msg cs-msg--info">
                    No se encontraron cámaras disponibles.
                </div>
            </div>
        );
    }

    // ── Cargando (aún no hay cámaras pero no hay error) ──────────────
    if (cameras.length === 0) {
        return (
            <div className="cs-wrapper">
                <div className="cs-msg cs-msg--info">
                    Solicitando acceso a la cámara…
                </div>
            </div>
        );
    }

    // ── Selector normal ──────────────────────────────────────────────────
    return (
        <div className="cs-wrapper">
            <label className="cs-label" htmlFor="camera-select">
                Cámara
            </label>
            <select
                id="camera-select"
                className="cs-select"
                value={selectedId || ""}
                onChange={(e) => onSelect(e.target.value)}
            >
                {cameras.map((cam) => (
                    <option key={cam.deviceId} value={cam.deviceId}>
                        {cam.label}
                    </option>
                ))}
            </select>
        </div>
    );
}
