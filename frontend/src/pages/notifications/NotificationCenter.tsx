import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Box,
    Typography,
    Paper,
    List,
    ListItem,
    ListItemText,
    IconButton,
    Button,
    Pagination,
    Chip,
    CircularProgress,
    Alert,
    Tooltip,
} from '@mui/material';
import MarkEmailReadIcon from '@mui/icons-material/MarkEmailRead';
import DoneAllIcon from '@mui/icons-material/DoneAll';
import {
    getNotifications,
    markAsRead,
    markAllAsRead,
} from '../../services/notificationService';

export default function NotificationCenter() {
    const [page, setPage] = useState(1);
    const pageSize = 20;
    const queryClient = useQueryClient();

    const { data, isLoading, isError } = useQuery({
        queryKey: ['notifications', page, pageSize],
        queryFn: () => getNotifications(page, pageSize),
    });

    const markAsReadMutation = useMutation({
        mutationFn: (notificationId: string) => markAsRead(notificationId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
        },
    });

    const markAllMutation = useMutation({
        mutationFn: () => markAllAsRead(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
        },
    });

    const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
        setPage(value);
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    if (isLoading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                <CircularProgress />
            </Box>
        );
    }

    if (isError) {
        return (
            <Box sx={{ p: 3 }}>
                <Alert severity="error">
                    Erro ao carregar notificações. Tente novamente mais tarde.
                </Alert>
            </Box>
        );
    }

    const hasUnread = data?.items.some((n) => !n.is_read);

    return (
        <Box sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h5" component="h1">
                    Central de Notificações
                </Typography>
                {hasUnread && (
                    <Button
                        variant="outlined"
                        startIcon={<DoneAllIcon />}
                        onClick={() => markAllMutation.mutate()}
                        disabled={markAllMutation.isPending}
                        size="small"
                    >
                        Marcar todas como lidas
                    </Button>
                )}
            </Box>

            {!data?.items.length ? (
                <Paper sx={{ p: 4, textAlign: 'center' }}>
                    <Typography color="text.secondary">
                        Nenhuma notificação encontrada.
                    </Typography>
                </Paper>
            ) : (
                <>
                    <List disablePadding>
                        {data.items.map((notification) => (
                            <Paper
                                key={notification.id}
                                elevation={notification.is_read ? 0 : 1}
                                sx={{
                                    mb: 1,
                                    bgcolor: notification.is_read
                                        ? 'background.default'
                                        : 'action.hover',
                                    borderLeft: notification.is_read
                                        ? '3px solid transparent'
                                        : '3px solid',
                                    borderLeftColor: notification.is_read
                                        ? 'transparent'
                                        : 'primary.main',
                                }}
                            >
                                <ListItem
                                    secondaryAction={
                                        !notification.is_read ? (
                                            <Tooltip title="Marcar como lida">
                                                <IconButton
                                                    edge="end"
                                                    onClick={() =>
                                                        markAsReadMutation.mutate(notification.id)
                                                    }
                                                    disabled={markAsReadMutation.isPending}
                                                    size="small"
                                                >
                                                    <MarkEmailReadIcon />
                                                </IconButton>
                                            </Tooltip>
                                        ) : null
                                    }
                                >
                                    <ListItemText
                                        primary={
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <Typography
                                                    variant="subtitle1"
                                                    sx={{
                                                        fontWeight: notification.is_read
                                                            ? 'normal'
                                                            : 'bold',
                                                    }}
                                                >
                                                    {notification.title}
                                                </Typography>
                                                {!notification.is_read && (
                                                    <Chip
                                                        label="Nova"
                                                        size="small"
                                                        color="primary"
                                                        variant="outlined"
                                                    />
                                                )}
                                            </Box>
                                        }
                                        secondary={
                                            <Box component="span">
                                                <Typography
                                                    variant="body2"
                                                    color="text.secondary"
                                                    component="span"
                                                    sx={{ display: 'block', mt: 0.5 }}
                                                >
                                                    {notification.message}
                                                </Typography>
                                                <Typography
                                                    variant="caption"
                                                    color="text.disabled"
                                                    component="span"
                                                    sx={{ display: 'block', mt: 0.5 }}
                                                >
                                                    {formatDate(notification.created_at)}
                                                </Typography>
                                            </Box>
                                        }
                                    />
                                </ListItem>
                            </Paper>
                        ))}
                    </List>

                    {data.total_pages > 1 && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                            <Pagination
                                count={data.total_pages}
                                page={page}
                                onChange={handlePageChange}
                                color="primary"
                            />
                        </Box>
                    )}
                </>
            )}
        </Box>
    );
}
