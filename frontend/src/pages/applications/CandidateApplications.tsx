/**
 * Candidate applications list page.
 * Shows all applications for the logged-in candidate with status, job title, company, and date.
 * Includes cancel button for applications that are not in a final status.
 * Requirements: 6.2, 6.4
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
} from '@mui/material';
import CancelIcon from '@mui/icons-material/Cancel';
import { getMyApplications, cancelApplication } from '../../services/applicationService';
import {
    APPLICATION_STATUS_LABELS,
    APPLICATION_STATUS_COLORS,
} from '../../types/application';
import type { Application } from '../../types/application';

export default function CandidateApplications() {
    const queryClient = useQueryClient();
    const [page, setPage] = useState(1);
    const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
    const [selectedApplication, setSelectedApplication] = useState<Application | null>(null);
    const [actionError, setActionError] = useState('');

    const { data, isLoading, isError } = useQuery({
        queryKey: ['my-applications', page],
        queryFn: () => getMyApplications(page, 20),
    });

    const cancelMutation = useMutation({
        mutationFn: (applicationId: string) => cancelApplication(applicationId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['my-applications'] });
            setCancelDialogOpen(false);
            setSelectedApplication(null);
            setActionError('');
        },
        onError: (error: unknown) => {
            const err = error as { response?: { data?: { detail?: string } } };
            setActionError(
                err.response?.data?.detail || 'Erro ao cancelar candidatura.'
            );
        },
    });

    function canCancel(application: Application): boolean {
        return !['hired', 'rejected', 'cancelled'].includes(application.status);
    }

    function handleCancelClick(application: Application) {
        setSelectedApplication(application);
        setCancelDialogOpen(true);
    }

    function handleCancelConfirm() {
        if (selectedApplication) {
            cancelMutation.mutate(selectedApplication.id);
        }
    }

    function formatDate(dateStr: string): string {
        return new Date(dateStr).toLocaleDateString('pt-BR');
    }

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Typography variant="h4" component="h1" gutterBottom>
                Minhas Candidaturas
            </Typography>

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
                    Você ainda não possui candidaturas. Explore as vagas disponíveis para se candidatar.
                </Alert>
            )}

            {/* Applications table */}
            {data && data.items.length > 0 && (
                <TableContainer component={Paper} variant="outlined">
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Status</TableCell>
                                <TableCell>Vaga</TableCell>
                                <TableCell>Empresa</TableCell>
                                <TableCell>Data</TableCell>
                                <TableCell align="right">Ações</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {data.items.map((app) => (
                                <TableRow key={app.id}>
                                    <TableCell>
                                        <Chip
                                            label={APPLICATION_STATUS_LABELS[app.status]}
                                            color={APPLICATION_STATUS_COLORS[app.status]}
                                            size="small"
                                        />
                                    </TableCell>
                                    <TableCell>{app.job_title || '—'}</TableCell>
                                    <TableCell>{app.company_name || '—'}</TableCell>
                                    <TableCell>{formatDate(app.applied_at)}</TableCell>
                                    <TableCell align="right">
                                        {canCancel(app) && (
                                            <Button
                                                size="small"
                                                color="error"
                                                startIcon={<CancelIcon />}
                                                onClick={() => handleCancelClick(app)}
                                            >
                                                Cancelar
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

            {/* Cancel confirmation dialog */}
            <Dialog open={cancelDialogOpen} onClose={() => setCancelDialogOpen(false)}>
                <DialogTitle>Cancelar Candidatura</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Tem certeza que deseja cancelar sua candidatura para a vaga{' '}
                        <strong>{selectedApplication?.job_title || ''}</strong>?
                        Esta ação não pode ser desfeita.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCancelDialogOpen(false)}>Voltar</Button>
                    <Button
                        variant="contained"
                        color="error"
                        onClick={handleCancelConfirm}
                        disabled={cancelMutation.isPending}
                    >
                        Confirmar Cancelamento
                    </Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
}
