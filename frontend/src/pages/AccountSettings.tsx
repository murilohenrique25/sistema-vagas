import { useState } from 'react';
import { Alert, Box, Button, Checkbox, Container, FormControlLabel, Paper, TextField, Typography } from '@mui/material';
import DeleteForeverRounded from '@mui/icons-material/DeleteForeverRounded';
import WarningAmberRounded from '@mui/icons-material/WarningAmberRounded';
import { useNavigate } from 'react-router-dom';
import { deleteAccount } from '../services/authService';
import { useAuthStore } from '../stores/authStore';

const phrase = 'EXCLUIR MINHA CONTA';

export default function AccountSettings() {
    const navigate = useNavigate();
    const { user, logout } = useAuthStore();
    const [confirmation, setConfirmation] = useState('');
    const [password, setPassword] = useState('');
    const [acknowledged, setAcknowledged] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const employer = user?.role === 'employer';

    async function handleDelete() {
        setError(''); setLoading(true);
        try {
            await deleteAccount(confirmation, password || undefined);
            logout();
            navigate('/', { replace: true });
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setError(detail || 'Não foi possível excluir a conta.');
        } finally { setLoading(false); }
    }

    return <Container maxWidth="sm" sx={{ py: 5 }}>
        <Typography variant="h4" component="h1" sx={{ mb: 1, fontWeight: 750 }}>Configurações da conta</Typography>
        <Typography color="text.secondary" sx={{ mb: 4 }}>Gerencie o encerramento definitivo da sua conta.</Typography>
        <Paper sx={{ p: { xs: 3, sm: 4 }, border: '1px solid', borderColor: 'error.light' }}>
            <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', mb: 2 }}>
                <WarningAmberRounded color="error" />
                <Typography variant="h5" color="error.main" sx={{ fontWeight: 700 }}>Excluir conta permanentemente</Typography>
            </Box>
            <Alert severity="error" sx={{ mb: 2 }}>
                Esta ação é irreversível. Os dados removidos não poderão ser recuperados.
            </Alert>
            <Typography sx={{ mb: 2 }}>
                {employer
                    ? 'Serão excluídos a empresa, todas as vagas, candidaturas recebidas, análises, notificações e demais dados vinculados à conta.'
                    : 'Serão excluídos seu currículo, experiências, formação, candidaturas, análises, notificações e demais dados vinculados à conta.'}
            </Typography>
            <Alert severity="warning" sx={{ mb: 2 }}>
                Qualquer saldo restante será perdido e não poderá ser utilizado posteriormente. A exclusão da conta não gera reembolso automático, ressalvados os direitos previstos em lei.
            </Alert>
            <FormControlLabel sx={{ alignItems: 'flex-start', mb: 2 }} control={<Checkbox checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} />} label="Entendi que a exclusão é permanente e que perderei todos os dados e eventual saldo restante." />
            <TextField fullWidth label={`Digite ${phrase}`} value={confirmation} onChange={(e) => setConfirmation(e.target.value)} sx={{ mb: 2 }} />
            <TextField fullWidth type="password" label="Senha atual" helperText="Contas criadas com Google ou LinkedIn podem deixar este campo em branco." value={password} onChange={(e) => setPassword(e.target.value)} sx={{ mb: 2 }} />
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <Button fullWidth variant="contained" color="error" size="large" startIcon={<DeleteForeverRounded />} disabled={!acknowledged || confirmation !== phrase || loading} onClick={handleDelete}>
                {loading ? 'Excluindo definitivamente...' : 'Excluir minha conta e todos os dados'}
            </Button>
        </Paper>
    </Container>;
}
