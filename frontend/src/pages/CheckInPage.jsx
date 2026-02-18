import { useCallback } from "react";
import QRScanner from "../components/qr/QRScanner";

function CheckInPage() {
    console.log('✅ CheckInPage rendering');

    const handleQRResult = useCallback((text) => {
        console.log("✅ QR detectado:", text);
    }, []);

    console.log('✅ CheckInPage about to return JSX');

    return (
        <div style={{
            minHeight: '100vh',
            padding: 40,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 24,
            backgroundColor: '#242424',
            color: '#ffffffde'
        }}>
            <div style={{ maxWidth: 600, width: '100%', textAlign: 'center' }}>
                <h1 style={{ fontSize: '3em', marginBottom: 8 }}>Registro de asistencia</h1>
                <p style={{ opacity: 0.7 }}>Escanea tu código QR para registrar tu entrada</p>
            </div>

            <QRScanner onResult={handleQRResult} />
        </div>
    );
}

export default CheckInPage;
