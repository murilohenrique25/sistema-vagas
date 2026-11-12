import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Box,
    Typography,
    Container,
    Button,
    Alert,
    Paper,
    Stepper,
    Step,
    StepLabel,
    Stack,
    Divider,
    CircularProgress,
} from '@mui/material';
import {
    Save as SaveIcon,
} from '@mui/icons-material';
import { useResumeFormStore } from '../../stores/resumeFormStore';
import { createOrUpdateResume, getMyResume } from '../../services/resumeService';
import type { ResumeCreate as ResumeCreatePayload } from '../../services/resumeService';
import PersonalDataSection from './sections/PersonalDataSection';
import ExperiencesSection from './sections/ExperiencesSection';
import EducationsSection from './sections/EducationsSection';
import SkillsSection from './sections/SkillsSection';
import CertificationsSection from './sections/CertificationsSection';
import LanguagesSection from './sections/LanguagesSection';
import PdfUploadSection from './sections/PdfUploadSection';

const steps = [
    'Dados Pessoais',
    'Experiência',
    'Formação',
    'Habilidades',
    'Certificações',
    'Idiomas',
];

export default function ResumeCreate() {
    const navigate = useNavigate();
    const {
        formData,
        isFromAiExtraction,
        setFullFormData,
        resetForm,
    } = useResumeFormStore();

    const [activeStep, setActiveStep] = useState(0);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const [loadingExisting, setLoadingExisting] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

    // Load existing resume if any
    useEffect(() => {
        async function loadExistingResume() {
            try {
                const resume = await getMyResume();
                // Populate form with existing data
                setFullFormData({
                    full_name: resume.full_name || '',
                    contact_email: resume.contact_email || '',
                    phone: resume.phone || '',
                    location: resume.location || '',
                    summary: resume.summary || '',
                    experiences: resume.experiences.map((exp) => ({
                        company: exp.company,
                        position: exp.position,
                        start_date: exp.start_date,
                        end_date: exp.end_date,
                        description: exp.description,
                    })),
                    educations: resume.educations.map((edu) => ({
                        institution: edu.institution,
                        course: edu.course,
                        degree: edu.degree,
                        start_date: edu.start_date,
                        end_date: edu.end_date,
                    })),
                    skills: resume.skills.map((skill) => ({
                        name: skill.name,
                        proficiency: skill.proficiency,
                    })),
                    certifications: resume.certifications.map((cert) => ({
                        name: cert.name,
                        issuer: cert.issuer,
                        obtained_at: cert.obtained_at,
                    })),
                    languages: resume.languages.map((lang) => ({
                        language: lang.language,
                        fluency: lang.fluency,
                    })),
                });
                setIsEditing(true);
            } catch {
                // No existing resume, that's fine - use form store data (may be preserved from error or AI extraction)
            } finally {
                setLoadingExisting(false);
            }
        }

        // Only load if form is not from AI extraction (AI extraction fills the form directly)
        if (!isFromAiExtraction) {
            loadExistingResume();
        } else {
            setLoadingExisting(false);
        }
    }, [isFromAiExtraction, setFullFormData]);

    function validateForm(): boolean {
        const errors: Record<string, string> = {};

        if (!formData.full_name.trim()) {
            errors.full_name = 'Nome completo é obrigatório';
        } else if (formData.full_name.length > 200) {
            errors.full_name = 'Nome completo deve ter no máximo 200 caracteres';
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!formData.contact_email) {
            errors.contact_email = 'Email de contato é obrigatório';
        } else if (!emailRegex.test(formData.contact_email)) {
            errors.contact_email = 'Formato de email inválido';
        }

        if (formData.experiences.length === 0 && formData.educations.length === 0) {
            errors._global = 'É necessário pelo menos uma experiência ou formação';
        }

        // Validate experiences
        formData.experiences.forEach((exp, i) => {
            if (!exp.company.trim()) errors[`exp_${i}_company`] = 'Empresa é obrigatória';
            if (!exp.position.trim()) errors[`exp_${i}_position`] = 'Cargo é obrigatório';
            if (!exp.start_date) errors[`exp_${i}_start_date`] = 'Data de início é obrigatória';
            if (exp.description && exp.description.length > 2000) {
                errors[`exp_${i}_description`] = 'Descrição deve ter no máximo 2000 caracteres';
            }
        });

        // Validate educations
        formData.educations.forEach((edu, i) => {
            if (!edu.institution.trim()) errors[`edu_${i}_institution`] = 'Instituição é obrigatória';
            if (!edu.course.trim()) errors[`edu_${i}_course`] = 'Curso é obrigatório';
            if (!edu.start_date) errors[`edu_${i}_start_date`] = 'Data de início é obrigatória';
        });

        // Validate skills
        formData.skills.forEach((skill, i) => {
            if (!skill.name.trim()) errors[`skill_${i}_name`] = 'Nome da habilidade é obrigatório';
        });

        // Validate certifications
        formData.certifications.forEach((cert, i) => {
            if (!cert.name.trim()) errors[`cert_${i}_name`] = 'Nome da certificação é obrigatório';
            if (!cert.issuer.trim()) errors[`cert_${i}_issuer`] = 'Instituição emissora é obrigatória';
        });

        // Validate languages
        formData.languages.forEach((lang, i) => {
            if (!lang.language.trim()) errors[`lang_${i}_language`] = 'Idioma é obrigatório';
        });

        setFieldErrors(errors);
        return Object.keys(errors).length === 0;
    }

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (!validateForm()) {
            setError('Por favor, corrija os campos com erro antes de salvar.');
            return;
        }

        setLoading(true);

        try {
            const payload: ResumeCreatePayload = {
                full_name: formData.full_name.trim(),
                contact_email: formData.contact_email.trim(),
                phone: formData.phone?.trim() || null,
                location: formData.location?.trim() || null,
                summary: formData.summary?.trim() || null,
                experiences: formData.experiences.map((exp) => ({
                    ...exp,
                    company: exp.company.trim(),
                    position: exp.position.trim(),
                    description: exp.description?.trim() || null,
                    end_date: exp.end_date || null,
                })),
                educations: formData.educations.map((edu) => ({
                    ...edu,
                    institution: edu.institution.trim(),
                    course: edu.course.trim(),
                    end_date: edu.end_date || null,
                })),
                skills: formData.skills.map((s) => ({
                    name: s.name.trim(),
                    proficiency: s.proficiency,
                })),
                certifications: formData.certifications.map((c) => ({
                    name: c.name.trim(),
                    issuer: c.issuer.trim(),
                    obtained_at: c.obtained_at || null,
                })),
                languages: formData.languages.map((l) => ({
                    language: l.language.trim(),
                    fluency: l.fluency,
                })),
            };

            await createOrUpdateResume(payload);
            setSuccess('Currículo salvo com sucesso!');
            resetForm();

            // Navigate after short delay so user sees success message
            setTimeout(() => {
                navigate('/dashboard/candidate');
            }, 1500);
        } catch (err: unknown) {
            if (err && typeof err === 'object' && 'response' in err) {
                const axiosError = err as { response?: { data?: { detail?: string } } };
                setError(
                    axiosError.response?.data?.detail ||
                    'Erro ao salvar currículo. Seus dados foram preservados no formulário.'
                );
            } else {
                setError('Erro ao conectar com o servidor. Seus dados foram preservados no formulário.');
            }
        } finally {
            setLoading(false);
        }
    }

    function handleNext() {
        setActiveStep((prev) => Math.min(prev + 1, steps.length - 1));
    }

    function handleBack() {
        setActiveStep((prev) => Math.max(prev - 1, 0));
    }

    function renderStepContent(step: number) {
        switch (step) {
            case 0:
                return <PersonalDataSection fieldErrors={fieldErrors} />;
            case 1:
                return <ExperiencesSection fieldErrors={fieldErrors} />;
            case 2:
                return <EducationsSection fieldErrors={fieldErrors} />;
            case 3:
                return <SkillsSection fieldErrors={fieldErrors} />;
            case 4:
                return <CertificationsSection fieldErrors={fieldErrors} />;
            case 5:
                return <LanguagesSection fieldErrors={fieldErrors} />;
            default:
                return null;
        }
    }

    if (loadingExisting) {
        return (
            <Container maxWidth="md">
                <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
                    <CircularProgress />
                </Box>
            </Container>
        );
    }

    return (
        <Container maxWidth="md">
            <Box sx={{ mt: 4, mb: 4 }}>
                <Typography variant="h4" component="h1" gutterBottom>
                    {isEditing ? 'Editar Currículo' : 'Cadastrar Currículo'}
                </Typography>

                {isFromAiExtraction && (
                    <Alert severity="info" sx={{ mb: 2 }}>
                        Os dados abaixo foram extraídos do seu PDF pela IA. Revise e corrija as
                        informações antes de salvar. Campos destacados em amarelo não puderam ser
                        preenchidos automaticamente.
                    </Alert>
                )}

                {/* PDF Upload Section */}
                {!isFromAiExtraction && (
                    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
                        <PdfUploadSection />
                    </Paper>
                )}

                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                    </Alert>
                )}

                {success && (
                    <Alert severity="success" sx={{ mb: 2 }}>
                        {success}
                    </Alert>
                )}

                {fieldErrors._global && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                        {fieldErrors._global}
                    </Alert>
                )}

                {/* Stepper */}
                <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 3 }}>
                    {steps.map((label) => (
                        <Step key={label}>
                            <StepLabel>{label}</StepLabel>
                        </Step>
                    ))}
                </Stepper>

                {/* Form content */}
                <Paper elevation={2} sx={{ p: 3 }}>
                    <Box component="form" onSubmit={handleSubmit} noValidate>
                        {renderStepContent(activeStep)}

                        <Divider sx={{ my: 3 }} />

                        <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
                            <Button
                                disabled={activeStep === 0}
                                onClick={handleBack}
                            >
                                Anterior
                            </Button>

                            <Stack direction="row" spacing={2}>
                                {activeStep < steps.length - 1 && (
                                    <Button variant="outlined" onClick={handleNext}>
                                        Próximo
                                    </Button>
                                )}
                                <Button
                                    type="submit"
                                    variant="contained"
                                    startIcon={<SaveIcon />}
                                    disabled={loading}
                                >
                                    {loading ? 'Salvando...' : 'Salvar Currículo'}
                                </Button>
                            </Stack>
                        </Stack>
                    </Box>
                </Paper>
            </Box>
        </Container>
    );
}
