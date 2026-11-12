/**
 * Employer job management panel - lists, manages, and controls employer's jobs.
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Box,
    Container,
    Typography,
    Button,
    Card,
    CardContent,
    CardActions,
    Chip,
    Pagination,
    Alert,
    Skeleton,
    IconButton,
    Tooltip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import BlockIcon from '@mui/icons-material/Block';
import ScheduleIcon from '@mui/icons-material/Schedule';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PeopleIcon from '@mui/icons-material/People';
import {
    getEmployerJobs,
    duplicateJob,
    changeJobStatus,
    extendJobDeadline,
} from '../../services/jobService';
import { JOB_STATUS_LABELS, MODALITY_LABELS, CONTRACT_TYPE_LABELS } from '../../types/job';
import type { JobStatus } from '../../types/job';

const STATUS_COLORS: Record<JobStatus, 'success' | 'error' | 'default' | 'warning'> = {
    active: 'success',
    inactive: 'error',
    closed: 'default',
    draft: 'warning',
};

export default function EmployerJobsPanel() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [page, setPage] = useState(1);
    const [extendDialogOpen, setExtendDialogOpen] = useState(false);
    const [extendJobId, setExtendJobId] = useState<string | null>(null);
    const [extendDate, setExtendDate] = useState('');
    const [actionError, setActionError] = useState('');

    const { data, isLoading, isError } = useQuery({
        queryKey: ['employer-jobs', page],
        queryFn: () => getEmployerJobs({ page, page_size: 20 }),
    });

    const duplicateMutation = useMutation({
        mutationFn: (jobId: string) => duplicateJob(jobId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['employer-jobs'] });
            setActionError('');
        },
        onError: (error: unknown) => {
            const err = error as { response?: { data?: { detail?: string } } };
            setActionError(err.response?.data?.detail || 'Erro ao duplicar vaga.');
        },
    });

    const statusMutation = useMutation({
        mutationFn: ({ jobId, status }: { jobId: string; status: JobStatus }) =>
            changeJobStatus(jobId, status),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['employer-jobs'] });
            setActionError('');
        },
        onError: (error: unknown) => {
            const err = error as { response?: { data?: { detail?: string } } };
            setActionError(err.response?.data?.detail || 'Erro ao alterar status.');
        },
    });

    const extendMutation = useMutation({
        mutationFn: ({ jobId, newDate }: { jobId: string; newDate: string }) =>
            extendJobDeadline(jobId, newDate),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['employer-jobs'] });
            setExtendDialogOpen(false);
            setExtendJobId(null);
            setExtendDate('');
            setActionError('');
        },
        onError: (error: unknown) => {
            const err = error as { response?: { data?: { detail?: string } } };
            setActionError(err.response?.data?.detail || 'Erro ao prorrogar prazo.');
        },
    });

    function handleExtendOpen(jobId: string) {
        setExtendJobId(jobId);
        setExtendDialogOpen(true);
    }

    function handleExtendSubmit() {
        if (extendJobId && extendDate) {
            extendMutation.mutate({ jobId: extendJobId, newDate: extendDate });
        }
    }

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4" component="h1">
                    Minhas Vagas
                </Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => navigate('/dashboard/employer/jobs/new')}
                >
                    Nova Vaga
                </Button>
            </Box>

            {actionError && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setActionError('')}>
                    {actionError}
                </Alert>
            )}

            {/* Loading state */}
            {isLoading && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} variant="rectangular" height={120} sx={{ borderRadius: 1 }} />
                    ))}
                </Box>
            )}

            {/* Error state */}
            {isError && (
                <Alert severity="error">
                    Erro ao carregar vagas. Tente novamente mais tarde.
                </Alert>
            )}

            {/* Empty state */}
            {data && data.items.length === 0 && (
                <Alert severity="info">
                    Você ainda não possui vagas cadastradas. Clique em &quot;Nova Vaga&quot; para começar.
                </Alert>
            )}

            {/* Job cards */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {data?.items.map((job) => (
                    <Card key={job.id} variant="outlined">
                        <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <Box>
                                    <Typography variant="h6" component="h2">
                                        {job.title}
                                    </Typography>
                                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                                        <Chip
                                            label={JOB_STATUS_LABELS[job.status]}
                                            color={STATUS_COLORS[job.status]}
                                            size="small"
                                        />
                                        <Chip label={MODALITY_LABELS[job.modality]} size="small" variant="outlined" />
                                        <Chip label={CONTRACT_TYPE_LABELS[job.contract_type]} size="small" variant="outlined" />
                                        {job.location && <Chip label={job.location} size="small" variant="outlined" />}
                                    </Box>
                                </Box>
                                <Box>
                                    {job.deadline && (
                                        <Typography variant="caption" color="text.secondary">
                                            Prazo: {new Date(job.deadline).toLocaleDateString('pt-BR')}
                                        </Typography>
                                    )}
                                </Box>
                            </Box>
                        </CardContent>
                        <CardActions sx={{ justifyContent: 'flex-end' }}>
                            <Button
                                size="small"
                                startIcon={<PeopleIcon />}
                                onClick={() => navigate(`/dashboard/employer/jobs/${job.id}/applications`)}
                            >
                                Candidaturas
                            </Button>
                            <Tooltip title="Editar">
                                <IconButton
                                    size="small"
                                    onClick={() => navigate(`/dashboard/employer/jobs/${job.id}/edit`)}
                                >
                                    <EditIcon />
                                </IconButton>
                            </Tooltip>
                            <Tooltip title="Duplicar">
                                <IconButton
                                    size="small"
                                    onClick={() => duplicateMutation.mutate(job.id)}
                                    disabled={duplicateMutation.isPending}
                                >
                                    <ContentCopyIcon />
                                </IconButton>
                            </Tooltip>
                            {job.status === 'active' && (
                                <>
                                    <Tooltip title="Inativar">
                                        <IconButton
                                            size="small"
                                            color="error"
                                            onClick={() =>
                                                statusMutation.mutate({ jobId: job.id, status: 'inactive' })
                                            }
                                            disabled={statusMutation.isPending}
                                        >
                                            <BlockIcon />
                                        </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Prorrogar prazo">
                                        <IconButton
                                            size="small"
                                            color="primary"
                                            onClick={() => handleExtendOpen(job.id)}
                                        >
                                            <ScheduleIcon />
                                        </IconButton>
                                    </Tooltip>
                                </>
                            )}
                            {(job.status === 'draft' || job.status === 'inactive') && (
                                <Tooltip title="Ativar">
                                    <IconButton
                                        size="small"
                                        color="success"
                                        onClick={() =>
                                            statusMutation.mutate({ jobId: job.id, status: 'active' })
                                        }
                                        disabled={statusMutation.isPending}
                                    >
                                        <PlayArrowIcon />
                                    </IconButton>
                                </Tooltip>
                            )}
                        </CardActions>
                    </Card>
                ))}
            </Box>

            {/* Pagination */}
            {data && data.total_pages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                    <Pagination
                        count={data.total_pages}
                        page={page}
                        onChange={(_, value) => setPage(value)}
                        color="primary"
                    />
                </Box>
            )}

            {/* Extend deadline dialog */}
            <Dialog open={extendDialogOpen} onClose={() => setExtendDialogOpen(false)}>
                <DialogTitle>Prorrogar Prazo</DialogTitle>
                <DialogContent>
                    <TextField
                        fullWidth
                        label="Nova data de encerramento"
                        type="date"
                        value={extendDate}
                        onChange={(e) => setExtendDate(e.target.value)}
                        slotProps={{ inputLabel: { shrink: true } }}
                        helperText="Entre 1 e 180 dias no futuro"
                        sx={{ mt: 1 }}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setExtendDialogOpen(false)}>Cancelar</Button>
                    <Button
                        variant="contained"
                        onClick={handleExtendSubmit}
                        disabled={!extendDate || extendMutation.isPending}
                    >
                        Confirmar
                    </Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
}
