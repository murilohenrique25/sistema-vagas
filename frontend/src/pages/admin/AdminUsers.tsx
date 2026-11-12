import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
    Button,
    Chip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    CircularProgress,
    Alert,
    IconButton,
    Tooltip,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import BlockIcon from '@mui/icons-material/Block';
import DownloadIcon from '@mui/icons-material/Download';
import {
    getAdminUsers,
    updateAdminUser,
    activateUser,
    deactivateUser,
    exportCsv,
} from '../../services/adminService';
import type { AdminUser, AdminUserUpdate } from '../../types/admin';

export default function AdminUsers() {
    const queryClient = useQueryClient();
    const [page, setPage] = useState(0);
    const [pageSize, setPageSize] = useState(20);
    const [editUser, setEditUser] = useState<AdminUser | null>(null);
    const [editForm, setEditForm] = useState<AdminUserUpdate>({});

    const { data, isLoading, error } = useQuery({
        queryKey: ['admin', 'users', page, pageSize],
        queryFn: () => getAdminUsers(page + 1, pageSize),
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: AdminUserUpdate }) =>
            updateAdminUser(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
            setEditUser(null);
        },
    });

    const activateMutation = useMutation({
        mutationFn: activateUser,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
    });

    const deactivateMutation = useMutation({
        mutationFn: deactivateUser,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
    });

    const openEdit = (user: AdminUser) => {
        setEditUser(user);
        setEditForm({ name: user.name, email: user.email, role: user.role });
    };

    const statusColor = (isActive: boolean) => {
        return isActive ? 'success' : 'default';
    };

    const translateRole = (role: string) => {
        const map: Record<string, string> = {
            candidate: 'Candidato',
            employer: 'Empregador',
            admin: 'Administrador',
        };
        return map[role] || role;
    };

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                    Gestão de Usuários
                </Typography>
                <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={() => exportCsv('users')}
                >
                    Exportar CSV
                </Button>
            </Box>

            {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    Erro ao carregar usuários.
                </Alert>
            )}

            {isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress />
                </Box>
            ) : (
                <Paper>
                    <TableContainer>
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableCell>Nome</TableCell>
                                    <TableCell>Email</TableCell>
                                    <TableCell>Perfil</TableCell>
                                    <TableCell>Status</TableCell>
                                    <TableCell>Criado em</TableCell>
                                    <TableCell align="right">Ações</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {data?.items.map((user) => (
                                    <TableRow key={user.id}>
                                        <TableCell>{user.name}</TableCell>
                                        <TableCell>{user.email}</TableCell>
                                        <TableCell>
                                            <Chip label={translateRole(user.role)} size="small" />
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={user.is_active ? 'Ativo' : 'Inativo'}
                                                size="small"
                                                color={statusColor(user.is_active) as 'success' | 'default'}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            {new Date(user.created_at).toLocaleDateString('pt-BR')}
                                        </TableCell>
                                        <TableCell align="right">
                                            <Tooltip title="Editar">
                                                <IconButton
                                                    size="small"
                                                    onClick={() => openEdit(user)}
                                                >
                                                    <EditIcon fontSize="small" />
                                                </IconButton>
                                            </Tooltip>
                                            {user.is_active ? (
                                                <Tooltip title="Desativar">
                                                    <IconButton
                                                        size="small"
                                                        color="error"
                                                        onClick={() => deactivateMutation.mutate(user.id)}
                                                    >
                                                        <BlockIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                            ) : (
                                                <Tooltip title="Ativar">
                                                    <IconButton
                                                        size="small"
                                                        color="success"
                                                        onClick={() => activateMutation.mutate(user.id)}
                                                    >
                                                        <CheckCircleIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    <TablePagination
                        component="div"
                        count={data?.total ?? 0}
                        page={page}
                        onPageChange={(_, p) => setPage(p)}
                        rowsPerPage={pageSize}
                        onRowsPerPageChange={(e) => {
                            setPageSize(parseInt(e.target.value, 10));
                            setPage(0);
                        }}
                        labelRowsPerPage="Itens por página"
                    />
                </Paper>
            )}

            {/* Edit Dialog */}
            <Dialog open={!!editUser} onClose={() => setEditUser(null)} maxWidth="sm" fullWidth>
                <DialogTitle>Editar Usuário</DialogTitle>
                <DialogContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                        <TextField
                            label="Nome"
                            value={editForm.name ?? ''}
                            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                            fullWidth
                        />
                        <TextField
                            label="Email"
                            value={editForm.email ?? ''}
                            onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                            fullWidth
                        />
                        <FormControl fullWidth>
                            <InputLabel>Perfil</InputLabel>
                            <Select
                                value={editForm.role ?? ''}
                                label="Perfil"
                                onChange={(e) =>
                                    setEditForm({ ...editForm, role: e.target.value as AdminUserUpdate['role'] })
                                }
                            >
                                <MenuItem value="candidate">Candidato</MenuItem>
                                <MenuItem value="employer">Empregador</MenuItem>
                                <MenuItem value="admin">Admin</MenuItem>
                            </Select>
                        </FormControl>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setEditUser(null)}>Cancelar</Button>
                    <Button
                        variant="contained"
                        onClick={() => {
                            if (editUser) {
                                updateMutation.mutate({ id: editUser.id, data: editForm });
                            }
                        }}
                        disabled={updateMutation.isPending}
                    >
                        Salvar
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
