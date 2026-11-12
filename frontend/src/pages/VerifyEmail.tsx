import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Alert, Box, Button, CircularProgress, Container, Link, Paper, TextField, Typography } from '@mui/material';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { confirmEmailVerification, requestEmailVerification } from '../services/authService';

export default function VerifyEmail() {
    const [params] = useSearchParams();
    const token = params.get('token') ?? '';
    const [email, setEmail] = useState(params.get('email') ?? '');
    const [message, setMessage] = useState(token ? '' : 'Cadastro realizado. Confira seu e-mail para ativar a conta.');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(Boolean(token));
    const requested = useRef(false);

    useEffect(() => {
        if (!token || requested.current) return;
        requested.current = true;
        confirmEmailVerification(token)
            .then(setMessage)
            .catch((err: unknown) => setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Não foi possível confirmar o e-mail.'))
            .finally(() => setLoading(false));
    }, [token]);

    async function resend(event: FormEvent) {
        event.preventDefault(); setLoading(true); setError('');
        try { setMessage(await requestEmailVerification(email)); }
        catch { setError('Não foi possível processar a solicitação.'); }
        finally { setLoading(false); }
    }

    return <Container maxWidth="sm" sx={{ py: { xs: 5, md: 9 } }}><Paper elevation={0} sx={{ p: { xs: 3, sm: 5 }, textAlign: 'center', border: '1px solid', borderColor: 'divider' }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 800 }}>Confirmação de e-mail</Typography>
        {loading && token && <CircularProgress sx={{ my: 4 }} />}
        {message && <Alert severity="success" sx={{ my: 3, textAlign: 'left' }}>{message}</Alert>}
        {error && <Alert severity="error" sx={{ my: 3, textAlign: 'left' }}>{error}</Alert>}
        {!token && <Box component="form" onSubmit={resend} sx={{ mt: 3 }}>
            <TextField fullWidth required type="email" label="E-mail" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Button fullWidth type="submit" variant="outlined" disabled={loading || !email} sx={{ mt: 2 }}>{loading ? 'Enviando...' : 'Reenviar confirmação'}</Button>
        </Box>}
        <Box sx={{ mt: 3 }}><Link component={RouterLink} to="/login">Ir para o login</Link></Box>
    </Paper></Container>;
}
