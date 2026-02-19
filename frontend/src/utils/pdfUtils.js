/**
 * Convierte un string Base64 a Blob y:
 * - Si openInNewTab=true: intenta abrir el PDF en una nueva pestaña (si es bloqueado, hace descarga).
 * - Si openInNewTab=false: fuerza descarga directa.
 *
 * Nota Safari/iOS: el atributo download puede no comportarse igual; por eso el fallback abre si se puede.
 *
 * @param {string} pdfBase64 - Contenido del PDF en Base64 (SIN prefijo data:application/pdf;base64,).
 * @param {string} filename - Nombre del archivo a descargar.
 * @param {boolean} openInNewTab - Si true, intenta abrir primero; si falla, descarga.
 */
export const downloadPdfFromBase64 = (pdfBase64, filename = "badge.pdf", openInNewTab = true) => {
    try {
        if (!pdfBase64 || typeof pdfBase64 !== "string") {
            throw new Error("pdfBase64 inválido o vacío");
        }

        // Base64 -> Uint8Array
        const byteCharacters = atob(pdfBase64);
        const byteArray = new Uint8Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteArray[i] = byteCharacters.charCodeAt(i);
        }

        // Blob PDF
        const blob = new Blob([byteArray], { type: "application/pdf" });
        const blobUrl = URL.createObjectURL(blob);

        // Helper: descarga
        const forceDownload = () => {
            const link = document.createElement("a");
            link.href = blobUrl;
            link.download = filename || "download.pdf";
            link.rel = "noopener"; // seguridad extra
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        };

        if (openInNewTab) {
            // Intento de abrir (puede ser bloqueado por popup blocker)
            const win = window.open(blobUrl, "_blank", "noopener,noreferrer");

            // Si el navegador bloqueó el popup, win será null/undefined
            if (!win) {
                forceDownload();
            }
        } else {
            forceDownload();
        }

        // Cleanup: darle tiempo al navegador para abrir/descargar antes de revocar
        setTimeout(() => {
            URL.revokeObjectURL(blobUrl);
        }, 2000);

    } catch (error) {
        console.error("Error downloading/opening PDF:", error);
    }
};
