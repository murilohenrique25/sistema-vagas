import { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Paper,
    Grid,
    TextField,
    Button,
    MenuItem,
    Switch,
    FormControlLabel,
    CircularProgress,
    Alert,
    Snackbar,
    Divider,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import IntegrationInstructionsIcon from '@mui/icons-material/IntegrationInstructions';
import PaidOutlinedIcon from '@mui/icons-material/PaidOutlined';
import { getPaymentSettings, updatePaymentSettings } from '../../services/adminService';
import { useQueryClient } from '@tanstack/react-query';

interface PaymentFormData {
    pix_key_type: string;
    pix_key: string;
    pix_beneficiary_name: string;
    gateway_provider: string;
    gateway_api_key: string;
    gateway_secret_key: string;
    gateway_webhook_url: string;
    bank_name: string;
    bank_agency: string;
    bank_account: string;
    bank_account_type: string;
    resume_analysis_price: number;
    job_compatibility_price: number;
    minimum_wallet_topup: number;
    is_active: boolean;
}

const initialFormData: PaymentFormData = {
    pix_key_type: '',
    pix_key: '',
    pix_beneficiary_name: '',
    gateway_provider: '',
    gateway_api_key: '',
    gateway_secret_key: '',
    gateway_webhook_url: '',
    bank_name: '',
    bank_agency: '',
    bank_account: '',
    bank_account_type: '',
    resume_analysis_price: 5,
    job_compatibility_price: 5,
    minimum_wallet_topup: 1,
    is_active: true,
};

const gatewayProviders = [
    { value: 'mercadopago', label: 'Mercado Pago' },
];

export default function AdminPaymentSettings() {
    const queryClient = useQueryClient();
    const [formData, setFormData] = useState<PaymentFormData>(initialFormData);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
        open: false,
        message: '',
        severity: 'success',
    });

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            setLoading(true);
            const data = await getPaymentSettings();
            if (data.exists) {
                setFormData({
                    pix_key_type: data.pix_key_type || '',
                    pix_key: data.pix_key || '',
                    pix_beneficiary_name: data.pix_beneficiary_name || '',
                    gateway_provider: data.gateway_provider || '',
                    gateway_api_key: data.gateway_api_key || '',
                    gateway_secret_key: data.gateway_secret_key || '',
                    gateway_webhook_url: data.gateway_webhook_url || '',
                    bank_name: data.bank_name || '',
                    bank_agency: data.bank_agency || '',
                    bank_account: data.bank_account || '',
                    bank_account_type: data.bank_account_type || '',
                    resume_analysis_price: Number(data.resume_analysis_price ?? 5),
                    job_compatibility_price: Number(data.job_compatibility_price ?? 5),
                    minimum_wallet_topup: Number(data.minimum_wallet_topup ?? 1),
                    is_active: data.is_active ?? true,
                });
            }
        } catch {
            setSnackbar({ open: true, message: 'Erro ao carregar configurações.', severity: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (field: keyof PaymentFormData) => (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
    ) => {
        setFormData({ ...formData, [field]: e.target.value });
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            await updatePaymentSettings(formData);
            await queryClient.invalidateQueries({ queryKey: ['payment-config'] });
            setSnackbar({ open: true, message: 'Configurações salvas com sucesso!', severity: 'success' });
        } catch {
            setSnackbar({ open: true, message: 'Erro ao salvar configurações.', severity: 'error' });
        } finally {
            setSaving(false);
        }
    };

    const handlePriceChange = (field: keyof PaymentFormData) => (
        e: React.ChangeEvent<HTMLInputElement>
    ) => setFormData({ ...formData, [field]: Number(e.target.value) });

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                    Configurações de Pagamento
                </Typography>
                <FormControlLabel
                    control={
                        <Switch
                            checked={formData.is_active}
                            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                            color="primary"
                        />
                    }
                    label="Pagamentos ativos"
                />
            </Box>

            <Paper sx={{ p: 3, mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <PaidOutlinedIcon color="primary" />
                    <Typography variant="h6">Valores dos serviços</Typography>
                </Box>
                <Alert severity="info" sx={{ mb: 2 }}>
                    Toda entrada de dinheiro é realizada no Checkout Pro do Mercado Pago. As ações pagas consomem o saldo disponível na carteira.
                </Alert>
                <Grid container spacing={2}>
                    {([
                        ['resume_analysis_price', 'Análise de currículo'],
                        ['job_compatibility_price', 'Compatibilidade com vaga'],
                        ['minimum_wallet_topup', 'Recarga mínima da carteira'],
                    ] as const).map(([field, label]) => (
                        <Grid key={field} size={{ xs: 12, sm: 6, md: 4 }}>
                            <TextField label={label} type="number" value={formData[field]}
                                onChange={handlePriceChange(field)} fullWidth size="small"
                                slotProps={{ htmlInput: { min: 0.01, max: 50000, step: '0.01' } }} />
                        </Grid>
                    ))}
                </Grid>
            </Paper>

            {/* Gateway Section */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <IntegrationInstructionsIcon color="primary" />
                    <Typography variant="h6">Gateway de Pagamento</Typography>
                </Box>
                <Alert severity="warning" sx={{ mb: 2 }}>
                    As credenciais são criptografadas antes de serem gravadas e nunca são exibidas novamente. Deixe “•••” para manter o valor atual.
                </Alert>
                <Grid container spacing={2}>
                    <Grid size={{ xs: 12, sm: 6 }}>
                        <TextField
                            select
                            label="Provedor"
                            value={formData.gateway_provider}
                            onChange={handleChange('gateway_provider')}
                            fullWidth
                            size="small"
                        >
                            <MenuItem value="">Selecione...</MenuItem>
                            {gatewayProviders.map((opt) => (
                                <MenuItem key={opt.value} value={opt.value}>
                                    {opt.label}
                                </MenuItem>
                            ))}
                        </TextField>
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                        <TextField
                            label="Webhook URL"
                            value={formData.gateway_webhook_url}
                            onChange={handleChange('gateway_webhook_url')}
                            fullWidth
                            size="small"
                            placeholder="https://..."
                            helperText="Callback público: /v1/payments/webhooks/mercadopago"
                        />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                        <TextField
                            label="Access Token"
                            value={formData.gateway_api_key}
                            onChange={handleChange('gateway_api_key')}
                            fullWidth
                            size="small"
                            type="password"
                            helperText="Credencial privada de teste ou produção; nunca use a Public Key aqui"
                        />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                        <TextField
                            label="Segredo do webhook"
                            value={formData.gateway_secret_key}
                            onChange={handleChange('gateway_secret_key')}
                            fullWidth
                            size="small"
                            type="password"
                            helperText="Assinatura secreta do webhook"
                        />
                    </Grid>
                </Grid>
            </Paper>

            <Divider sx={{ my: 3 }} />

            {/* Save Button */}
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                    variant="contained"
                    size="large"
                    startIcon={<SaveIcon />}
                    onClick={handleSave}
                    disabled={saving}
                >
                    {saving ? 'Salvando...' : 'Salvar Configurações'}
                </Button>
            </Box>

            {/* Toast */}
            <Snackbar
                open={snackbar.open}
                autoHideDuration={4000}
                onClose={() => setSnackbar({ ...snackbar, open: false })}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            >
                <Alert
                    onClose={() => setSnackbar({ ...snackbar, open: false })}
                    severity={snackbar.severity}
                    variant="filled"
                    sx={{ width: '100%' }}
                >
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Box>
    );
}
