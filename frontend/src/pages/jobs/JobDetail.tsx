/**
 * Job detail page - displays full information about a single job.
 * Requirements: 2.1, 5.1
 */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
    Box,
    Container,
    Typography,
    Button,
    Chip,
    Divider,
    Paper,
    Skeleton,
    Alert,
    CircularProgress,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import WorkIcon from '@mui/icons-material/Work';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import StarIcon from '@mui/icons-material/Star';
import SendIcon from '@mui/icons-material/Send';
import { getJob, reportJob } from '../../services/jobService';
import { applyToJob, getMyApplications } from '../../services/applicationService';
import { MODALITY_LABELS, CONTRACT_TYPE_LABELS } from '../../types/job';
import { useAuthStore } from '../../stores/authStore';
import { toast } from '../../stores/toastStore';

export default function JobDetail() {
    const { jobId } = useParams<{ jobId: string }>();
    const navigate = useNavigate();
    const { isAuthenticated, user } = useAuthStore();
    const [alreadyApplied, setAlreadyApplied] = useState(false);
    const [reporting, setReporting] = useState(false);

    const { data: job, isLoading, isError } = useQuery({
        queryKey: ['job', jobId],
        queryFn: () => getJob(jobId!),
        enabled: !!jobId,
    });

    // Check if candidate already applied to this job
    const { data: myApplications } = useQuery({
        queryKey: ['my-applications-check', jobId],
        queryFn: () => getMyApplications(1, 100),
        enabled: !!jobId && isAuthenticated && user?.role === 'candidate',
    });

    // Update alreadyApplied based on fetched applications
    const hasApplied = alreadyApplied || (myApplications?.items?.some(
        (app: { job_id: string }) => app.job_id === jobId
    ) ?? false);

    const applyMutation = useMutation({
        mutationFn: () => applyToJob(jobId!),
        onSuccess: () => {
            toast.success('Candidatura enviada com sucesso! Acompanhe o status em "Minhas Candidaturas".');
            setAlreadyApplied(true);
        },
        onError: (err: unknown) => {
            const error = err as { response?: { data?: { detail?: string }; status?: number } };
            const detail = error.response?.data?.detail;
            if (error.response?.status === 409) {
                toast.warning('Você já se candidatou a esta vaga.');
                setAlreadyApplied(true);
            } else if (error.response?.status === 400) {
                toast.error(detail || 'Não foi possível candidatar-se. Verifique se você tem um currículo cadastrado.');
            } else if (error.response?.status === 401) {
                toast.error('Faça login para se candidatar.');
                navigate('/login');
            } else {
                toast.error(detail || 'Erro ao se candidatar. Tente novamente.');
            }
        },
    });

    function handleApply() {
        if (!isAuthenticated) {
            toast.info('Faça login para se candidatar a esta vaga.');
            navigate('/login');
            return;
        }
        if (user?.role === 'employer') {
            toast.warning('Empregadores não podem se candidatar a vagas.');
            return;
        }
        applyMutation.mutate();
    }

    function formatSalary(min: number | string | null, max: number | string | null): string {
        if (!min && !max) return 'A combinar';
        const fmt = (v: number | string) =>
            Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        if (min && max) return `${fmt(min)} - ${fmt(max)}`;
        if (min) return `A partir de ${fmt(min)}`;
        return `Até ${fmt(max!)}`;
    }

    if (isLoading) {
        return (
            <Container maxWidth="md" sx={{ py: 4 }}>
                <Skeleton variant="rectangular" height={40} sx={{ mb: 2 }} />
                <Skeleton variant="rectangular" height={200} />
            </Container>
        );
    }

    if (isError || !job) {
        return (
            <Container maxWidth="md" sx={{ py: 4 }}>
                <Alert severity="error">
                    Vaga não encontrada ou erro ao carregar os dados.
                </Alert>
                <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/jobs')} sx={{ mt: 2 }}>
                    Voltar para vagas
                </Button>
            </Container>
        );
    }

    return (
        <Container maxWidth="md" sx={{ py: 4 }}>
            <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/jobs')} sx={{ mb: 2 }}>
                Voltar para vagas
            </Button>

            <Paper elevation={1} sx={{ p: 4 }}>
                {/* Header */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    {job.is_highlighted && (
                        <Chip icon={<StarIcon />} label="Destaque" color="warning" size="small" />
                    )}
                    <Typography variant="h4" component="h1">
                        {job.title}
                    </Typography>
                </Box>

                {job.company_name && (
                    <Typography variant="h6" color="text.secondary" gutterBottom>
                        {job.company_name}
                    </Typography>
                )}

                {/* Tags */}
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', my: 2 }}>
                    {job.location && (
                        <Chip icon={<LocationOnIcon />} label={job.location} variant="outlined" />
                    )}
                    <Chip icon={<WorkIcon />} label={MODALITY_LABELS[job.modality]} variant="outlined" />
                    <Chip label={CONTRACT_TYPE_LABELS[job.contract_type]} variant="outlined" />
                    <Chip label={formatSalary(job.salary_min, job.salary_max)} color="primary" variant="outlined" />
                    {job.deadline && (
                        <Chip
                            icon={<CalendarTodayIcon />}
                            label={`Prazo: ${new Date(job.deadline).toLocaleDateString('pt-BR')}`}
                            variant="outlined"
                        />
                    )}
                </Box>

                <Divider sx={{ my: 3 }} />

                {/* Responsibilities */}
                {job.responsibilities && (
                    <Box sx={{ mb: 3 }}>
                        <Typography variant="h6" gutterBottom>
                            Responsabilidades
                        </Typography>
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
                            {job.responsibilities}
                        </Typography>
                    </Box>
                )}

                {/* Required skills */}
                {job.required_skills && (
                    <Box sx={{ mb: 3 }}>
                        <Typography variant="h6" gutterBottom>
                            Requisitos Obrigatórios
                        </Typography>
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
                            {job.required_skills}
                        </Typography>
                    </Box>
                )}

                {/* Optional skills */}
                {job.optional_skills && (
                    <Box sx={{ mb: 3 }}>
                        <Typography variant="h6" gutterBottom>
                            Requisitos Desejáveis
                        </Typography>
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
                            {job.optional_skills}
                        </Typography>
                    </Box>
                )}

                {/* Benefits */}
                {job.benefits && (
                    <Box sx={{ mb: 3 }}>
                        <Typography variant="h6" gutterBottom>
                            Benefícios
                        </Typography>
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
                            {job.benefits}
                        </Typography>
                    </Box>
                )}

                <Divider sx={{ my: 3 }} />

                {/* Footer info */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="caption" color="text.secondary">
                        Publicada em: {new Date(job.created_at).toLocaleDateString('pt-BR')}
                    </Typography>
                    <Button
                        variant="contained"
                        size="large"
                        onClick={handleApply}
                        disabled={applyMutation.isPending || hasApplied}
                        startIcon={applyMutation.isPending ? <CircularProgress size={18} /> : hasApplied ? undefined : <SendIcon />}
                        color={hasApplied ? 'success' : 'primary'}
                    >
                        {applyMutation.isPending ? 'Candidatando...' : hasApplied ? '✓ Candidatado' : 'Candidatar-se'}
                    </Button>
                    {isAuthenticated && user?.role !== 'employer' && <Button color="error" variant="text" disabled={reporting} onClick={async()=>{const details=window.prompt('Descreva o motivo da denúncia:');if(!details)return;try{setReporting(true);await reportJob(job.id,'other',details);toast.success('Denúncia enviada para análise.')}catch{toast.error('Não foi possível enviar a denúncia.')}finally{setReporting(false)}}}>Denunciar vaga</Button>}
                </Box>
            </Paper>
        </Container>
    );
}
