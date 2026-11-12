import { useState, type FormEvent } from 'react';
import { Alert, Box, Button, Container, Link, Paper, TextField, Typography } from '@mui/material';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../services/authService';

export default function ResetPassword() {
    const [params] = useSearchParams();
    const token = params.get('token') ?? '';
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState(token ? '' : 'Link inválido. Solicite uma nova recuperação de senha.');
    const [loading, setLoading] = useState(false);

    async function submit(event: FormEvent) {
        event.preventDefault(); setError('');
        if (password !== confirm) { setError('As senhas não coincidem.'); return; }
        setLoading(true);
        try { setMessage(await resetPassword(token, password)); }
        catch (err: unknown) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(detail || 'Não foi possível redefinir a senha.');
        } finally { setLoading(false); }
    }

    return <Container maxWidth="sm" sx={{ py: { xs: 5, md: 9 } }}><Paper elevation={0} sx={{ p: { xs: 3, sm: 5 }, border: '1px solid', borderColor: 'divider' }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 800 }}>Criar nova senha</Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>Use ao menos 8 caracteres, com maiúscula, minúscula, número e caractere especial.</Typography>
        {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {!message && <Box component="form" onSubmit={submit}>
            <TextField fullWidth required type="password" label="Nova senha" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} sx={{ mb: 2 }} />
            <TextField fullWidth required type="password" label="Confirmar nova senha" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            <Button fullWidth type="submit" variant="contained" size="large" disabled={loading || !token} sx={{ mt: 3 }}>{loading ? 'Salvando...' : 'Redefinir senha'}</Button>
        </Box>}
        <Box sx={{ textAlign: 'center', mt: 3 }}><Link component={RouterLink} to="/login">Ir para o login</Link></Box>
    </Paper></Container>;
}
