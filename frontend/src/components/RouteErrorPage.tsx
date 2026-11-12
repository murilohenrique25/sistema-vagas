import { ErrorOutlineRounded } from '@mui/icons-material';
import { Box, Button, Container, Paper, Stack, Typography } from '@mui/material';
import { useNavigate, useRouteError } from 'react-router-dom';

export default function RouteErrorPage() {
    const navigate = useNavigate();
    const error = useRouteError();
    console.error('Route error:', error);

    return (
        <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', bgcolor: '#f5f7fa', p: 2 }}>
            <Container maxWidth="sm">
                <Paper sx={{ p: { xs: 3, sm: 5 }, textAlign: 'center', border: '1px solid #e2e8f2' }}>
                    <ErrorOutlineRounded sx={{ fontSize: 58, color: 'primary.main', mb: 2 }} />
                    <Typography variant="h4" component="h1" sx={{ fontWeight: 800 }}>Não foi possível abrir esta página</Typography>
                    <Typography color="text.secondary" sx={{ mt: 2, mb: 4 }}>Tente novamente. Se o problema continuar, volte ao início e refaça a operação.</Typography>
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ justifyContent: 'center' }}>
                        <Button variant="contained" onClick={() => window.location.reload()}>Tentar novamente</Button>
                        <Button variant="outlined" onClick={() => navigate('/')}>Voltar ao início</Button>
                    </Stack>
                </Paper>
            </Container>
        </Box>
    );
}
