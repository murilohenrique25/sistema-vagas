import { useState, type FormEvent } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
    Box,
    Typography,
    Container,
    TextField,
    Button,
    Alert,
    Link,
    Paper,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    type SelectChangeEvent,
    Stack,
    FormControlLabel,
    Checkbox,
} from '@mui/material';
import { CheckCircleOutlineRounded } from '@mui/icons-material';
import { register } from '../services/authService';

export default function Register() {
    const navigate = useNavigate();

    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState<'employer' | 'candidate'>('candidate');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [acceptTerms, setAcceptTerms] = useState(false);
    const [acceptPrivacy, setAcceptPrivacy] = useState(false);

    const [nameError, setNameError] = useState('');
    const [emailError, setEmailError] = useState('');
    const [passwordError, setPasswordError] = useState('');

    function validateForm(): boolean {
        let valid = true;
        setNameError('');
        setEmailError('');
        setPasswordError('');

        if (!name.trim()) {
            setNameError('Nome é obrigatório');
            valid = false;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!email) {
            setEmailError('Email é obrigatório');
            valid = false;
        } else if (!emailRegex.test(email)) {
            setEmailError('Formato de email inválido');
            valid = false;
        }

        if (!password) {
            setPasswordError('Senha é obrigatória');
            valid = false;
        } else if (password.length < 8) {
            setPasswordError('Senha deve ter no mínimo 8 caracteres');
            valid = false;
        } else {
            const hasUppercase = /[A-Z]/.test(password);
            const hasLowercase = /[a-z]/.test(password);
            const hasNumber = /\d/.test(password);
            const hasSpecial = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(password);

            if (!hasUppercase || !hasLowercase || !hasNumber || !hasSpecial) {
                setPasswordError(
                    'Senha deve conter ao menos: uma maiúscula, uma minúscula, um número e um caractere especial'
                );
                valid = false;
            }
        }

        return valid;
    }

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setError('');

        if (!validateForm()) return;

        setLoading(true);

        try {
            await register({ name, email, password, role, accept_terms: true, accept_privacy: true });
            navigate(`/verify-email?email=${encodeURIComponent(email)}`, { replace: true });
        } catch (err: unknown) {
            if (err && typeof err === 'object' && 'response' in err) {
                const axiosError = err as { response?: { data?: { detail?: string } } };
                setError(
                    axiosError.response?.data?.detail || 'Erro ao registrar. Tente novamente.'
                );
            } else {
                setError('Erro ao conectar com o servidor. Tente novamente.');
            }
        } finally {
            setLoading(false);
        }
    }

    function handleRoleChange(e: SelectChangeEvent) {
        setRole(e.target.value as 'employer' | 'candidate');
    }

    return (
        <Box sx={{ minHeight: 'calc(100vh - 64px)', display: 'flex', alignItems: 'center', py: { xs: 4, md: 7 }, background: 'linear-gradient(135deg, #f7f9fc 0%, #edf2fb 100%)' }}>
            <Container maxWidth="md">
                <Paper elevation={0} sx={{ overflow: 'hidden', display: 'grid', gridTemplateColumns: { xs: '1fr', md: '0.8fr 1.2fr' }, border: '1px solid #e2e8f2', boxShadow: '0 24px 60px rgba(24,39,90,.11)' }}>
                    <Box sx={{ display: { xs: 'none', md: 'block' }, p: 5, color: 'white', background: 'linear-gradient(155deg, #15235e, #1769aa)' }}>
                        <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: '-.03em' }}>Comece gratuitamente</Typography>
                        <Typography sx={{ mt: 2, color: 'rgba(255,255,255,.78)', lineHeight: 1.7 }}>Escolha seu perfil e tenha acesso às oportunidades e ferramentas da plataforma.</Typography>
                        <Stack spacing={2.2} sx={{ mt: 5 }}>
                            {['Candidaturas sem limite', 'Sem mensalidade', 'Créditos via checkout seguro'].map((text) => (
                                <Stack key={text} direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                                    <CheckCircleOutlineRounded sx={{ color: 'secondary.light' }} />
                                    <Typography>{text}</Typography>
                                </Stack>
                            ))}
                        </Stack>
                    </Box>
                    <Box sx={{ p: { xs: 3, sm: 5 } }}>
                    <Typography variant="h4" component="h1" sx={{ fontWeight: 800, letterSpacing: '-.03em' }}>
                        Criar sua conta
                    </Typography>
                    <Typography color="text.secondary" sx={{ mt: 1, mb: 2 }}>Leva menos de dois minutos.</Typography>

                    {error && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                            {error}
                        </Alert>
                    )}

                    <Box component="form" onSubmit={handleSubmit} noValidate>
                        <TextField
                            margin="normal"
                            required
                            fullWidth
                            id="name"
                            label="Nome completo"
                            name="name"
                            autoComplete="name"
                            autoFocus
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            error={!!nameError}
                            helperText={nameError}
                        />
                        <TextField
                            margin="normal"
                            required
                            fullWidth
                            id="email"
                            label="Email"
                            name="email"
                            autoComplete="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            error={!!emailError}
                            helperText={emailError}
                        />
                        <TextField
                            margin="normal"
                            required
                            fullWidth
                            name="password"
                            label="Senha"
                            type="password"
                            id="password"
                            autoComplete="new-password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            error={!!passwordError}
                            helperText={passwordError}
                        />
                        <FormControl fullWidth margin="normal">
                            <InputLabel id="role-label">Quero usar como</InputLabel>
                            <Select
                                labelId="role-label"
                                id="role"
                                value={role}
                                label="Quero usar como"
                                onChange={handleRoleChange}
                            >
                                <MenuItem value="candidate">Candidato — buscar oportunidades</MenuItem>
                                <MenuItem value="employer">Empregador — publicar vagas</MenuItem>
                            </Select>
                        </FormControl>
                        <FormControlLabel control={<Checkbox checked={acceptTerms} onChange={(e) => setAcceptTerms(e.target.checked)} />} label={<span>Li e aceito os <Link component={RouterLink} to="/terms" target="_blank">Termos de Uso</Link>.</span>} />
                        <FormControlLabel control={<Checkbox checked={acceptPrivacy} onChange={(e) => setAcceptPrivacy(e.target.checked)} />} label={<span>Li a <Link component={RouterLink} to="/privacy" target="_blank">Política de Privacidade</Link> e estou ciente do tratamento dos meus dados.</span>} />
                        <Button
                            type="submit"
                            fullWidth
                            variant="contained"
                            size="large"
                            sx={{ mt: 3, mb: 2, py: 1.35 }}
                            disabled={loading || !acceptTerms || !acceptPrivacy}
                        >
                            {loading ? 'Cadastrando...' : 'Cadastrar'}
                        </Button>
                    </Box>

                    <Box sx={{ mt: 2, textAlign: 'center' }}>
                        <Link component={RouterLink} to="/login" variant="body2">
                            Já tem uma conta? <strong>Entrar</strong>
                        </Link>
                    </Box>
                    </Box>
                </Paper>
            </Container>
        </Box>
    );
}
