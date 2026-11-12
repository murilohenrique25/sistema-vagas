/**
 * Job creation and editing form for employers.
 * Requirements: 2.1, 2.2, 2.3
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Box,
    Container,
    Typography,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Button,
    Paper,
    Alert,
    Grid,
    CircularProgress,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { getJob, createJob, updateJob } from '../../services/jobService';
import type { JobCreate, JobModality, ContractType } from '../../types/job';
import { MODALITY_LABELS, CONTRACT_TYPE_LABELS } from '../../types/job';

interface FormErrors {
    title?: string;
    modality?: string;
    location?: string;
    responsibilities?: string;
    required_skills?: string;
    contract_type?: string;
    deadline?: string;
}

export default function JobForm() {
    const { jobId } = useParams<{ jobId: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const isEdit = Boolean(jobId);

    const [title, setTitle] = useState('');
    const [modality, setModality] = useState<JobModality>('onsite');
    const [location, setLocation] = useState('');
    const [responsibilities, setResponsibilities] = useState('');
    const [requiredSkills, setRequiredSkills] = useState('');
    const [optionalSkills, setOptionalSkills] = useState('');
    const [benefits, setBenefits] = useState('');
    const [contractType, setContractType] = useState<ContractType>('clt');
    const [deadline, setDeadline] = useState('');
    const [salaryMin, setSalaryMin] = useState('');
    const [salaryMax, setSalaryMax] = useState('');
    const [errors, setErrors] = useState<FormErrors>({});
    const [submitError, setSubmitError] = useState('');

    // Load existing job for editing
    const { data: existingJob, isLoading: loadingJob } = useQuery({
        queryKey: ['job', jobId],
        queryFn: () => getJob(jobId!),
        enabled: isEdit,
    });

    useEffect(() => {
        if (existingJob) {
            setTitle(existingJob.title);
            setModality(existingJob.modality);
            setLocation(existingJob.location || '');
            setResponsibilities(existingJob.responsibilities || '');
            setRequiredSkills(existingJob.required_skills || '');
            setOptionalSkills(existingJob.optional_skills || '');
            setBenefits(existingJob.benefits || '');
            setContractType(existingJob.contract_type);
            setDeadline(existingJob.deadline || '');
            setSalaryMin(existingJob.salary_min?.toString() || '');
            setSalaryMax(existingJob.salary_max?.toString() || '');
        }
    }, [existingJob]);

    const createMutation = useMutation({
        mutationFn: (data: JobCreate) => createJob(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            navigate('/dashboard/employer/jobs');
        },
        onError: (error: unknown) => {
            const err = error as { response?: { status?: number; data?: { detail?: string } } };
            setSubmitError(err.response?.data?.detail || 'Erro ao criar vaga. Tente novamente.');
        },
    });

    const updateMutation = useMutation({
        mutationFn: (data: JobCreate) => updateJob(jobId!, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            queryClient.invalidateQueries({ queryKey: ['job', jobId] });
            navigate('/dashboard/employer/jobs');
        },
        onError: (error: unknown) => {
            const err = error as { response?: { data?: { detail?: string } } };
            setSubmitError(err.response?.data?.detail || 'Erro ao atualizar vaga. Tente novamente.');
        },
    });

    function validate(): boolean {
        const newErrors: FormErrors = {};

        if (!title.trim()) {
            newErrors.title = 'O título é obrigatório';
        } else if (title.length > 150) {
            newErrors.title = 'O título deve ter no máximo 150 caracteres';
        }

        if (!location.trim()) {
            newErrors.location = 'A localização é obrigatória';
        }

        if (!responsibilities.trim()) {
            newErrors.responsibilities = 'As responsabilidades são obrigatórias';
        }

        if (!requiredSkills.trim()) {
            newErrors.required_skills = 'Os requisitos obrigatórios são obrigatórios';
        }

        if (!deadline) {
            newErrors.deadline = 'O prazo de encerramento é obrigatório';
        } else {
            const deadlineDate = new Date(deadline);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const diffDays = Math.ceil(
                (deadlineDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
            );
            if (diffDays < 1) {
                newErrors.deadline = 'O prazo deve ser no mínimo 1 dia no futuro';
            } else if (diffDays > 180) {
                newErrors.deadline = 'O prazo deve ser no máximo 180 dias no futuro';
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    }

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setSubmitError('');

        if (!validate()) return;

        const data: JobCreate = {
            title: title.trim(),
            modality,
            location: location.trim(),
            responsibilities: responsibilities.trim(),
            required_skills: requiredSkills.trim(),
            contract_type: contractType,
            deadline,
            optional_skills: optionalSkills.trim() || undefined,
            benefits: benefits.trim() || undefined,
            salary_min: salaryMin ? Number(salaryMin) : undefined,
            salary_max: salaryMax ? Number(salaryMax) : undefined,
        };

        if (isEdit) {
            updateMutation.mutate(data);
        } else {
            createMutation.mutate(data);
        }
    }

    const isSubmitting = createMutation.isPending || updateMutation.isPending;

    if (isEdit && loadingJob) {
        return (
            <Container maxWidth="md" sx={{ py: 4, textAlign: 'center' }}>
                <CircularProgress />
            </Container>
        );
    }

    return (
        <Container maxWidth="md" sx={{ py: 4 }}>
            <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/dashboard/employer/jobs')} sx={{ mb: 2 }}>
                Voltar
            </Button>

            <Typography variant="h4" component="h1" gutterBottom>
                {isEdit ? 'Editar Vaga' : 'Nova Vaga'}
            </Typography>

            {submitError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {submitError}
                </Alert>
            )}

            <Paper elevation={1} sx={{ p: 4 }}>
                <Box component="form" onSubmit={handleSubmit} noValidate>
                    <Grid container spacing={3}>
                        {/* Title */}
                        <Grid size={12}>
                            <TextField
                                fullWidth
                                label="Título da Vaga"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                error={!!errors.title}
                                helperText={errors.title || `${title.length}/150 caracteres`}
                                required
                                slotProps={{ htmlInput: { maxLength: 150 } }}
                            />
                        </Grid>

                        {/* Modality and Contract Type */}
                        <Grid size={{ xs: 12, md: 6 }}>
                            <FormControl fullWidth required>
                                <InputLabel>Modalidade</InputLabel>
                                <Select
                                    value={modality}
                                    label="Modalidade"
                                    onChange={(e) => setModality(e.target.value as JobModality)}
                                >
                                    {Object.entries(MODALITY_LABELS).map(([key, label]) => (
                                        <MenuItem key={key} value={key}>
                                            {label}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid size={{ xs: 12, md: 6 }}>
                            <FormControl fullWidth required>
                                <InputLabel>Regime de Contratação</InputLabel>
                                <Select
                                    value={contractType}
                                    label="Regime de Contratação"
                                    onChange={(e) => setContractType(e.target.value as ContractType)}
                                >
                                    {Object.entries(CONTRACT_TYPE_LABELS).map(([key, label]) => (
                                        <MenuItem key={key} value={key}>
                                            {label}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>

                        {/* Location */}
                        <Grid size={12}>
                            <TextField
                                fullWidth
                                label="Localização"
                                value={location}
                                onChange={(e) => setLocation(e.target.value)}
                                error={!!errors.location}
                                helperText={errors.location}
                                required
                                placeholder="Ex: São Paulo, SP"
                            />
                        </Grid>

                        {/* Salary range */}
                        <Grid size={{ xs: 12, md: 6 }}>
                            <TextField
                                fullWidth
                                label="Salário Mínimo (R$)"
                                type="number"
                                value={salaryMin}
                                onChange={(e) => setSalaryMin(e.target.value)}
                                placeholder="Opcional"
                            />
                        </Grid>
                        <Grid size={{ xs: 12, md: 6 }}>
                            <TextField
                                fullWidth
                                label="Salário Máximo (R$)"
                                type="number"
                                value={salaryMax}
                                onChange={(e) => setSalaryMax(e.target.value)}
                                placeholder="Opcional"
                            />
                        </Grid>

                        {/* Deadline */}
                        <Grid size={{ xs: 12, md: 6 }}>
                            <TextField
                                fullWidth
                                label="Prazo de Encerramento"
                                type="date"
                                value={deadline}
                                onChange={(e) => setDeadline(e.target.value)}
                                error={!!errors.deadline}
                                helperText={errors.deadline || 'Entre 1 e 180 dias no futuro'}
                                required
                                slotProps={{ inputLabel: { shrink: true } }}
                            />
                        </Grid>

                        {/* Responsibilities */}
                        <Grid size={12}>
                            <TextField
                                fullWidth
                                label="Responsabilidades"
                                value={responsibilities}
                                onChange={(e) => setResponsibilities(e.target.value)}
                                error={!!errors.responsibilities}
                                helperText={errors.responsibilities}
                                required
                                multiline
                                rows={4}
                                placeholder="Descreva as responsabilidades do cargo"
                            />
                        </Grid>

                        {/* Required skills */}
                        <Grid size={12}>
                            <TextField
                                fullWidth
                                label="Requisitos Obrigatórios"
                                value={requiredSkills}
                                onChange={(e) => setRequiredSkills(e.target.value)}
                                error={!!errors.required_skills}
                                helperText={errors.required_skills}
                                required
                                multiline
                                rows={3}
                                placeholder="Liste os requisitos obrigatórios"
                            />
                        </Grid>

                        {/* Optional skills */}
                        <Grid size={12}>
                            <TextField
                                fullWidth
                                label="Requisitos Desejáveis"
                                value={optionalSkills}
                                onChange={(e) => setOptionalSkills(e.target.value)}
                                multiline
                                rows={3}
                                placeholder="Liste os requisitos desejáveis (opcional)"
                            />
                        </Grid>

                        {/* Benefits */}
                        <Grid size={12}>
                            <TextField
                                fullWidth
                                label="Benefícios"
                                value={benefits}
                                onChange={(e) => setBenefits(e.target.value)}
                                multiline
                                rows={3}
                                placeholder="Liste os benefícios oferecidos (opcional)"
                            />
                        </Grid>

                        {/* Submit */}
                        <Grid size={12}>
                            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                                <Button
                                    variant="outlined"
                                    onClick={() => navigate('/dashboard/employer/jobs')}
                                >
                                    Cancelar
                                </Button>
                                <Button
                                    type="submit"
                                    variant="contained"
                                    startIcon={isSubmitting ? <CircularProgress size={20} /> : <SaveIcon />}
                                    disabled={isSubmitting}
                                >
                                    {isEdit ? 'Salvar Alterações' : 'Publicar vaga gratuitamente'}
                                </Button>
                            </Box>
                        </Grid>
                    </Grid>
                </Box>
            </Paper>
        </Container>
    );
}
