import {
    ArrowForwardRounded,
    AutoAwesomeRounded,
    CheckCircleRounded,
    PersonSearchRounded,
    WorkOutlineRounded,
} from '@mui/icons-material';
import { Box, Button, Chip, Container, Grid, Paper, Stack, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { usePaymentConfig } from '../hooks/usePaymentConfig';
import { formatBRL } from '../utils/currency';

export default function Home() {
    const navigate = useNavigate();
    const paymentConfig = usePaymentConfig();
    const { resume_analysis, job_compatibility } = paymentConfig.prices;
    const benefits = [
        { icon: <WorkOutlineRounded />, title: 'Para empresas', text: 'Publique vagas gratuitamente e encontre candidatos com mais agilidade.' },
        { icon: <PersonSearchRounded />, title: 'Para candidatos', text: 'Candidate-se gratuitamente a vagas em Caldas Novas, região e oportunidades remotas.' },
        { icon: <AutoAwesomeRounded />, title: 'IA sob demanda', text: `Pague apenas quando solicitar uma análise: ${formatBRL(resume_analysis)} por uso.` },
    ];

    return (
        <Box sx={{ bgcolor: '#f7f9fc', overflow: 'hidden' }}>
            <Box
                component="section"
                sx={{
                    position: 'relative',
                    color: 'white',
                    background: 'linear-gradient(135deg, #101a46 0%, #253b88 52%, #1769aa 100%)',
                    py: { xs: 8, md: 13 },
                    '&::after': {
                        content: '""', position: 'absolute', width: 520, height: 520,
                        borderRadius: '50%', right: -180, top: -250,
                        background: 'radial-gradient(circle, rgba(79,209,197,.28), transparent 68%)',
                    },
                }}
            >
                <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1 }}>
                    <Grid container spacing={{ xs: 6, md: 8 }} sx={{ alignItems: 'center' }}>
                        <Grid size={{ xs: 12, md: 7 }}>
                            <Chip
                                icon={<AutoAwesomeRounded />}
                                label="Recrutamento mais simples e inteligente"
                                sx={{ mb: 3, bgcolor: 'rgba(255,255,255,.1)', color: 'white', border: '1px solid rgba(255,255,255,.2)', '& .MuiChip-icon': { color: '#6ee7dc' } }}
                            />
                            <Typography component="h1" sx={{ fontSize: { xs: '2.45rem', sm: '3.5rem', md: '4.25rem' }, lineHeight: 1.06, fontWeight: 800, letterSpacing: '-.045em', maxWidth: 760 }}>
                                Talentos e empresas, conectados pelo que realmente importa.
                            </Typography>
                            <Typography sx={{ mt: 3, maxWidth: 650, fontSize: { xs: '1.05rem', md: '1.25rem' }, lineHeight: 1.7, color: 'rgba(255,255,255,.78)' }}>
                                Encontre vagas em Caldas Novas e região, divulgue oportunidades e use inteligência artificial somente quando ela agregar valor.
                            </Typography>
                            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mt: 4 }}>
                                <Button size="large" variant="contained" endIcon={<ArrowForwardRounded />} onClick={() => navigate('/register')} sx={{ bgcolor: '#fff', color: '#17245b', px: 3.5, '&:hover': { bgcolor: '#eef3ff' } }}>
                                    Criar conta grátis
                                </Button>
                                <Button size="large" variant="outlined" onClick={() => navigate('/jobs')} sx={{ color: 'white', borderColor: 'rgba(255,255,255,.45)', px: 3.5, '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,.06)' } }}>
                                    Explorar vagas
                                </Button>
                            </Stack>
                            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={{ xs: 1, sm: 3 }} sx={{ mt: 4 }}>
                                {['Vagas e candidaturas gratuitas', 'IA sob demanda', 'Checkout Mercado Pago'].map((item) => (
                                    <Stack key={item} direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                                        <CheckCircleRounded sx={{ color: '#6ee7dc', fontSize: 19 }} />
                                        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,.82)' }}>{item}</Typography>
                                    </Stack>
                                ))}
                            </Stack>
                        </Grid>
                        <Grid size={{ xs: 12, md: 5 }}>
                            <Paper sx={{ p: { xs: 3, sm: 4 }, bgcolor: 'rgba(255,255,255,.97)', boxShadow: '0 28px 70px rgba(5,13,49,.3)' }}>
                                <Typography color="primary.dark" variant="h5" sx={{ fontWeight: 800 }}>Preço claro, sem assinatura</Typography>
                                <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>Adicione saldo à carteira e utilize quando precisar.</Typography>
                                <Stack spacing={2.2}>
                                    {[
                                        ['Publicar uma vaga', 'Grátis'],
                                        ['Analisar um currículo', formatBRL(resume_analysis)],
                                        ['Ver compatibilidade com vaga', formatBRL(job_compatibility)],
                                    ].map(([label, price]) => (
                                        <Stack key={label} direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', pb: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                                            <Typography color="text.primary">{label}</Typography>
                                            <Typography color="primary.main" sx={{ fontWeight: 800 }}>{price}</Typography>
                                        </Stack>
                                    ))}
                                </Stack>
                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2.5 }}>Criar conta, publicar e buscar vagas e candidatar-se são gratuitos.</Typography>
                            </Paper>
                        </Grid>
                    </Grid>
                </Container>
            </Box>

            <Container component="section" maxWidth="lg" sx={{ py: { xs: 7, md: 10 } }}>
                <Box sx={{ textAlign: 'center', maxWidth: 720, mx: 'auto', mb: 6 }}>
                    <Typography color="primary.main" variant="overline" sx={{ fontWeight: 800 }}>Feito para decisões melhores</Typography>
                    <Typography variant="h3" sx={{ mt: 1, fontSize: { xs: '2rem', md: '2.75rem' }, letterSpacing: '-.03em' }}>Um processo profissional para os dois lados</Typography>
                    <Typography color="text.secondary" sx={{ mt: 2, fontSize: '1.05rem' }}>Menos barreiras para candidatos. Mais controle e inteligência para empresas.</Typography>
                </Box>
                <Grid container spacing={3}>
                    {benefits.map((item) => (
                        <Grid key={item.title} size={{ xs: 12, md: 4 }}>
                            <Paper sx={{ p: 4, height: '100%', border: '1px solid #e5eaf3', boxShadow: '0 12px 32px rgba(29,46,94,.06)' }}>
                                <Box sx={{ width: 50, height: 50, display: 'grid', placeItems: 'center', borderRadius: 3, bgcolor: '#eaf0ff', color: 'primary.main', mb: 3 }}>{item.icon}</Box>
                                <Typography variant="h5" sx={{ fontWeight: 800 }}>{item.title}</Typography>
                                <Typography color="text.secondary" sx={{ mt: 1.5, lineHeight: 1.75 }}>{item.text}</Typography>
                            </Paper>
                        </Grid>
                    ))}
                </Grid>
            </Container>

            <Box component="section" sx={{ bgcolor: '#eef3fb', py: { xs: 7, md: 9 } }}>
                <Container maxWidth="md" sx={{ textAlign: 'center' }}>
                    <Typography variant="h3" sx={{ fontSize: { xs: '2rem', md: '2.7rem' }, letterSpacing: '-.03em' }}>Pronto para encontrar a próxima oportunidade?</Typography>
                    <Typography color="text.secondary" sx={{ mt: 2, mb: 4, fontSize: '1.05rem' }}>Comece gratuitamente. Você só paga pelas ações premium que escolher usar.</Typography>
                    <Button size="large" variant="contained" endIcon={<ArrowForwardRounded />} onClick={() => navigate('/register')}>Começar agora</Button>
                </Container>
            </Box>
            <Box component="footer" sx={{ py: 3, bgcolor: '#101a46', color: 'rgba(255,255,255,.65)' }}>
                <Container maxWidth="lg"><Typography variant="body2">© 2026 Recruta IA · Recrutamento com transparência e tecnologia.</Typography></Container>
            </Box>
        </Box>
    );
}
