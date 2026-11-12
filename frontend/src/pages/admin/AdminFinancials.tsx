import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    Box,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    TablePagination,
    TextField,
    Button,
    Card,
    CardContent,
    Grid,
    Chip,
    CircularProgress,
    Alert,
    Tabs,
    Tab,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import {
    getAdminTransactions,
    getAdminPayments,
    getAdminRevenue,
    exportCsv,
} from '../../services/adminService';
import { formatBRL } from '../../utils/currency';

export default function AdminFinancials() {
    const [tab, setTab] = useState(0);
    const [txPage, setTxPage] = useState(0);
    const [txPageSize, setTxPageSize] = useState(20);
    const [payPage, setPayPage] = useState(0);
    const [payPageSize, setPayPageSize] = useState(20);

    // Date range for revenue
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
    const [startDate, setStartDate] = useState(thirtyDaysAgo.toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(today.toISOString().split('T')[0]);

    const { data: revenue, isLoading: revenueLoading } = useQuery({
        queryKey: ['admin', 'revenue', startDate, endDate],
        queryFn: () => getAdminRevenue(startDate, endDate),
        enabled: !!startDate && !!endDate,
    });

    const { data: transactions, isLoading: txLoading, error: txError } = useQuery({
        queryKey: ['admin', 'transactions', txPage, txPageSize],
        queryFn: () => getAdminTransactions(txPage + 1, txPageSize),
    });

    const { data: payments, isLoading: payLoading, error: payError } = useQuery({
        queryKey: ['admin', 'payments', payPage, payPageSize],
        queryFn: () => getAdminPayments(payPage + 1, payPageSize),
    });

    const paymentStatusColor = (status: string) => {
        switch (status) {
            case 'confirmed': return 'success';
            case 'pending': return 'warning';
            case 'failed': return 'error';
            case 'expired': return 'default';
            default: return 'default';
        }
    };

    const txTypeColor = (type: string) => {
        switch (type) {
            case 'credit': return 'success';
            case 'debit': return 'error';
            case 'refund': return 'info';
            default: return 'default';
        }
    };

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                    Módulo Financeiro
                </Typography>
                <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={() => exportCsv('payments')}
                >
                    Exportar CSV
                </Button>
            </Box>

            {/* Revenue Summary */}
            <Paper sx={{ p: 2, mb: 3 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>Receita por Período</Typography>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
                    <TextField
                        label="Data Início"
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        slotProps={{ inputLabel: { shrink: true } }}
                        size="small"
                    />
                    <TextField
                        label="Data Fim"
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        slotProps={{ inputLabel: { shrink: true } }}
                        size="small"
                    />
                </Box>
                {revenueLoading ? (
                    <CircularProgress size={24} />
                ) : revenue ? (
                    <Grid container spacing={2}>
                        <Grid size={{ xs: 12, sm: 4 }}>
                            <Card variant="outlined">
                                <CardContent>
                                    <Typography variant="body2" color="text.secondary">Receita Total</Typography>
                                    <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                                        {formatBRL(revenue.total_revenue)}
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 4 }}>
                            <Card variant="outlined">
                                <CardContent>
                                    <Typography variant="body2" color="text.secondary">Receita Tokens</Typography>
                                    <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                                        {formatBRL(revenue.token_revenue)}
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 4 }}>
                            <Card variant="outlined">
                                <CardContent>
                                    <Typography variant="body2" color="text.secondary">Receita Assinaturas</Typography>
                                    <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                                        {formatBRL(revenue.subscription_revenue)}
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>
                    </Grid>
                ) : null}
            </Paper>

            {/* Tabs for Transactions / Payments */}
            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label="Transações de Tokens" />
                <Tab label="Pagamentos" />
            </Tabs>

            {tab === 0 && (
                <>
                    {txError && <Alert severity="error" sx={{ mb: 2 }}>Erro ao carregar transações.</Alert>}
                    {txLoading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                            <CircularProgress />
                        </Box>
                    ) : (
                        <Paper>
                            <TableContainer>
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Usuário</TableCell>
                                            <TableCell>Tipo</TableCell>
                                            <TableCell>Quantidade</TableCell>
                                            <TableCell>Descrição</TableCell>
                                            <TableCell>Data</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {transactions?.items.map((tx) => (
                                            <TableRow key={tx.id}>
                                                <TableCell>{tx.user_name}</TableCell>
                                                <TableCell>
                                                    <Chip label={tx.type} size="small" color={txTypeColor(tx.type)} />
                                                </TableCell>
                                                <TableCell>{formatBRL(tx.amount)}</TableCell>
                                                <TableCell>{tx.description}</TableCell>
                                                <TableCell>
                                                    {new Date(tx.created_at).toLocaleDateString('pt-BR')}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                            <TablePagination
                                component="div"
                                count={transactions?.total ?? 0}
                                page={txPage}
                                onPageChange={(_, p) => setTxPage(p)}
                                rowsPerPage={txPageSize}
                                onRowsPerPageChange={(e) => {
                                    setTxPageSize(parseInt(e.target.value, 10));
                                    setTxPage(0);
                                }}
                                labelRowsPerPage="Itens por página"
                            />
                        </Paper>
                    )}
                </>
            )}

            {tab === 1 && (
                <>
                    {payError && <Alert severity="error" sx={{ mb: 2 }}>Erro ao carregar pagamentos.</Alert>}
                    {payLoading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                            <CircularProgress />
                        </Box>
                    ) : (
                        <Paper>
                            <TableContainer>
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Usuário</TableCell>
                                            <TableCell>Método</TableCell>
                                            <TableCell>Valor</TableCell>
                                            <TableCell>Status</TableCell>
                                            <TableCell>Data</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {payments?.items.map((pay) => (
                                            <TableRow key={pay.id}>
                                                <TableCell>{pay.user_name}</TableCell>
                                                <TableCell>
                                                    <Chip label={pay.method === 'checkout_pro' ? 'Mercado Pago' : pay.method.toUpperCase()} size="small" variant="outlined" />
                                                </TableCell>
                                                <TableCell>
                                                    {formatBRL(pay.amount)}
                                                </TableCell>
                                                <TableCell>
                                                    <Chip
                                                        label={pay.status}
                                                        size="small"
                                                        color={paymentStatusColor(pay.status)}
                                                    />
                                                </TableCell>
                                                <TableCell>
                                                    {new Date(pay.created_at).toLocaleDateString('pt-BR')}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                            <TablePagination
                                component="div"
                                count={payments?.total ?? 0}
                                page={payPage}
                                onPageChange={(_, p) => setPayPage(p)}
                                rowsPerPage={payPageSize}
                                onRowsPerPageChange={(e) => {
                                    setPayPageSize(parseInt(e.target.value, 10));
                                    setPayPage(0);
                                }}
                                labelRowsPerPage="Itens por página"
                            />
                        </Paper>
                    )}
                </>
            )}
        </Box>
    );
}
