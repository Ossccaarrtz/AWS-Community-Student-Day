import { useState, useEffect, useCallback, useRef } from "react";

const STORAGE_KEY = "preferred-camera-id";

/**
 * Custom hook — enumera cámaras, maneja permisos, persiste selección.
 *
 * Flujo:
 *  1) getUserMedia({ video: true })          → warm-up para obtener labels
 *  2) enumerateDevices() + filtrar videoinput
 *  3) Auto-seleccionar: localStorage > back/rear/environment > primera
 *  4) Escuchar devicechange para hot-plug USB
 *
 * Limitación iOS Safari: enumerateDevices() puede devolver labels vacíos
 * incluso tras conceder permiso (restricción WebKit). El warm-up mitiga
 * parcialmente este caso.
 *
 * @returns {{
 *   cameras: Array<{deviceId: string, label: string}>,
 *   selectedId: string|null,
 *   setSelectedId: (id: string) => void,
 *   permissionDenied: boolean,
 *   noCameras: boolean,
 *   retryPermission: () => void
 * }}
 */
export default function useCameraDevices() {
    const [cameras, setCameras] = useState([]);
    const [selectedId, setSelectedIdState] = useState(null);
    const [permissionDenied, setPermissionDenied] = useState(false);
    const [noCameras, setNoCameras] = useState(false);

    // Ref para evitar race-conditions con múltiples llamadas
    const initRef = useRef(false);

    // ── Enumerar cámaras (tras obtener permiso) ──────────────────────────
    const enumerate = useCallback(async () => {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter((d) => d.kind === "videoinput");

            if (videoDevices.length === 0) {
                setCameras([]);
                setNoCameras(true);
                setSelectedIdState(null);
                return;
            }

            setNoCameras(false);

            // Asignar labels amigables
            const list = videoDevices.map((d, i) => ({
                deviceId: d.deviceId,
                label: d.label || `Cámara ${i + 1}`,
            }));

            setCameras(list);

            // Decidir cuál seleccionar
            setSelectedIdState((prev) => {
                // 1. Si la cámara previamente seleccionada sigue disponible, mantenerla
                if (prev && list.some((c) => c.deviceId === prev)) return prev;

                // 2. Leer de localStorage
                const stored = localStorage.getItem(STORAGE_KEY);
                if (stored && list.some((c) => c.deviceId === stored)) return stored;

                // 3. Preferir cámara trasera
                const back = list.find((c) =>
                    /back|rear|environment|trasera/i.test(c.label)
                );
                if (back) return back.deviceId;

                // 4. Primera disponible
                return list[0].deviceId;
            });
        } catch (err) {
            console.error("[useCameraDevices] enumerate error:", err);
        }
    }, []);

    // ── Pedir permisos + enumerar ────────────────────────────────────────
    const requestPermissionAndEnumerate = useCallback(async () => {
        setPermissionDenied(false);
        try {
            // Warm-up: abrir y cerrar stream para obtener labels
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            // Liberar la cámara inmediatamente
            stream.getTracks().forEach((t) => t.stop());
            await enumerate();
        } catch (err) {
            console.error("[useCameraDevices] permission error:", err);
            if (
                err.name === "NotAllowedError" ||
                err.name === "PermissionDeniedError"
            ) {
                setPermissionDenied(true);
            } else {
                // Otros errores (NotFoundError, etc.)
                setNoCameras(true);
            }
        }
    }, [enumerate]);

    // ── Setter público — persiste en localStorage ────────────────────────
    const setSelectedId = useCallback((id) => {
        setSelectedIdState(id);
        try {
            localStorage.setItem(STORAGE_KEY, id);
        } catch (_) {
            /* localStorage lleno o no disponible — ignorar */
        }
    }, []);

    // ── Reintentar permisos ──────────────────────────────────────────────
    const retryPermission = useCallback(() => {
        requestPermissionAndEnumerate();
    }, [requestPermissionAndEnumerate]);

    // ── Init + devicechange listener ─────────────────────────────────────
    useEffect(() => {
        if (initRef.current) return;
        initRef.current = true;

        requestPermissionAndEnumerate();

        // Escuchar cambios de dispositivo (USB hot-plug)
        const handleDeviceChange = () => {
            enumerate();
        };

        navigator.mediaDevices?.addEventListener("devicechange", handleDeviceChange);

        return () => {
            navigator.mediaDevices?.removeEventListener(
                "devicechange",
                handleDeviceChange
            );
        };
    }, [requestPermissionAndEnumerate, enumerate]);

    // Persistir en localStorage cuando cambia la selección (via auto-select)
    useEffect(() => {
        if (selectedId) {
            try {
                localStorage.setItem(STORAGE_KEY, selectedId);
            } catch (_) { /* ignore */ }
        }
    }, [selectedId]);

    return {
        cameras,
        selectedId,
        setSelectedId,
        permissionDenied,
        noCameras,
        retryPermission,
    };
}
