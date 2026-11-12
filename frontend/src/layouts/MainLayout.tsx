import { Link as RouterLink, Outlet, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Box, Chip, Tooltip, IconButton, Badge, Avatar, Button, Stack } from '@mui/material';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import NotificationsIcon from '@mui/icons-material/Notifications';
import LogoutIcon from '@mui/icons-material/Logout';
import HomeIcon from '@mui/icons-material/Home';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';
import { getWalletBalance } from '../services/walletService';
import { getUnreadCount } from '../services/notificationService';
import { formatBRL } from '../utils/currency';
import SeoManager from '../components/SeoManager';

function TokenBalanceDisplay() {
    const navigate = useNavigate();
    const { isAuthenticated } = useAuthStore();
    const { data } = useQuery({ queryKey: ['wallet-balance'], queryFn: getWalletBalance, enabled: isAuthenticated });
    if (!isAuthenticated || !data) return null;

    return (
        <Tooltip title="Saldo da carteira">
            <Chip
                icon={<AccountBalanceWalletIcon />}
                label={formatBRL(data.balance)}
                color="default"
                variant="outlined"
                onClick={() => navigate('/dashboard/wallet')}
                sx={{
                    color: 'white',
                    borderColor: 'rgba(255,255,255,0.4)',
                    cursor: 'pointer',
                    backdropFilter: 'blur(4px)',
                    backgroundColor: 'rgba(255,255,255,0.08)',
                    '& .MuiChip-icon': { color: 'rgba(255,255,255,0.9)' },
                    '&:hover': {
                        borderColor: 'white',
                        bgcolor: 'rgba(255,255,255,0.15)',
                    },
                }}
            />
        </Tooltip>
    );
}

function NotificationBell() {
    const navigate = useNavigate();
    const { isAuthenticated } = useAuthStore();

    const { data } = useQuery({
        queryKey: ['notifications-unread-count'],
        queryFn: getUnreadCount,
        enabled: isAuthenticated,
        refetchInterval: 60000,
    });

    if (!isAuthenticated) return null;

    const unreadCount = data?.unread_count ?? 0;

    return (
        <Tooltip title="Notificações">
            <IconButton
                color="inherit"
                onClick={() => navigate('/dashboard/notifications')}
                sx={{ mr: 1 }}
            >
                <Badge badgeContent={unreadCount} color="error" max={99}>
                    <NotificationsIcon />
                </Badge>
            </IconButton>
        </Tooltip>
    );
}

export default function MainLayout() {
    const navigate = useNavigate();
    const { isAuthenticated, logout, user } = useAuthStore();

    function handleLogout() {
        logout();
        navigate('/login');
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <SeoManager />
            <AppBar position="sticky" elevation={0}>
                <Toolbar
                    sx={{
                        px: { xs: 2, sm: 3, md: 4 },
                        height: 64,
                        minHeight: '64px !important',
                    }}
                >
                    <Typography
                        variant="h6"
                        component="div"
                        sx={{
                            flexGrow: 1,
                            fontSize: { xs: '1rem', sm: '1.25rem' },
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            cursor: 'pointer',
                            fontWeight: 700,
                            letterSpacing: '-0.02em',
                        }}
                        onClick={() => navigate(isAuthenticated ? '/dashboard' : '/')}
                    >
                        <Box component="img" src="/brand-icon.svg" alt="" sx={{ width: 34, height: 34, mr: 1.2, verticalAlign: 'middle', borderRadius: 1.5 }} />
                        <Box component="span" sx={{ verticalAlign: 'middle' }}>Recruta <Box component="span" sx={{ color: 'secondary.light' }}>IA</Box></Box>
                    </Typography>
                    {!isAuthenticated && (
                        <Stack direction="row" spacing={1}>
                            <Button color="inherit" onClick={() => navigate('/jobs')} sx={{ display: { xs: 'none', sm: 'inline-flex' } }}>Vagas</Button>
                            <Button color="inherit" onClick={() => navigate('/login')}>Entrar</Button>
                            <Button
                                variant="contained"
                                onClick={() => navigate('/register')}
                                sx={{ bgcolor: 'white', color: 'primary.dark', px: { xs: 1.5, sm: 2.5 }, '&:hover': { bgcolor: '#eef3ff' } }}
                            >
                                Criar conta
                            </Button>
                        </Stack>
                    )}
                    {isAuthenticated && (
                        <Tooltip title="Dashboard">
                            <IconButton color="inherit" onClick={() => navigate('/dashboard')} sx={{ mr: 0.5 }}>
                                <HomeIcon />
                            </IconButton>
                        </Tooltip>
                    )}
                    <NotificationBell />
                    <TokenBalanceDisplay />
                    {isAuthenticated && user && (
                        <Box sx={{ display: 'flex', alignItems: 'center', ml: 2, gap: 1 }}>
                            <Avatar
                                sx={{
                                    width: 32,
                                    height: 32,
                                    bgcolor: 'rgba(255,255,255,0.2)',
                                    fontSize: '0.875rem',
                                    fontWeight: 600,
                                }}
                            >
                                {user.name?.charAt(0)?.toUpperCase() || 'U'}
                            </Avatar>
                            <Typography
                                variant="body2"
                                sx={{
                                    color: 'rgba(255,255,255,0.9)',
                                    display: { xs: 'none', sm: 'block' },
                                    fontWeight: 500,
                                    maxWidth: 120,
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                }}
                            >
                                {user.name}
                            </Typography>
                        </Box>
                    )}
                    {isAuthenticated && (
                        <Tooltip title="Sair">
                            <IconButton color="inherit" onClick={handleLogout} sx={{ ml: 1 }}>
                                <LogoutIcon />
                            </IconButton>
                        </Tooltip>
                    )}
                </Toolbar>
            </AppBar>
            <Box
                component="main"
                sx={{
                    flex: 1,
                    minHeight: 'calc(100vh - 64px)',
                }}
            >
                <Outlet />
            </Box>
            <Box component="footer" sx={{ py: 2.5, px: 3, borderTop: '1px solid', borderColor: 'divider', bgcolor: '#fff' }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'center', alignItems: 'center' }}>
                    <Typography variant="caption" color="text.secondary">© 2026 Recruta IA · Sienix Sistemas</Typography>
                    <Button size="small" component={RouterLink} to="/terms">Termos de Uso</Button>
                    <Button size="small" component={RouterLink} to="/privacy">Privacidade</Button>
                    <Button size="small" component={RouterLink} to="/cookies">Cookies</Button>
                </Stack>
            </Box>
        </Box>
    );
}
