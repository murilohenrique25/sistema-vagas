/**
 * Employer applications panel - view and manage applications per job.
 * Includes status change interface with valid transitions and a "Recebida" counter
 * that refreshes every 60 seconds.
 * Requirements: 7.1, 7.7
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Box,
    Container,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    Chip,
    Pagination,
    Alert,
    Skeleton,
    Select,
    MenuItem,
    Badge,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    FormControl,
    InputLabel,
    List,
    ListItem,
    ListItemText,
    Divider,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import InboxIcon from '@mui/icons-material/Inbox';
import DescriptionIcon from '@mui/icons-material/Description';
import {
    getJobApplications,
    changeApplicationStatus,
    getCandidateResume,
} from '../../services/applicationService';
import {
    APPLICATION_STATUS_LABELS,
    APPLICATION_STATUS_COLORS,
    VALID_TRANSITIONS,
} from '../../types/application';
import type { Application, ApplicationStatus } from '../../types/application';

function translateProficiency(level: string): string {
    const map: Record<string, string> = {
        beginner: 'Iniciante',
        intermediate: 'Intermediário',
        advanced: 'Avançado',
        expert: 'Especialista',
    };
    return map[level] || level;
}

function translateDegree(degree: string): string {
    const map: Record<string, string> = {
        high_school: 'Ensino Médio',
        technical: 'Técnico',
        bachelor: 'Graduação',
        postgraduate: 'Pós-Graduação',
        master: 'Mestrado',
        doctorate: 'Doutorado',
    };
    return map[degree] || degree;
}

export default function EmployerApplicationsPanel() {
    const { jobId } = useParams<{ jobId: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [page, setPage] = useState(1);
    const [statusDialogOpen, setStatusDialogOpen] = useState(false);
    const [selectedApplication, setSelectedApplication] = useState<Application | null>(null);
    const [newStatus, setNewStatus] = useState<ApplicationStatus | ''>('');
    const [actionError, setActionError] = useState('');
    const [resumeDialogOpen, setResumeDialogOpen] = useState(false);
    const [resumeData, setResumeData] = useState<Record<string, unknown> | null>(null);
    const [resumeLoading, setResumeLoading] = useState(false);

    // Fetch applications for the job
    const { data, isLoading, isError } = useQuery({
        queryKey: ['job-applications', jobId, page],
        queryFn: () => getJobApplications(jobId!, page, 20),
        enabled: !!jobId,
    });

    const statusMutation = useMutation({
        mutationFn: ({
            applicationId,
            status,
        }: {
            applicationId: string;
            status: ApplicationStatus;
        }) => changeApplicationStatus(applicationId, status),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['job-applications', jobId] });
            queryClient.invalidateQueries({ queryKey: ['received-count', jobId] });
            setStatusDialogOpen(false);
            setSelectedApplication(null);
            setNewStatus('');
            setActionError('');
        },
        onError: (error: unknown) => {
            const err = error as { response?: { data?: { detail?: string } } };
            setActionError(
                err.response?.data?.detail || 'Erro ao alterar status da candidatura.'
            );
        },
    });

    function getValidTransitions(status: ApplicationStatus): ApplicationStatus[] {
        return VALID_TRANSITIONS[status] || [];
    }

    function handleStatusChangeClick(application: Application) {
        setSelectedApplication(application);
        setNewStatus('');
        setStatusDialogOpen(true);
        setActionError('');
    }

    function handleStatusChangeConfirm() {
        if (selectedApplication && newStatus) {
            statusMutation.mutate({
                applicationId: selectedApplication.id,
                status: newStatus,
            });
        }
    }

    function formatDate(dateStr: string): string {
        return new Date(dateStr).toLocaleDateString('pt-BR');
    }

    async function handleViewResume(candidateId: string) {
        setResumeLoading(true);
        setResumeDialogOpen(true);
        try {
            const data = await getCandidateResume(candidateId);
            setResumeData(data as Record<string, unknown>);
        } catch {
            setResumeData(null);
            setActionError('Currículo não encontrado para este candidato.');
        } finally {
            setResumeLoading(false);
        }
    }

    if (!jobId) {
        return (
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Alert severity="error">ID da vaga não informado.</Alert>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                <Button
                    startIcon={<ArrowBackIcon />}
                    onClick={() => navigate('/dashboard/employer/jobs')}
                >
                    Voltar
                </Button>
                <Typography variant="h4" component="h1" sx={{ flex: 1 }}>
                    Candidaturas da Vaga
                </Typography>
                <ReceivedCounter jobId={jobId} />
            </Box>

            {actionError && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setActionError('')}>
                    {actionError}
                </Alert>
            )}

            {/* Loading state */}
            {isLoading && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {[1, 2, 3, 4, 5].map((i) => (
                        <Skeleton key={i} variant="rectangular" height={50} sx={{ borderRadius: 1 }} />
                    ))}
                </Box>
            )}

            {/* Error state */}
            {isError && (
                <Alert severity="error">
                    Erro ao carregar candidaturas. Tente novamente mais tarde.
                </Alert>
            )}

            {/* Empty state */}
            {data && data.items.length === 0 && (
                <Alert severity="info">
                    Esta vaga ainda não recebeu candidaturas.
                </Alert>
            )}

            {/* Applications table */}
            {data && data.items.length > 0 && (
                <TableContainer component={Paper} variant="outlined">
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Candidato</TableCell>
                                <TableCell>Status</TableCell>
                                <TableCell>Data da Candidatura</TableCell>
                                <TableCell align="right">Alterar Status</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {data.items.map((app) => (
                                <TableRow key={app.id}>
                                    <TableCell>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            {(app as unknown as Record<string, string>).candidate_name || 'Candidato'}
                                            <Button
                                                size="small"
                                                startIcon={<DescriptionIcon />}
                                                onClick={() => handleViewResume(app.candidate_id)}
                                                sx={{ ml: 1 }}
                                            >
                                                Currículo
                                            </Button>
                                        </Box>
                                    </TableCell>
                                    <TableCell>
                                        <Chip
                                            label={APPLICATION_STATUS_LABELS[app.status]}
                                            color={APPLICATION_STATUS_COLORS[app.status]}
                                            size="small"
                                        />
                                    </TableCell>
                                    <TableCell>{formatDate(app.applied_at)}</TableCell>
                                    <TableCell align="right">
                                        {getValidTransitions(app.status).length > 0 && (
                                            <Button
                                                size="small"
                                                variant="outlined"
                                                onClick={() => handleStatusChangeClick(app)}
                                            >
                                                Alterar Status
                                            </Button>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            )}

            {/* Pagination */}
            {data && data.total_pages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                    <Pagination
                        count={data.total_pages}
                        page={page}
                        onChange={(_, value) => setPage(value)}
                        color="primary"
                    />
                </Box>
            )}

            {/* Status change dialog */}
            <Dialog open={statusDialogOpen} onClose={() => setStatusDialogOpen(false)}>
                <DialogTitle>Alterar Status da Candidatura</DialogTitle>
                <DialogContent>
                    <DialogContentText sx={{ mb: 2 }}>
                        Status atual:{' '}
                        <strong>
                            {selectedApplication
                                ? APPLICATION_STATUS_LABELS[selectedApplication.status]
                                : ''}
                        </strong>
                    </DialogContentText>
                    <FormControl fullWidth>
                        <InputLabel id="new-status-label">Novo Status</InputLabel>
                        <Select
                            labelId="new-status-label"
                            value={newStatus}
                            label="Novo Status"
                            onChange={(e) => setNewStatus(e.target.value as ApplicationStatus)}
                        >
                            {selectedApplication &&
                                getValidTransitions(selectedApplication.status).map(
                                    (status) => (
                                        <MenuItem key={status} value={status}>
                                            {APPLICATION_STATUS_LABELS[status]}
                                        </MenuItem>
                                    )
                                )}
                        </Select>
                    </FormControl>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setStatusDialogOpen(false)}>Cancelar</Button>
                    <Button
                        variant="contained"
                        onClick={handleStatusChangeConfirm}
                        disabled={!newStatus || statusMutation.isPending}
                    >
                        Confirmar
                    </Button>
                </DialogActions>
            </Dialog>
            {/* Resume dialog */}
            <Dialog open={resumeDialogOpen} onClose={() => setResumeDialogOpen(false)} maxWidth="md" fullWidth>
                <DialogTitle>Currículo do Candidato</DialogTitle>
                <DialogContent>
                    {resumeLoading && <Typography>Carregando...</Typography>}
                    {!resumeLoading && !resumeData && (
                        <Alert severity="info">Currículo não encontrado.</Alert>
                    )}
                    {!resumeLoading && resumeData && (
                        <Box>
                            <Typography variant="h6" gutterBottom>
                                {(resumeData as Record<string, unknown>).full_name as string || 'Nome não informado'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                                {(resumeData as Record<string, unknown>).contact_email as string} • {(resumeData as Record<string, unknown>).phone as string} • {(resumeData as Record<string, unknown>).location as string}
                            </Typography>
                            <Divider sx={{ my: 2 }} />

                            {/* Experiences */}
                            {Array.isArray((resumeData as Record<string, unknown>).experiences) && ((resumeData as Record<string, unknown>).experiences as Array<Record<string, string>>).length > 0 && (
                                <>
                                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 600 }}>Experiência Profissional</Typography>
                                    <List dense>
                                        {((resumeData as Record<string, unknown>).experiences as Array<Record<string, string>>).map((exp, i) => (
                                            <ListItem key={i} disableGutters>
                                                <ListItemText
                                                    primary={`${exp.position} - ${exp.company}`}
                                                    secondary={exp.description}
                                                />
                                            </ListItem>
                                        ))}
                                    </List>
                                </>
                            )}

                            {/* Skills */}
                            {Array.isArray((resumeData as Record<string, unknown>).skills) && ((resumeData as Record<string, unknown>).skills as Array<Record<string, string>>).length > 0 && (
                                <>
                                    <Typography variant="subtitle1" gutterBottom sx={{ mt: 2, fontWeight: 600 }}>Habilidades</Typography>
                                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                        {((resumeData as Record<string, unknown>).skills as Array<Record<string, string>>).map((skill, i) => (
                                            <Chip key={i} label={`${skill.name} (${translateProficiency(skill.proficiency)})`} size="small" variant="outlined" />
                                        ))}
                                    </Box>
                                </>
                            )}

                            {/* Education */}
                            {Array.isArray((resumeData as Record<string, unknown>).educations) && ((resumeData as Record<string, unknown>).educations as Array<Record<string, string>>).length > 0 && (
                                <>
                                    <Typography variant="subtitle1" gutterBottom sx={{ mt: 2, fontWeight: 600 }}>Formação</Typography>
                                    <List dense>
                                        {((resumeData as Record<string, unknown>).educations as Array<Record<string, string>>).map((edu, i) => (
                                            <ListItem key={i} disableGutters>
                                                <ListItemText
                                                    primary={`${edu.course} - ${edu.institution}`}
                                                    secondary={translateDegree(edu.degree)}
                                                />
                                            </ListItem>
                                        ))}
                                    </List>
                                </>
                            )}
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setResumeDialogOpen(false)}>Fechar</Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
}

/**
 * Received applications counter component.
 * Refreshes every 60 seconds as per requirement 7.7.
 */
function ReceivedCounter({ jobId }: { jobId: string }) {
    const { data } = useQuery({
        queryKey: ['received-count', jobId],
        queryFn: async () => {
            // Fetch first page with status filter to count received
            const response = await getJobApplications(jobId, 1, 100);
            return response.items.filter((app) => app.status === 'received').length;
        },
        refetchInterval: 60_000, // Refresh every 60 seconds
    });

    const count = data ?? 0;

    return (
        <Badge badgeContent={count} color="primary" max={999}>
            <Chip
                icon={<InboxIcon />}
                label={`Recebidas: ${count}`}
                color={count > 0 ? 'primary' : 'default'}
                variant="outlined"
            />
        </Badge>
    );
}
