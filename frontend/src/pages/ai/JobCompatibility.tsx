/**
 * Candidate page: AI Job Compatibility.
 * Allows candidate to trigger compatibility analysis with active jobs.
 * Displays top 5 compatible jobs with percentages, justifications, and improvement suggestions.
 * Requirements: 9.1, 9.2, 9.3
 */
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Box,
    Container,
    Typography,
    Button,
    Alert,
    LinearProgress,
    Paper,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Chip,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    CircularProgress,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import WorkIcon from '@mui/icons-material/Work';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import InfoIcon from '@mui/icons-material/Info';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';
import { useNavigate } from 'react-router-dom';
import { getJobCompatibility } from '../../services/aiService';
import type { JobMatchingResponse, JobMatch } from '../../types/ai';
import { usePaymentConfig } from '../../hooks/usePaymentConfig';
import { formatBRL } from '../../utils/currency';

export default function JobCompatibility() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const compatibilityPrice = usePaymentConfig().prices.job_compatibility;
    const [matchingResult, setMatchingResult] = useState<JobMatchingResponse | null>(null);

    // Matching mutation
    const matchingMutation = useMutation({
        mutationFn: () => getJobCompatibility(),
        onSuccess: (data) => {
            setMatchingResult(data);
            queryClient.invalidateQueries({ queryKey: ['wallet-balance'] });
        },
    });

    function handleAnalyze() {
        setMatchingResult(null);
        matchingMutation.mutate();
    }

    function getCompatibilityColor(percentage: number): 'success' | 'warning' | 'error' {
        if (percentage >= 70) return 'success';
        if (percentage >= 40) return 'warning';
        return 'error';
    }

    function getErrorMessage(error: unknown): string {
        const err = error as { response?: { data?: { detail?: string }; status?: number } };
        if (err.response?.status === 402 || err.response?.data?.detail?.includes('token')) {
            return 'Saldo insuficiente. Adicione dinheiro à sua carteira para continuar.';
        }
        if (err.response?.status === 422 || err.response?.data?.detail?.includes('currículo')) {
            return 'Seu currículo precisa ter ao menos 1 experiência profissional ou 1 habilidade cadastrada para utilizar a análise de compatibilidade.';
        }
        if (err.response?.status === 503 || err.response?.data?.detail?.includes('indisponível')) {
            return 'O serviço de IA está temporariamente indisponível. Tente novamente em alguns minutos.';
        }
        return err.response?.data?.detail || 'Erro ao realizar análise. Tente novamente.';
    }

    function getErrorAction(error: unknown) {
        const err = error as { response?: { data?: { detail?: string }; status?: number } };
        if (err.response?.status === 402) {
            return <Button color="inherit" size="small" onClick={() => navigate('/dashboard/wallet')}>
                Adicionar saldo
            </Button>;
        }
        if (err.response?.status === 422) {
            return (
                <Button
                    color="inherit"
                    size="small"
                    onClick={() => navigate('/resume/create')}
                >
                    Completar Currículo
                </Button>
            );
        }
        return undefined;
    }

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Typography variant="h4" component="h1" gutterBottom>
                <SmartToyIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Compatibilidade de Vagas com IA
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                Descubra quais vagas possuem maior aderência ao seu perfil.
                A IA irá comparar seu currículo com as vagas ativas e apresentar as mais compatíveis.
                Você pode se candidatar gratuitamente a quantas vagas quiser; esta busca desconta {formatBRL(compatibilityPrice)} da carteira.
            </Typography>

            {/* Action section */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                    <Button
                        variant="contained"
                        onClick={handleAnalyze}
                        disabled={matchingMutation.isPending}
                        startIcon={matchingMutation.isPending ? <CircularProgress size={20} /> : <SmartToyIcon />}
                        size="large"
                    >
                        {matchingMutation.isPending ? 'Analisando...' : `Buscar por ${formatBRL(compatibilityPrice)}`}
                    </Button>
                    <Typography variant="body2" color="text.secondary">
                        Cada busca desconta {formatBRL(compatibilityPrice)} do saldo da carteira.
                    </Typography>
                </Box>
            </Paper>

            {/* Loading indicator */}
            {matchingMutation.isPending && (
                <Paper sx={{ p: 3, mb: 3 }}>
                    <Typography variant="body1" gutterBottom>
                        Processando análise de compatibilidade...
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        A IA está comparando seu currículo com as vagas ativas disponíveis.
                        Isso pode levar alguns segundos.
                    </Typography>
                    <LinearProgress />
                </Paper>
            )}

            {/* Error handling */}
            {matchingMutation.isError && (
                <Alert
                    severity="error"
                    sx={{ mb: 3 }}
                    action={getErrorAction(matchingMutation.error)}
                >
                    {getErrorMessage(matchingMutation.error)}
                </Alert>
            )}

            {/* No compatible jobs found */}
            {matchingResult && matchingResult.matches.length === 0 && (
                <Alert severity="info" sx={{ mb: 3 }} icon={<InfoIcon />}>
                    <Typography variant="body1" gutterBottom>
                        {matchingResult.message ||
                            'Não foram encontradas vagas com aderência relevante ao seu perfil (todas abaixo de 10%).'}
                    </Typography>
                    <Typography variant="body2">
                        Considere atualizar seu currículo com mais experiências e habilidades.
                    </Typography>
                </Alert>
            )}

            {/* Results */}
            {matchingResult && matchingResult.matches.length > 0 && (
                <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h5">
                            Vagas Compatíveis ({matchingResult.matches.length})
                        </Typography>
                        <Chip label={`Busca paga: ${formatBRL(compatibilityPrice)}`} size="small" variant="outlined" />
                    </Box>

                    {matchingResult.matches
                        .sort((a, b) => b.compatibility_percentage - a.compatibility_percentage)
                        .map((job, index) => (
                            <JobMatchCard
                                key={job.job_id}
                                job={job}
                                rank={index + 1}
                                getCompatibilityColor={getCompatibilityColor}
                            />
                        ))}
                </Box>
            )}
        </Container>
    );
}

interface JobMatchCardProps {
    job: JobMatch;
    rank: number;
    getCompatibilityColor: (percentage: number) => 'success' | 'warning' | 'error';
}

function JobMatchCard({ job, rank, getCompatibilityColor }: JobMatchCardProps) {
    return (
        <Accordion sx={{ mb: 1 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%', pr: 2 }}>
                    <Chip
                        label={`#${rank}`}
                        size="small"
                        color="primary"
                        variant="outlined"
                    />
                    <Box sx={{ flex: 1 }}>
                        <Typography sx={{ fontWeight: 500 }}>
                            {job.job_title}
                        </Typography>
                        {job.company_name && (
                            <Typography variant="body2" color="text.secondary">
                                {job.company_name}
                            </Typography>
                        )}
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 150 }}>
                        <LinearProgress
                            variant="determinate"
                            value={job.compatibility_percentage}
                            color={getCompatibilityColor(job.compatibility_percentage)}
                            sx={{ flex: 1, height: 8, borderRadius: 4 }}
                        />
                        <Chip
                            label={`${job.compatibility_percentage}%`}
                            size="small"
                            color={getCompatibilityColor(job.compatibility_percentage)}
                        />
                    </Box>
                </Box>
            </AccordionSummary>
            <AccordionDetails>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {/* Justifications */}
                    {job.justifications.length > 0 && (
                        <Box>
                            <Typography variant="subtitle2" gutterBottom>
                                <WorkIcon fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
                                Justificativas
                            </Typography>
                            <List dense disablePadding>
                                {job.justifications.map((justification, i) => (
                                    <ListItem key={i} disableGutters>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <InfoIcon fontSize="small" color="info" />
                                        </ListItemIcon>
                                        <ListItemText primary={justification} />
                                    </ListItem>
                                ))}
                            </List>
                        </Box>
                    )}

                    {/* Improvement suggestions */}
                    {job.improvement_suggestions.length > 0 && (
                        <Box>
                            <Typography variant="subtitle2" color="warning.main" gutterBottom>
                                <TipsAndUpdatesIcon fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
                                Sugestões de Melhoria no Currículo
                            </Typography>
                            <List dense disablePadding>
                                {job.improvement_suggestions.map((suggestion, i) => (
                                    <ListItem key={i} disableGutters>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <LightbulbIcon fontSize="small" color="warning" />
                                        </ListItemIcon>
                                        <ListItemText primary={suggestion} />
                                    </ListItem>
                                ))}
                            </List>
                        </Box>
                    )}
                </Box>
            </AccordionDetails>
        </Accordion>
    );
}
