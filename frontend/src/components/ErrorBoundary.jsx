import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null, errorString: '' };
        console.log('🔵 ErrorBoundary constructor');
    }

    static getDerivedStateFromError(error) {
        console.error('❌ getDerivedStateFromError:', error);
        return { hasError: true, errorString: error?.toString() || 'Unknown error' };
    }

    componentDidCatch(error, errorInfo) {
        console.error('❌ ErrorBoundary caught an error:', error);
        console.error('❌ Error info:', errorInfo);
        console.error('❌ Error stack:', error?.stack);

        this.setState({
            hasError: true,
            error,
            errorInfo,
            errorString: error?.toString() || 'Unknown error'
        });
    }

    render() {
        if (this.state.hasError) {
            const errorMessage = this.state.error?.message || this.state.errorString || 'Error desconocido';
            const errorStack = this.state.error?.stack || '';
            const componentStack = this.state.errorInfo?.componentStack || '';

            return (
                <div style={{
                    padding: 40,
                    backgroundColor: '#1a1a1a',
                    color: '#fff',
                    minHeight: '100vh'
                }}>
                    <h1 style={{ color: '#ff6b6b' }}>⚠️ Error en la aplicación</h1>

                    <h2 style={{ marginTop: 30 }}>Mensaje del error:</h2>
                    <pre style={{
                        backgroundColor: '#242424',
                        padding: 20,
                        borderRadius: 8,
                        overflow: 'auto',
                        fontSize: 14,
                        color: '#ff6b6b',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                    }}>
                        {errorMessage}
                    </pre>

                    {errorStack && (
                        <>
                            <h2 style={{ marginTop: 20 }}>Stack trace:</h2>
                            <pre style={{
                                backgroundColor: '#242424',
                                padding: 20,
                                borderRadius: 8,
                                overflow: 'auto',
                                fontSize: 12,
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word'
                            }}>
                                {errorStack}
                            </pre>
                        </>
                    )}

                    {componentStack && (
                        <>
                            <h2 style={{ marginTop: 20 }}>Component stack:</h2>
                            <pre style={{
                                backgroundColor: '#242424',
                                padding: 20,
                                borderRadius: 8,
                                overflow: 'auto',
                                fontSize: 12,
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word'
                            }}>
                                {componentStack}
                            </pre>
                        </>
                    )}

                    <div style={{ marginTop: 30, fontSize: 14, opacity: 0.8 }}>
                        💡 <strong>Tip:</strong> Abre la consola del navegador (F12) para ver más detalles
                    </div>

                    <button
                        onClick={() => window.location.reload()}
                        style={{
                            marginTop: 20,
                            padding: '10px 20px',
                            backgroundColor: '#646cff',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 8,
                            cursor: 'pointer',
                            fontSize: 16
                        }}
                    >
                        Recargar página
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
