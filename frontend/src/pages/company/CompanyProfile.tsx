import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Box, Button, CircularProgress, Container, Grid, MenuItem, Paper, TextField, Typography } from '@mui/material';
import BusinessRounded from '@mui/icons-material/BusinessRounded';
import SaveRounded from '@mui/icons-material/SaveRounded';
import { getMyCompany, lookupCnpj, saveMyCompany, type CompanyProfile as CompanyData } from '../../services/companyService';

const emptyCompany: CompanyData = {
    name: '', legal_name: '', cnpj: '', description: '', website: '', email: '', phone: '',
    industry: '', company_size: '', city: '', state: '', address: '', logo_url: '',
};

function formatCnpj(value: string) {
    return value.replace(/\D/g, '').slice(0, 14)
        .replace(/^(\d{2})(\d)/, '$1.$2').replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
        .replace(/\.(\d{3})(\d)/, '.$1/$2').replace(/(\d{4})(\d)/, '$1-$2');
}

export default function CompanyProfile() {
    const queryClient = useQueryClient();
    const [form, setForm] = useState<CompanyData>(emptyCompany);
    const [message, setMessage] = useState('');
    const { data, isLoading, isError } = useQuery({ queryKey: ['my-company'], queryFn: getMyCompany });
    useEffect(() => { if (data) setForm({ ...emptyCompany, ...data, cnpj: formatCnpj(data.cnpj) }); }, [data]);

    const mutation = useMutation({
        mutationFn: saveMyCompany,
        onSuccess: async (saved) => {
            setForm({ ...emptyCompany, ...saved, cnpj: formatCnpj(saved.cnpj) });
            setMessage('Empresa salva com sucesso.');
            await queryClient.invalidateQueries({ queryKey: ['my-company'] });
        },
    });
    const cnpjMutation = useMutation({
        mutationFn: () => lookupCnpj(form.cnpj),
        onSuccess: (result) => {
            setForm((current) => ({
                ...current,
                cnpj: formatCnpj(result.cnpj), name: result.name || current.name,
                legal_name: result.legal_name || current.legal_name,
                industry: result.industry || current.industry, phone: result.phone || current.phone,
                city: result.city || current.city, state: result.state || current.state,
                address: result.address || current.address, cnpj_status: result.status,
                cnpj_source: result.source,
            }));
        },
    });
    const change = (field: keyof CompanyData) => (event: React.ChangeEvent<HTMLInputElement>) =>
        setForm((current) => ({ ...current, [field]: field === 'cnpj' ? formatCnpj(event.target.value) : event.target.value }));
    const detail = (mutation.error as { response?: { data?: { detail?: string } } } | null)?.response?.data?.detail;
    const cnpjDetail = (cnpjMutation.error as { response?: { data?: { detail?: string } } } | null)?.response?.data?.detail;

    if (isLoading) return <Box sx={{ minHeight: '50vh', display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>;
    return <Container maxWidth="md" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
            <BusinessRounded color="primary" sx={{ fontSize: 38 }} />
            <Box><Typography variant="h4" component="h1">Minha empresa</Typography><Typography color="text.secondary">Estas informações serão exibidas nas suas vagas.</Typography></Box>
        </Box>
        <Paper component="form" onSubmit={(e) => { e.preventDefault(); setMessage(''); mutation.mutate(form); }} sx={{ p: { xs: 2.5, sm: 4 } }}>
            {isError && <Alert severity="error" sx={{ mb: 2 }}>Não foi possível carregar os dados da empresa.</Alert>}
            {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
            {mutation.isError && <Alert severity="error" sx={{ mb: 2 }}>{detail || 'Não foi possível salvar a empresa.'}</Alert>}
            {form.cnpj_status && <Alert severity={form.cnpj_status === 'ATIVA' ? 'success' : 'warning'} sx={{ mb: 2 }}>Situação cadastral: <strong>{form.cnpj_status}</strong> · Fonte: {form.cnpj_source || 'base pública consultada'}</Alert>}
            {cnpjMutation.isError && <Alert severity="error" sx={{ mb: 2 }}>{cnpjDetail || 'Não foi possível consultar o CNPJ.'}</Alert>}
            <Grid container spacing={2.5}>
                <Grid size={{ xs: 12, sm: 6 }}><TextField required fullWidth label="Nome fantasia" value={form.name} onChange={change('name')} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Razão social" value={form.legal_name} onChange={change('legal_name')} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField required fullWidth label="CNPJ" value={form.cnpj} onChange={change('cnpj')} slotProps={{ htmlInput: { inputMode: 'numeric' } }} helperText="Consulte para preencher os dados públicos e verificar a situação cadastral." /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><Button variant="outlined" sx={{ mt: 1 }} disabled={form.cnpj.replace(/\D/g, '').length !== 14 || cnpjMutation.isPending} onClick={() => cnpjMutation.mutate()}>{cnpjMutation.isPending ? 'Consultando...' : 'Consultar CNPJ'}</Button></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Segmento" value={form.industry} onChange={change('industry')} placeholder="Ex.: Hotelaria, Tecnologia" /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField select fullWidth label="Porte" value={form.company_size} onChange={change('company_size')}>
                    <MenuItem value="">Não informado</MenuItem><MenuItem value="micro">Microempresa</MenuItem><MenuItem value="small">Pequena</MenuItem><MenuItem value="medium">Média</MenuItem><MenuItem value="large">Grande</MenuItem>
                </TextField></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth type="email" label="E-mail comercial" value={form.email} onChange={change('email')} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Telefone" value={form.phone} onChange={change('phone')} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><TextField fullWidth label="Site" value={form.website} onChange={change('website')} placeholder="https://" /></Grid>
                <Grid size={{ xs: 12, sm: 8 }}><TextField fullWidth label="Cidade" value={form.city} onChange={change('city')} /></Grid>
                <Grid size={{ xs: 12, sm: 4 }}><TextField fullWidth label="UF" value={form.state} onChange={change('state')} slotProps={{ htmlInput: { maxLength: 2 } }} /></Grid>
                <Grid size={{ xs: 12 }}><TextField fullWidth label="Endereço" value={form.address} onChange={change('address')} /></Grid>
                <Grid size={{ xs: 12 }}><TextField fullWidth label="URL da logo" value={form.logo_url} onChange={change('logo_url')} placeholder="https://" /></Grid>
                <Grid size={{ xs: 12 }}><TextField fullWidth multiline minRows={4} label="Descrição da empresa" value={form.description} onChange={change('description')} /></Grid>
            </Grid>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}><Button type="submit" size="large" variant="contained" startIcon={<SaveRounded />} disabled={mutation.isPending}>{mutation.isPending ? 'Salvando...' : 'Salvar empresa'}</Button></Box>
        </Paper>
    </Container>;
}
