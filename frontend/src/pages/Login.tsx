import { useState, type FormEvent } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
    Box,
    Typography,
    Container,
    TextField,
    Button,
    Alert,
    Divider,
    Link,
    Paper,
    Stack,
} from '@mui/material';
import { Google as GoogleIcon, LinkedIn as LinkedInIcon } from '@mui/icons-material';
import { useAuthStore } from '../stores/authStore';
import { login, oauthRedirect } from '../services/authService';
import { toast } from '../stores/toastStore';

export default function Login() {
    const navigate = useNavigate();
    const setAuth = useAuthStore((state) => state.setAuth);

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [otpCode, setOtpCode] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [needsVerification, setNeedsVerification] = useState(false);

    const [emailError, setEmailError] = useState('');
    const [passwordError, setPasswordError] = useState('');

    function validateForm(): boolean {
        let valid = true;
        setEmailError('');
        setPasswordError('');

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!email) {
            setEmailError('Email é obrigatório');
            valid = false;
        } else if (!emailRegex.test(email)) {
            setEmailError('Formato de email inválido');
            valid = false;
        }

        if (!password) {
            setPasswordError('Senha é obrigatória');
            valid = false;
        }

        return valid;
    }

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setError('');
        setNeedsVerification(false);

        if (!validateForm()) return;

        setLoading(true);

        try {
            const response = await login({ email, password, otp_code: otpCode || undefined });
            setAuth(response.user, response.access_token, response.refresh_token);
            toast.success(`Bem-vindo, ${response.user.name || response.user.email}!`);

            if (response.user.role === 'employer') {
                navigate('/dashboard/employer');
            } else {
                navigate('/dashboard/candidate');
            }
        } catch (err: unknown) {
            if (err && typeof err === 'object' && 'response' in err) {
                const axiosError = err as { response?: { data?: { detail?: string } } };
                const detail = axiosError.response?.data?.detail || 'Credenciais inválidas. Tente novamente.';
                setError(detail);
                setNeedsVerification(detail.includes('Confirme seu e-mail'));
            } else {
                setError('Erro ao conectar com o servidor. Tente novamente.');
            }
        } finally {
            setLoading(false);
        }
    }

    return (
        <Box
            sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: 'calc(100vh - 140px)',
                py: 4,
            }}
        >
            <Container maxWidth="sm">
                <Paper
                    elevation={0}
                    sx={{
                        p: { xs: 3, sm: 5 },
                        width: '100%',
                        boxShadow: '0 8px 40px rgba(0, 0, 0, 0.08)',
                        border: '1px solid rgba(0, 0, 0, 0.06)',
                    }}
                >
                    {/* Logo/Brand */}
                    <Box sx={{ textAlign: 'center', mb: 4 }}>
                        <Box
                            sx={{
                                width: 56,
                                height: 56,
                                borderRadius: 3,
                                background: 'linear-gradient(135deg, #1a237e 0%, #1565c0 100%)',
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                mb: 2,
                                boxShadow: '0 4px 14px rgba(26, 35, 126, 0.3)',
                            }}
                        >
                            <Box component="img" src="/brand-icon.svg" alt="Recruta IA" sx={{ width: 56, height: 56, borderRadius: 3 }} />
                        </Box>
                        <Typography variant="h5" component="h1" sx={{ fontWeight: 700, color: 'text.primary' }}>
                            Bem-vindo de volta
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            Entre na plataforma de Recrutamento IA
                        </Typography>
                    </Box>

                    {error && (
                        <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
                            {error}
                            {needsVerification && (
                                <Box sx={{ mt: 1 }}>
                                    <Link component={RouterLink} to={`/verify-email?email=${encodeURIComponent(email)}`} sx={{ fontWeight: 700 }}>
                                        Reenviar link de confirmação
                                    </Link>
                                </Box>
                            )}
                        </Alert>
                    )}

                    <Box component="form" onSubmit={handleSubmit} noValidate>
                        <TextField
                            margin="normal"
                            required
                            fullWidth
                            id="email"
                            label="Email"
                            name="email"
                            autoComplete="email"
                            autoFocus
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            error={!!emailError}
                            helperText={emailError}
                        />
                        <TextField
                            margin="normal"
                            required
                            fullWidth
                            name="password"
                            label="Senha"
                            type="password"
                            id="password"
                            autoComplete="current-password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            error={!!passwordError}
                            helperText={passwordError}
                        />
                        <Box sx={{ textAlign: 'right', mt: 0.5 }}>
                            <Link component={RouterLink} to="/forgot-password" variant="body2">
                                Esqueci minha senha
                            </Link>
                        </Box>
                        <TextField margin="normal" fullWidth label="Código 2FA (administradores)" inputMode="numeric" value={otpCode} onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))} helperText="Preencha somente se a autenticação em dois fatores estiver ativada." />
                        <Button
                            type="submit"
                            fullWidth
                            variant="contained"
                            size="large"
                            sx={{
                                mt: 3,
                                mb: 2,
                                py: 1.5,
                                background: 'linear-gradient(135deg, #1a237e 0%, #1565c0 100%)',
                                '&:hover': {
                                    background: 'linear-gradient(135deg, #283593 0%, #1976d2 100%)',
                                },
                            }}
                            disabled={loading}
                        >
                            {loading ? 'Entrando...' : 'Entrar'}
                        </Button>
                    </Box>

                    <Divider sx={{ my: 3 }}>
                        <Typography variant="body2" color="text.secondary">
                            ou
                        </Typography>
                    </Divider>

                    <Stack spacing={2}>
                        <Button
                            fullWidth
                            variant="outlined"
                            startIcon={<GoogleIcon />}
                            onClick={() => oauthRedirect('google')}
                            sx={{
                                py: 1.2,
                                borderColor: 'divider',
                                color: 'text.primary',
                                '&:hover': {
                                    borderColor: 'primary.main',
                                    bgcolor: 'rgba(40, 53, 147, 0.04)',
                                },
                            }}
                        >
                            Entrar com Google
                        </Button>
                        <Button
                            fullWidth
                            variant="outlined"
                            startIcon={<LinkedInIcon />}
                            onClick={() => oauthRedirect('linkedin')}
                            sx={{
                                py: 1.2,
                                borderColor: 'divider',
                                color: 'text.primary',
                                '&:hover': {
                                    borderColor: '#0077b5',
                                    bgcolor: 'rgba(0, 119, 181, 0.04)',
                                },
                            }}
                        >
                            Entrar com LinkedIn
                        </Button>
                    </Stack>

                    <Box sx={{ mt: 3, textAlign: 'center' }}>
                        <Link component={RouterLink} to="/register" variant="body2" sx={{ fontWeight: 500 }}>
                            Não tem conta? Cadastre-se
                        </Link>
                    </Box>
                </Paper>
            </Container>
        </Box>
    );
}
