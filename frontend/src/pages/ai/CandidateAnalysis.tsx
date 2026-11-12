/**
 * Employer page: AI Candidate Analysis.
 * Allows employer to select a job and trigger AI analysis of candidates.
 * Displays ranked results with scores, strengths, concerns, and justifications.
 * Requirements: 8.1, 8.2
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    CircularProgress,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { useNavigate } from 'react-router-dom';
import { getEmployerJobs } from '../../services/jobService';
import { analyzeCandidates } from '../../services/aiService';
import type { CandidateAnalysisResponse, CandidateScore } from '../../types/ai';
import type { Job } from '../../types/job';
import { usePaymentConfig } from '../../hooks/usePaymentConfig';
import { formatBRL } from '../../utils/currency';

export default function CandidateAnalysis() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const analysisPrice = usePaymentConfig().prices.resume_analysis;
    const [selectedJobId, setSelectedJobId] = useState<string>('');
    const [analysisResult, setAnalysisResult] = useState<CandidateAnalysisResponse | null>(null);

    // Fetch employer's active jobs
    const { data: jobsData, isLoading: jobsLoading } = useQuery({
        queryKey: ['employer-jobs-active'],
        queryFn: () => getEmployerJobs({ page_size: 100 }),
    });

    const activeJobs: Job[] = (jobsData?.items ?? []).filter((j) => j.status === 'active');

    // Analysis mutation
    const analysisMutation = useMutation({
        mutationFn: (jobId: string) => analyzeCandidates(jobId),
        onSuccess: (data) => {
            setAnalysisResult(data);
            queryClient.invalidateQueries({ queryKey: ['wallet-balance'] });
        },
    });

    function handleAnalyze() {
        if (!selectedJobId) return;
        setAnalysisResult(null);
        analysisMutation.mutate(selectedJobId);
    }

    function getScoreColor(score: number): 'success' | 'warning' | 'error' {
        if (score >= 70) return 'success';
        if (score >= 40) return 'warning';
        return 'error';
    }

    function getErrorMessage(error: unknown): string {
        const err = error as { response?: { data?: { detail?: string }; status?: number } };
        if (err.response?.status === 402 || err.response?.data?.detail?.includes('token')) {
            return 'Saldo insuficiente. Adicione dinheiro à sua carteira para continuar.';
        }
        if (err.response?.status === 503 || err.response?.data?.detail?.includes('indisponível')) {
            return 'O serviço de IA está temporariamente indisponível. Tente novamente em alguns minutos.';
        }
        return err.response?.data?.detail || 'Erro ao realizar análise. Tente novamente.';
    }

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Typography variant="h4" component="h1" gutterBottom>
                <SmartToyIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Análise de Candidatos com IA
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                Selecione uma vaga ativa para analisar os candidatos com inteligência artificial.
                A IA irá classificar cada candidato com base na aderência ao perfil da vaga.
                Cada solicitação desconta {formatBRL(analysisPrice)} do saldo da sua carteira.
            </Typography>

            {/* Job selection */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                    <FormControl sx={{ minWidth: 300, flex: 1 }}>
                        <InputLabel id="job-select-label">Selecionar Vaga</InputLabel>
                        <Select
                            labelId="job-select-label"
                            value={selectedJobId}
                            label="Selecionar Vaga"
                            onChange={(e) => setSelectedJobId(e.target.value)}
                            disabled={jobsLoading || analysisMutation.isPending}
                        >
                            {activeJobs.map((job) => (
                                <MenuItem key={job.id} value={job.id}>
                                    {job.title}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <Button
                        variant="contained"
                        onClick={handleAnalyze}
                        disabled={!selectedJobId || analysisMutation.isPending}
                        startIcon={analysisMutation.isPending ? <CircularProgress size={20} /> : <SmartToyIcon />}
                    >
                        {analysisMutation.isPending ? 'Analisando...' : `Analisar por ${formatBRL(analysisPrice)}`}
                    </Button>
                </Box>

                {activeJobs.length === 0 && !jobsLoading && (
                    <Alert severity="info" sx={{ mt: 2 }}>
                        Você não possui vagas ativas. Crie uma vaga para utilizar a análise de IA.
                    </Alert>
                )}
            </Paper>

            {/* Loading indicator */}
            {analysisMutation.isPending && (
                <Paper sx={{ p: 3, mb: 3 }}>
                    <Typography variant="body1" gutterBottom>
                        Processando análise de candidatos...
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        A IA está comparando os currículos dos candidatos com os requisitos da vaga.
                        Isso pode levar alguns segundos.
                    </Typography>
                    <LinearProgress />
                </Paper>
            )}

            {/* Error handling */}
            {analysisMutation.isError && (
                <Alert
                    severity="error"
                    sx={{ mb: 3 }}
                    action={
                        analysisMutation.error &&
                            (analysisMutation.error as { response?: { status?: number } }).response?.status === 402 ? (
                            <Button
                                color="inherit"
                                size="small"
                                onClick={() => navigate('/dashboard/wallet')}
                            >
                                Adicionar saldo
                            </Button>
                        ) : undefined
                    }
                >
                    {getErrorMessage(analysisMutation.error)}
                </Alert>
            )}

            {/* Results */}
            {analysisResult && analysisResult.results.length > 0 && (
                <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h5">
                            Ranking de Candidatos ({analysisResult.results.length})
                        </Typography>
                        <Chip label={`Análise paga: ${formatBRL(analysisPrice)}`} size="small" variant="outlined" />
                    </Box>

                    {analysisResult.results
                        .sort((a, b) => b.score - a.score)
                        .map((candidate, index) => (
                            <CandidateResultCard
                                key={candidate.candidate_id}
                                candidate={candidate}
                                rank={index + 1}
                                getScoreColor={getScoreColor}
                            />
                        ))}
                </Box>
            )}

            {analysisResult && analysisResult.results.length === 0 && (
                <Alert severity="info">
                    Nenhum candidato encontrado para análise nesta vaga.
                </Alert>
            )}
        </Container>
    );
}

interface CandidateResultCardProps {
    candidate: CandidateScore;
    rank: number;
    getScoreColor: (score: number) => 'success' | 'warning' | 'error';
}

function CandidateResultCard({ candidate, rank, getScoreColor }: CandidateResultCardProps) {
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
                    <Typography sx={{ flex: 1, fontWeight: 500 }}>
                        {candidate.candidate_name || `Candidato ${candidate.candidate_id.slice(0, 8)}`}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 150 }}>
                        <LinearProgress
                            variant="determinate"
                            value={candidate.score}
                            color={getScoreColor(candidate.score)}
                            sx={{ flex: 1, height: 8, borderRadius: 4 }}
                        />
                        <Chip
                            label={`${candidate.score}%`}
                            size="small"
                            color={getScoreColor(candidate.score)}
                        />
                    </Box>
                </Box>
            </AccordionSummary>
            <AccordionDetails>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {/* Strengths */}
                    <Box>
                        <Typography variant="subtitle2" color="success.main" gutterBottom>
                            Pontos Fortes
                        </Typography>
                        <List dense disablePadding>
                            {candidate.strengths.map((strength, i) => (
                                <ListItem key={i} disableGutters>
                                    <ListItemIcon sx={{ minWidth: 32 }}>
                                        <CheckCircleIcon fontSize="small" color="success" />
                                    </ListItemIcon>
                                    <ListItemText primary={strength} />
                                </ListItem>
                            ))}
                        </List>
                    </Box>

                    {/* Concerns */}
                    <Box>
                        <Typography variant="subtitle2" color="warning.main" gutterBottom>
                            Pontos de Atenção
                        </Typography>
                        <List dense disablePadding>
                            {candidate.concerns.map((concern, i) => (
                                <ListItem key={i} disableGutters>
                                    <ListItemIcon sx={{ minWidth: 32 }}>
                                        <WarningIcon fontSize="small" color="warning" />
                                    </ListItemIcon>
                                    <ListItemText primary={concern} />
                                </ListItem>
                            ))}
                        </List>
                    </Box>

                    {/* Justification */}
                    <Box>
                        <Typography variant="subtitle2" gutterBottom>
                            Justificativa
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            {candidate.justification}
                        </Typography>
                    </Box>
                </Box>
            </AccordionDetails>
        </Accordion>
    );
}
