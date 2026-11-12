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
    CircularProgress,
    Alert,
} from '@mui/material';
import { getAdminAuditLogs } from '../../services/adminService';

export default function AdminAuditLog() {
    const [page, setPage] = useState(0);
    const [pageSize, setPageSize] = useState(50);

    const { data, isLoading, error } = useQuery({
        queryKey: ['admin', 'audit-logs', page, pageSize],
        queryFn: () => getAdminAuditLogs(page + 1, pageSize),
    });

    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 'bold' }}>
                Log de Auditoria
            </Typography>

            {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    Erro ao carregar logs de auditoria.
                </Alert>
            )}

            {isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress />
                </Box>
            ) : (
                <Paper>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Data</TableCell>
                                    <TableCell>Admin</TableCell>
                                    <TableCell>Ação</TableCell>
                                    <TableCell>Entidade</TableCell>
                                    <TableCell>ID Entidade</TableCell>
                                    <TableCell>Detalhes</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {data?.items.map((log) => (
                                    <TableRow key={log.id}>
                                        <TableCell>
                                            {new Date(log.created_at).toLocaleString('pt-BR')}
                                        </TableCell>
                                        <TableCell>{log.admin_name}</TableCell>
                                        <TableCell>{log.action}</TableCell>
                                        <TableCell>{log.entity_type}</TableCell>
                                        <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                            {log.entity_id}
                                        </TableCell>
                                        <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {log.details}
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
                            setPageSize(Math.min(parseInt(e.target.value, 10), 100));
                            setPage(0);
                        }}
                        rowsPerPageOptions={[25, 50, 100]}
                        labelRowsPerPage="Itens por página"
                    />
                </Paper>
            )}
        </Box>
    );
}
