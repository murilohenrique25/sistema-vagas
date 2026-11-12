import { Box, Typography, Button, Container } from '@mui/material';
import { useNavigate } from 'react-router-dom';

export default function NotFound() {
    const navigate = useNavigate();

    return (
        <Container maxWidth="sm">
            <Box
                sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minHeight: '60vh',
                    textAlign: 'center',
                    gap: 2,
                }}
            >
                <Typography variant="h2" component="h1">
                    404
                </Typography>
                <Typography variant="h5" color="text.secondary">
                    Página não encontrada
                </Typography>
                <Button variant="contained" onClick={() => navigate('/')}>
                    Voltar ao início
                </Button>
            </Box>
        </Container>
    );
}
