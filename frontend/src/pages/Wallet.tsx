import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Container, Divider, List, ListItem, ListItemText, Paper, Stack, TextField, Typography } from '@mui/material';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import { createWalletCheckout, getPaymentDetail, getWalletBalance, getWalletTransactions, reconcileWalletCheckout } from '../services/walletService';
import { formatBRL } from '../utils/currency';
import { usePaymentConfig } from '../hooks/usePaymentConfig';

export default function Wallet() {
    const queryClient = useQueryClient();
    const [amount, setAmount] = useState('50');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const paymentConfig = usePaymentConfig();
    const { data } = useQuery({ queryKey: ['wallet-balance'], queryFn: getWalletBalance });
    const { data: transactions = [] } = useQuery({ queryKey: ['wallet-transactions'], queryFn: getWalletTransactions });
    const checkoutResult = new URLSearchParams(window.location.search).get('checkout');
    const mercadoPagoPaymentId = new URLSearchParams(window.location.search).get('payment_id');
    const returningPaymentId = checkoutResult ? sessionStorage.getItem('wallet_checkout_payment_id') : null;
    const reconciliationStarted = useRef(false);
    const { data: returningPayment } = useQuery({
        queryKey: ['wallet-payment', returningPaymentId],
        queryFn: () => getPaymentDetail(returningPaymentId!),
        enabled: Boolean(returningPaymentId),
        refetchInterval: (query) => query.state.data?.status === 'pending' ? 2500 : false,
    });

    useEffect(() => {
        if (returningPayment?.status === 'confirmed') {
            sessionStorage.removeItem('wallet_checkout_payment_id');
            queryClient.invalidateQueries({ queryKey: ['wallet-balance'] });
            queryClient.invalidateQueries({ queryKey: ['wallet-transactions'] });
        }
    }, [returningPayment?.status, queryClient]);

    useEffect(() => {
        if (!mercadoPagoPaymentId || reconciliationStarted.current) return;
        reconciliationStarted.current = true;
        reconcileWalletCheckout(mercadoPagoPaymentId)
            .then(() => {
                queryClient.invalidateQueries({ queryKey: ['wallet-balance'] });
                queryClient.invalidateQueries({ queryKey: ['wallet-transactions'] });
                queryClient.invalidateQueries({ queryKey: ['wallet-payment', returningPaymentId] });
            })
            .catch(() => {
                // The webhook may still complete the payment; regular polling remains active.
                reconciliationStarted.current = false;
            });
    }, [mercadoPagoPaymentId, queryClient, returningPaymentId]);

    async function addBalance() {
        const value = Number(amount);
        if (!Number.isFinite(value) || value < paymentConfig.minimum_wallet_topup) {
            setError(`Informe um valor mínimo de ${formatBRL(paymentConfig.minimum_wallet_topup)}.`); return;
        }
        setLoading(true); setError('');
        try {
            const checkout = await createWalletCheckout(value);
            sessionStorage.setItem('wallet_checkout_payment_id', checkout.payment_id);
            window.location.assign(checkout.checkout_url);
        }
        catch (e) {
            const err = e as { response?: { data?: { detail?: string } } };
            setError(err.response?.data?.detail || 'Não foi possível abrir o Mercado Pago.');
        } finally { setLoading(false); }
    }

    return <Container maxWidth="sm" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom><AccountBalanceWalletIcon sx={{ mr: 1 }} />Minha carteira</Typography>
        {checkoutResult && returningPayment?.status === 'confirmed' &&
            <Alert severity="success" sx={{ mb: 2 }}>Pagamento aprovado. O saldo já foi adicionado à sua carteira.</Alert>}
        {checkoutResult !== 'failure' && checkoutResult && (!returningPayment || returningPayment.status === 'pending') &&
            <Alert severity="info" sx={{ mb: 2 }}>Pagamento recebido e em processamento. Esta página será atualizada automaticamente.</Alert>}
        {checkoutResult === 'failure' && returningPayment?.status !== 'confirmed' &&
            <Alert severity="warning" sx={{ mb: 2 }}>O pagamento não foi concluído. Você pode tentar novamente.</Alert>}
        <Paper sx={{ p: 3 }}>
            <Stack spacing={3}>
                <Typography variant="h3">{formatBRL(data?.balance)}</Typography>
                <Typography color="text.secondary">Use o saldo somente para solicitar análises de currículo e compatibilidade com vagas.</Typography>
                <TextField label="Valor para adicionar (R$)" type="number" value={amount}
                    onChange={(e) => setAmount(e.target.value)} slotProps={{ htmlInput: { min: paymentConfig.minimum_wallet_topup, step: '0.01' } }} />
                {error && <Alert severity="error">{error}</Alert>}
                <Button variant="contained" onClick={addBalance} disabled={loading}>
                    {loading ? 'Abrindo Mercado Pago...' : 'Ir para o Mercado Pago'}
                </Button>
                <Typography variant="caption" color="text.secondary">
                    O pagamento será realizado no ambiente seguro do Mercado Pago. O saldo é liberado após a confirmação oficial.
                </Typography>
            </Stack>
        </Paper>
        <Paper sx={{ p: 3, mt: 3 }}>
            <Typography variant="h6">Histórico</Typography>
            <List>
                {transactions.map((item, index) => <div key={item.id}>
                    {index > 0 && <Divider />}
                    <ListItem disableGutters>
                        <ListItemText primary={item.reason} secondary={new Date(item.created_at).toLocaleString('pt-BR')} />
                        <Typography color={item.amount >= 0 ? 'success.main' : 'error.main'} sx={{ fontWeight: 600 }}>
                            {item.amount >= 0 ? '+' : '-'} {formatBRL(Math.abs(Number(item.amount)))}
                        </Typography>
                    </ListItem>
                </div>)}
                {transactions.length === 0 && <Typography color="text.secondary">Nenhuma movimentação.</Typography>}
            </List>
        </Paper>
    </Container>;
}
