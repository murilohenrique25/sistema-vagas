import { Box, Typography, Container, Grid, Card, CardContent, CardActions, Button, Chip } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import WorkIcon from '@mui/icons-material/Work';
import DescriptionIcon from '@mui/icons-material/Description';
import AssignmentIcon from '@mui/icons-material/Assignment';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import TokenIcon from '@mui/icons-material/Token';
import NotificationsIcon from '@mui/icons-material/Notifications';
import BusinessIcon from '@mui/icons-material/Business';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import PeopleIcon from '@mui/icons-material/People';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import PaymentIcon from '@mui/icons-material/Payment';
import StorefrontIcon from '@mui/icons-material/Storefront';
import ManageAccountsIcon from '@mui/icons-material/ManageAccounts';
import { usePaymentConfig } from '../hooks/usePaymentConfig';
import { formatBRL } from '../utils/currency';

interface DashboardCard {
    title: string;
    description: string;
    icon: React.ReactNode;
    path: string;
    color: string;
    gradient: string;
}

const candidateCards: DashboardCard[] = [
    {
        title: 'Buscar Vagas',
        description: 'Explore vagas ativas e candidate-se às que combinam com seu perfil.',
        icon: <WorkIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/jobs',
        color: '#1976d2',
        gradient: 'linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)',
    },
    {
        title: 'Meu Currículo',
        description: 'Crie ou edite seu currículo para se destacar nas candidaturas.',
        icon: <DescriptionIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/resume/create',
        color: '#2e7d32',
        gradient: 'linear-gradient(135deg, #2e7d32 0%, #66bb6a 100%)',
    },
    {
        title: 'Minhas Candidaturas',
        description: 'Acompanhe o status de todas as suas candidaturas.',
        icon: <AssignmentIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/candidate/applications',
        color: '#ed6c02',
        gradient: 'linear-gradient(135deg, #ed6c02 0%, #ffb74d 100%)',
    },
    {
        title: 'Compatibilidade IA',
        description: 'Descubra quais vagas combinam mais com seu perfil usando IA.',
        icon: <SmartToyIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/candidate/ai/compatibility',
        color: '#9c27b0',
        gradient: 'linear-gradient(135deg, #9c27b0 0%, #ce93d8 100%)',
    },
    {
        title: 'Minha Carteira',
        description: 'Adicione saldo pelo Mercado Pago para usar buscas de compatibilidade.',
        icon: <PaymentIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/wallet',
        color: '#0288d1',
        gradient: 'linear-gradient(135deg, #0288d1 0%, #4fc3f7 100%)',
    },
    {
        title: 'Notificações',
        description: 'Veja suas notificações e atualizações.',
        icon: <NotificationsIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/notifications',
        color: '#d32f2f',
        gradient: 'linear-gradient(135deg, #d32f2f 0%, #ef5350 100%)',
    },
    {
        title: 'Minha Conta', description: 'Gerencie a segurança e a exclusão definitiva da conta.',
        icon: <ManageAccountsIcon sx={{ fontSize: 32, color: '#fff' }} />, path: '/dashboard/account', color: '#546e7a', gradient: 'linear-gradient(135deg, #37474f, #78909c)',
    },
];

const employerCards: DashboardCard[] = [
    {
        title: 'Minha Empresa',
        description: 'Cadastre os dados que serão apresentados nas suas vagas.',
        icon: <StorefrontIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/employer/company',
        color: '#00695c',
        gradient: 'linear-gradient(135deg, #00695c 0%, #26a69a 100%)',
    },
    {
        title: 'Minhas Vagas',
        description: 'Gerencie suas vagas publicadas, edite ou crie novas.',
        icon: <BusinessIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/employer/jobs',
        color: '#1976d2',
        gradient: 'linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)',
    },
    {
        title: 'Criar Nova Vaga',
        description: 'Publique uma nova oportunidade gratuitamente.',
        icon: <AddCircleIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/employer/jobs/new',
        color: '#2e7d32',
        gradient: 'linear-gradient(135deg, #2e7d32 0%, #66bb6a 100%)',
    },
    {
        title: 'Análise de Candidatos (IA)',
        description: 'Analise os currículos com cobrança por solicitação.',
        icon: <SmartToyIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/employer/ai/analyze',
        color: '#9c27b0',
        gradient: 'linear-gradient(135deg, #9c27b0 0%, #ce93d8 100%)',
    },
    {
        title: 'Minha Carteira',
        description: 'Adicione saldo pelo Mercado Pago para usar análises de IA.',
        icon: <PaymentIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/wallet',
        color: '#0288d1',
        gradient: 'linear-gradient(135deg, #0288d1 0%, #4fc3f7 100%)',
    },
    {
        title: 'Notificações',
        description: 'Acompanhe candidaturas recebidas e alertas.',
        icon: <NotificationsIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/dashboard/notifications',
        color: '#d32f2f',
        gradient: 'linear-gradient(135deg, #d32f2f 0%, #ef5350 100%)',
    },
    {
        title: 'Minha Conta', description: 'Gerencie a segurança e a exclusão definitiva da conta e da empresa.',
        icon: <ManageAccountsIcon sx={{ fontSize: 32, color: '#fff' }} />, path: '/dashboard/account', color: '#546e7a', gradient: 'linear-gradient(135deg, #37474f, #78909c)',
    },
];

const adminCards: DashboardCard[] = [
    {
        title: 'Painel Administrativo',
        description: 'Dashboard com KPIs, métricas e gestão da plataforma.',
        icon: <AdminPanelSettingsIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/admin',
        color: '#1976d2',
        gradient: 'linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)',
    },
    {
        title: 'Gestão de Usuários',
        description: 'Ativar, desativar e editar usuários da plataforma.',
        icon: <PeopleIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/admin/users',
        color: '#2e7d32',
        gradient: 'linear-gradient(135deg, #2e7d32 0%, #66bb6a 100%)',
    },
    {
        title: 'Financeiro',
        description: 'Transações, pagamentos e receita por período.',
        icon: <TokenIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/admin/financials',
        color: '#ed6c02',
        gradient: 'linear-gradient(135deg, #ed6c02 0%, #ffb74d 100%)',
    },
    {
        title: 'Configurações de Pagamento',
        description: 'Gerenciar preços, Checkout Pro e webhook.',
        icon: <PaymentIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/admin/payments',
        color: '#00897b',
        gradient: 'linear-gradient(135deg, #00897b 0%, #4db6ac 100%)',
    },
    {
        title: 'Segurança Administrativa',
        description: 'Ative a autenticação em dois fatores e proteja o painel.',
        icon: <AdminPanelSettingsIcon sx={{ fontSize: 32, color: '#fff' }} />,
        path: '/admin/security', color: '#5e35b1', gradient: 'linear-gradient(135deg, #4527a0, #7e57c2)',
    },
    {
        title: 'Denúncias de Vagas', description: 'Revise denúncias e aplique ações de moderação.',
        icon: <NotificationsIcon sx={{ fontSize: 32, color: '#fff' }} />, path: '/admin/reports', color: '#c62828', gradient: 'linear-gradient(135deg, #b71c1c, #ef5350)',
    },
];

export default function Dashboard() {
    const navigate = useNavigate();
    const user = useAuthStore((state) => state.user);
    const role = user?.role || 'candidate';
    const paymentConfig = usePaymentConfig();

    let cards: DashboardCard[] = candidateCards;
    let greeting = 'Candidato';

    if (role === 'employer') {
        cards = employerCards.map((card) => {
            if (card.title === 'Análise de Candidatos (IA)') return { ...card, description: `Analise os currículos por ${formatBRL(paymentConfig.prices.resume_analysis)} a cada solicitação.` };
            return card;
        });
        greeting = 'Empregador';
    } else if (role === 'admin') {
        cards = adminCards;
        greeting = 'Administrador';
    }

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            {/* Welcome Banner */}
            <Box
                sx={{
                    mb: 4,
                    p: { xs: 3, md: 4 },
                    borderRadius: 4,
                    background: 'linear-gradient(135deg, #1a237e 0%, #283593 50%, #1565c0 100%)',
                    color: 'white',
                    position: 'relative',
                    overflow: 'hidden',
                    '&::before': {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        right: 0,
                        width: '40%',
                        height: '100%',
                        background: 'radial-gradient(circle at 70% 50%, rgba(255,255,255,0.08) 0%, transparent 60%)',
                        pointerEvents: 'none',
                    },
                }}
            >
                <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
                    Olá, {user?.name || greeting}!
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body1" sx={{ opacity: 0.9 }}>
                        Painel do {greeting}
                    </Typography>
                    <Chip
                        label={role}
                        size="small"
                        sx={{
                            bgcolor: 'rgba(255,255,255,0.15)',
                            color: 'white',
                            fontWeight: 600,
                            borderColor: 'rgba(255,255,255,0.3)',
                            border: '1px solid',
                        }}
                    />
                </Box>
            </Box>

            <Grid container spacing={3}>
                {cards.map((card) => (
                    <Grid size={{ xs: 12, sm: 6, md: 4 }} key={card.path}>
                        <Card
                            sx={{
                                height: '100%',
                                display: 'flex',
                                flexDirection: 'column',
                                cursor: 'pointer',
                                position: 'relative',
                                '&::before': {
                                    content: '""',
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    height: '4px',
                                    background: card.gradient,
                                    borderRadius: '16px 16px 0 0',
                                    opacity: 0,
                                    transition: 'opacity 0.25s ease',
                                },
                                '&:hover::before': {
                                    opacity: 1,
                                },
                            }}
                            onClick={() => navigate(card.path)}
                        >
                            <CardContent sx={{ flexGrow: 1, p: 3 }}>
                                <Box
                                    sx={{
                                        width: 56,
                                        height: 56,
                                        borderRadius: 3,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        background: card.gradient,
                                        mb: 2.5,
                                        boxShadow: `0 4px 14px ${card.color}40`,
                                    }}
                                >
                                    {card.icon}
                                </Box>
                                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                                    {card.title}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
                                    {card.description}
                                </Typography>
                            </CardContent>
                            <CardActions sx={{ px: 3, pb: 2.5 }}>
                                <Button
                                    size="small"
                                    sx={{
                                        color: card.color,
                                        fontWeight: 600,
                                        '&:hover': {
                                            backgroundColor: `${card.color}08`,
                                        },
                                    }}
                                >
                                    Acessar →
                                </Button>
                            </CardActions>
                        </Card>
                    </Grid>
                ))}
            </Grid>
        </Container>
    );
}
