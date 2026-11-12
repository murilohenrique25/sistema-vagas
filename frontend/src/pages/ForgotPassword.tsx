import { useState, type FormEvent } from 'react';
import { Alert, Box, Button, Container, Link, Paper, TextField, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { requestPasswordReset } from '../services/authService';

export default function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    async function submit(event: FormEvent) {
        event.preventDefault();
        setLoading(true); setError('');
        try { setMessage(await requestPasswordReset(email)); }
        catch { setError('Não foi possível processar a solicitação. Tente novamente.'); }
        finally { setLoading(false); }
    }

    return <Container maxWidth="sm" sx={{ py: { xs: 5, md: 9 } }}>
        <Paper elevation={0} sx={{ p: { xs: 3, sm: 5 }, border: '1px solid', borderColor: 'divider', boxShadow: '0 16px 45px rgba(24,39,90,.1)' }}>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 800 }}>Recuperar senha</Typography>
            <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>Informe seu e-mail. Se houver uma conta cadastrada, enviaremos um link seguro com validade limitada.</Typography>
            {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <Box component="form" onSubmit={submit}>
                <TextField fullWidth required type="email" label="E-mail" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                <Button fullWidth type="submit" variant="contained" size="large" disabled={loading || !email} sx={{ mt: 3 }}>{loading ? 'Enviando...' : 'Enviar link seguro'}</Button>
            </Box>
            <Box sx={{ textAlign: 'center', mt: 3 }}><Link component={RouterLink} to="/login">Voltar para o login</Link></Box>
        </Paper>
    </Container>;
}
