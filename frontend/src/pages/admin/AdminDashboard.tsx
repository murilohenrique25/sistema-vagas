import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    Box,
    Card,
    CardContent,
    Grid,
    Typography,
    ToggleButton,
    ToggleButtonGroup,
    Divider,
    CircularProgress,
    Alert,
} from '@mui/material';
import WorkIcon from '@mui/icons-material/Work';
import PeopleIcon from '@mui/icons-material/People';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TimerIcon from '@mui/icons-material/Timer';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import PsychologyIcon from '@mui/icons-material/Psychology';
import {
    getPlatformKpis,
    getFinancialMetrics,
    getAiMetrics,
} from '../../services/adminService';
import type { MetricPeriod } from '../../types/admin';
import { formatBRL } from '../../utils/currency';

function KpiCard({
    title,
    value,
    icon,
    color = 'primary.main',
}: {
    title: string;
    value: string | number;
    icon: React.ReactNode;
    color?: string;
}) {
    return (
        <Card sx={{ height: '100%' }}>
            <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Box sx={{ color }}>{icon}</Box>
                    <Typography variant="body2" color="text.secondary">
                        {title}
                    </Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                    {value}
                </Typography>
            </CardContent>
        </Card>
    );
}

export default function AdminDashboard() {
    const [period, setPeriod] = useState<MetricPeriod>('monthly');

    const {
        data: kpis,
        isLoading: kpisLoading,
        error: kpisError,
    } = useQuery({
        queryKey: ['admin', 'kpis', period],
        queryFn: () => getPlatformKpis(period),
        refetchInterval: 60000,
    });

    const {
        data: financial,
        isLoading: financialLoading,
        error: financialError,
    } = useQuery({
        queryKey: ['admin', 'financial-metrics', period],
        queryFn: () => getFinancialMetrics(period),
        refetchInterval: 60000,
    });

    const {
        data: ai,
        isLoading: aiLoading,
        error: aiError,
    } = useQuery({
        queryKey: ['admin', 'ai-metrics', period],
        queryFn: () => getAiMetrics(period),
        refetchInterval: 60000,
    });

    const isLoading = kpisLoading || financialLoading || aiLoading;
    const error = kpisError || financialError || aiError;

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                    Painel Administrativo
                </Typography>
                <ToggleButtonGroup
                    value={period}
                    exclusive
                    onChange={(_, val) => val && setPeriod(val)}
                    size="small"
                >
                    <ToggleButton value="daily">Diário</ToggleButton>
                    <ToggleButton value="weekly">Semanal</ToggleButton>
                    <ToggleButton value="monthly">Mensal</ToggleButton>
                    <ToggleButton value="quarterly">Trimestral</ToggleButton>
                    <ToggleButton value="yearly">Anual</ToggleButton>
                </ToggleButtonGroup>
            </Box>

            {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    Erro ao carregar métricas. Tente novamente.
                </Alert>
            )}

            {isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
                    <CircularProgress />
                </Box>
            ) : (
                <>
                    {/* Platform KPIs */}
                    <Typography variant="h6" sx={{ mb: 2 }}>
                        KPIs da Plataforma
                    </Typography>
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                            <KpiCard
                                title="Vagas Publicadas"
                                value={kpis?.jobs_published ?? 0}
                                icon={<WorkIcon />}
                                color="primary.main"
                            />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                            <KpiCard
                                title="Candidaturas"
                                value={kpis?.total_applications ?? 0}
                                icon={<PeopleIcon />}
                                color="info.main"
                            />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                            <KpiCard
                                title="Taxa de Contratação"
                                value={`${((kpis?.hiring_rate ?? 0) * 100).toFixed(1)}%`}
                                icon={<TrendingUpIcon />}
                                color="success.main"
                            />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                            <KpiCard
                                title="Tempo Médio Contratação"
                                value={`${kpis?.avg_time_to_hire_days ?? 0}d`}
                                icon={<TimerIcon />}
                                color="warning.main"
                            />
                        </Grid>
                    </Grid>

                    <Divider sx={{ my: 3 }} />

                    {/* Financial Summary */}
                    <Typography variant="h6" sx={{ mb: 2 }}>
                        Resumo Financeiro
                    </Typography>
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                            <KpiCard
                                title="Receita Total"
                                value={formatBRL(financial?.total_revenue)}
                                icon={<AttachMoneyIcon />}
                                color="success.main"
                            />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                            <KpiCard
                                title="Receita Tokens"
                                value={formatBRL(financial?.token_revenue)}
                                icon={<AttachMoneyIcon />}
                                color="primary.main"
                            />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                            <KpiCard
                                title="Receita Assinaturas"
                                value={formatBRL(financial?.subscription_revenue)}
                                icon={<AttachMoneyIcon />}
                                color="info.main"
                            />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                            <KpiCard
                                title="Ticket Médio"
                                value={formatBRL(financial?.avg_ticket)}
                                icon={<AttachMoneyIcon />}
                                color="warning.main"
                            />
                        </Grid>
                    </Grid>

                    <Divider sx={{ my: 3 }} />

                    {/* AI Metrics */}
                    <Typography variant="h6" sx={{ mb: 2 }}>
                        Métricas de IA
                    </Typography>
                    <Grid container spacing={2}>
                        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                            <KpiCard
                                title="Total de Análises"
                                value={ai?.total_analyses ?? 0}
                                icon={<PsychologyIcon />}
                                color="secondary.main"
                            />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                            <KpiCard
                                title="Consumo de Tokens"
                                value={ai?.token_consumption ?? 0}
                                icon={<PsychologyIcon />}
                                color="warning.main"
                            />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                            <KpiCard
                                title="Score Médio"
                                value={`${(ai?.avg_score ?? 0).toFixed(1)}`}
                                icon={<PsychologyIcon />}
                                color="info.main"
                            />
                        </Grid>
                    </Grid>
                </>
            )}
        </Box>
    );
}
