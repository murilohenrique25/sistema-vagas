import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Box, Typography, Button, Paper, Stack } from '@mui/material';
import ErrorOutlined from '@mui/icons-material/ErrorOutlined';
import WifiOff from '@mui/icons-material/WifiOff';

interface ErrorBoundaryProps {
    children: ReactNode;
    showGoHome?: boolean;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
    isNetworkError: boolean;
}

function isNetworkError(error: Error): boolean {
    const message = error.message.toLowerCase();
    return (
        message.includes('network') ||
        message.includes('fetch') ||
        message.includes('failed to load') ||
        message.includes('timeout') ||
        message.includes('net::') ||
        (error.name === 'TypeError' && message.includes('failed'))
    );
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null, isNetworkError: false };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return {
            hasError: true,
            error,
            isNetworkError: isNetworkError(error),
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null, isNetworkError: false });
    };

    handleGoHome = () => {
        this.setState({ hasError: false, error: null, isNetworkError: false });
        window.location.href = '/';
    };

    render() {
        if (this.state.hasError) {
            const { isNetworkError: networkError } = this.state;
            const { showGoHome = true } = this.props;

            return (
                <Box
                    sx={{
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        minHeight: '50vh',
                        p: { xs: 2, md: 4 },
                    }}
                >
                    <Paper
                        elevation={3}
                        sx={{
                            p: { xs: 3, md: 5 },
                            maxWidth: 480,
                            width: '100%',
                            textAlign: 'center',
                        }}
                    >
                        {networkError ? (
                            <WifiOff sx={{ fontSize: 64, color: 'warning.main', mb: 2 }} />
                        ) : (
                            <ErrorOutlined sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
                        )}

                        <Typography variant="h5" gutterBottom>
                            {networkError ? 'Problema de conexão' : 'Algo deu errado'}
                        </Typography>

                        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                            {networkError
                                ? 'Não foi possível conectar ao servidor. Verifique sua conexão com a internet e tente novamente.'
                                : 'Ocorreu um erro inesperado. Por favor, tente novamente.'}
                        </Typography>

                        <Stack
                            direction={{ xs: 'column', sm: 'row' }}
                            spacing={2}
                            sx={{ justifyContent: 'center' }}
                        >
                            <Button variant="contained" onClick={this.handleRetry}>
                                Tentar novamente
                            </Button>
                            {showGoHome && (
                                <Button variant="outlined" onClick={this.handleGoHome}>
                                    Ir para o início
                                </Button>
                            )}
                        </Stack>
                    </Paper>
                </Box>
            );
        }

        return this.props.children;
    }
}
