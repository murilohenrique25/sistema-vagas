import { useState, useRef } from 'react';
import {
    Typography,
    Button,
    Stack,
    Alert,
    LinearProgress,
    Box,
    Chip,
} from '@mui/material';
import {
    CloudUpload as CloudUploadIcon,
    PictureAsPdf as PdfIcon,
    Refresh as RefreshIcon,
} from '@mui/icons-material';
import { importResumePdf } from '../../../services/resumeService';
import { useResumeFormStore } from '../../../stores/resumeFormStore';
import type { AiFilledFields } from '../../../stores/resumeFormStore';
import type {
    ExtractedResume,
    DegreeLevel,
    ProficiencyLevel,
    FluencyLevel,
} from '../../../services/resumeService';

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const VALID_DEGREE_LEVELS: DegreeLevel[] = ['high_school', 'bachelor', 'master', 'doctorate', 'technical'];
const VALID_PROFICIENCY_LEVELS: ProficiencyLevel[] = ['beginner', 'intermediate', 'advanced', 'expert'];
const VALID_FLUENCY_LEVELS: FluencyLevel[] = ['basic', 'intermediate', 'advanced', 'native'];

export default function PdfUploadSection() {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const { setFullFormData, setAiFilledFields, setIsFromAiExtraction } = useResumeFormStore();

    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [processingAi, setProcessingAi] = useState(false);
    const [error, setError] = useState('');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);

    function validateFile(file: File): string | null {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            return 'Apenas arquivos PDF são aceitos.';
        }
        if (file.size > MAX_FILE_SIZE) {
            return `Arquivo excede o limite de 5MB. Tamanho: ${(file.size / 1024 / 1024).toFixed(1)}MB`;
        }
        if (file.type && file.type !== 'application/pdf') {
            return 'O arquivo não é um PDF válido.';
        }
        return null;
    }

    function mapExtractedDataToForm(extracted: ExtractedResume) {
        const aiFields: AiFilledFields = {
            full_name: !!extracted.personal_data.full_name,
            contact_email: !!extracted.personal_data.contact_email,
            phone: !!extracted.personal_data.phone,
            location: !!extracted.personal_data.location,
            summary: false, // AI doesn't typically extract a summary
            experiences: [],
            educations: [],
            skills: [],
            certifications: [],
            languages: [],
        };

        // Map experiences
        const experiences = extracted.experiences
            .filter((exp) => exp.company || exp.position)
            .map((exp, index) => {
                const hasData = !!(exp.company && exp.position && exp.start_date);
                aiFields.experiences[index] = hasData;
                return {
                    company: exp.company || '',
                    position: exp.position || '',
                    start_date: exp.start_date || '',
                    end_date: exp.end_date || null,
                    description: exp.description || null,
                };
            });

        // Map educations
        const educations = extracted.educations
            .filter((edu) => edu.institution || edu.course)
            .map((edu, index) => {
                const hasData = !!(edu.institution && edu.course && edu.start_date);
                aiFields.educations[index] = hasData;
                return {
                    institution: edu.institution || '',
                    course: edu.course || '',
                    degree: (VALID_DEGREE_LEVELS.includes(edu.degree as DegreeLevel)
                        ? edu.degree
                        : 'bachelor') as DegreeLevel,
                    start_date: edu.start_date || '',
                    end_date: edu.end_date || null,
                };
            });

        // Map skills
        const skills = extracted.skills
            .filter((s) => s.name)
            .map((s, index) => {
                aiFields.skills[index] = !!s.name;
                return {
                    name: s.name || '',
                    proficiency: (VALID_PROFICIENCY_LEVELS.includes(s.proficiency as ProficiencyLevel)
                        ? s.proficiency
                        : 'intermediate') as ProficiencyLevel,
                };
            });

        // Map certifications
        const certifications = extracted.certifications
            .filter((c) => c.name)
            .map((c, index) => {
                aiFields.certifications[index] = !!(c.name && c.issuer);
                return {
                    name: c.name || '',
                    issuer: c.issuer || '',
                    obtained_at: c.obtained_at || null,
                };
            });

        // Map languages
        const languages = extracted.languages
            .filter((l) => l.language)
            .map((l, index) => {
                aiFields.languages[index] = !!l.language;
                return {
                    language: l.language || '',
                    fluency: (VALID_FLUENCY_LEVELS.includes(l.fluency as FluencyLevel)
                        ? l.fluency
                        : 'intermediate') as FluencyLevel,
                };
            });

        setFullFormData({
            full_name: extracted.personal_data.full_name || '',
            contact_email: extracted.personal_data.contact_email || '',
            phone: extracted.personal_data.phone || '',
            location: extracted.personal_data.location || '',
            summary: '',
            experiences,
            educations,
            skills,
            certifications,
            languages,
        });

        setAiFilledFields(aiFields);
        setIsFromAiExtraction(true);
    }

    async function handleUpload() {
        if (!selectedFile) return;

        const validationError = validateFile(selectedFile);
        if (validationError) {
            setError(validationError);
            return;
        }

        setError('');
        setUploading(true);
        setUploadProgress(0);

        try {
            // Upload phase
            setProcessingAi(false);
            const response = await importResumePdf(selectedFile, (progress) => {
                setUploadProgress(progress);
                if (progress === 100) {
                    setProcessingAi(true);
                }
            });

            // Map extracted data to form
            mapExtractedDataToForm(response.extracted_data);
        } catch (err: unknown) {
            if (err && typeof err === 'object' && 'response' in err) {
                const axiosError = err as { response?: { data?: { detail?: string } }; code?: string };
                if (axiosError.code === 'ECONNABORTED') {
                    setError(
                        'A extração não pôde ser concluída dentro do tempo limite. ' +
                        'Você pode tentar novamente ou preencher o currículo manualmente.'
                    );
                } else {
                    setError(
                        axiosError.response?.data?.detail ||
                        'Erro ao processar o PDF. Tente novamente ou preencha manualmente.'
                    );
                }
            } else {
                setError(
                    'Serviço de IA indisponível. Você pode tentar novamente ou preencher o currículo manualmente.'
                );
            }
        } finally {
            setUploading(false);
            setProcessingAi(false);
            setUploadProgress(0);
        }
    }

    function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
        const file = event.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setError('');
        }
    }

    function handleClickUploadArea() {
        fileInputRef.current?.click();
    }

    return (
        <Stack spacing={2}>
            <Typography variant="h6">Importar Currículo em PDF</Typography>
            <Typography variant="body2" color="text.secondary">
                Faça upload do seu currículo em PDF e nossa IA extrairá os dados automaticamente.
                Após a extração, você poderá revisar e corrigir as informações antes de salvar.
            </Typography>

            <Box
                onClick={handleClickUploadArea}
                sx={{
                    border: '2px dashed',
                    borderColor: selectedFile ? 'primary.main' : 'grey.400',
                    borderRadius: 2,
                    p: 3,
                    textAlign: 'center',
                    cursor: 'pointer',
                    transition: 'border-color 0.2s',
                    '&:hover': { borderColor: 'primary.main' },
                    backgroundColor: selectedFile ? 'action.hover' : 'transparent',
                }}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    hidden
                    onChange={handleFileSelect}
                />
                {selectedFile ? (
                    <Stack direction="row" spacing={1} sx={{ justifyContent: 'center', alignItems: 'center' }}>
                        <PdfIcon color="error" />
                        <Typography>{selectedFile.name}</Typography>
                        <Chip
                            label={`${(selectedFile.size / 1024 / 1024).toFixed(1)} MB`}
                            size="small"
                            variant="outlined"
                        />
                    </Stack>
                ) : (
                    <Stack spacing={1} sx={{ alignItems: 'center' }}>
                        <CloudUploadIcon sx={{ fontSize: 40, color: 'grey.500' }} />
                        <Typography color="text.secondary">
                            Clique para selecionar ou arraste um arquivo PDF (máx. 5MB)
                        </Typography>
                    </Stack>
                )}
            </Box>

            {/* Progress indicator */}
            {uploading && (
                <Box>
                    <Stack direction="row" sx={{ justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2" color="text.secondary">
                            {processingAi ? 'Processando com IA...' : 'Enviando arquivo...'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            {processingAi ? '' : `${uploadProgress}%`}
                        </Typography>
                    </Stack>
                    <LinearProgress
                        variant={processingAi ? 'indeterminate' : 'determinate'}
                        value={uploadProgress}
                    />
                    {processingAi && (
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                            A IA está extraindo dados do seu currículo. Isso pode levar até 60 segundos...
                        </Typography>
                    )}
                </Box>
            )}

            {error && (
                <Alert
                    severity="error"
                    action={
                        <Button
                            color="inherit"
                            size="small"
                            startIcon={<RefreshIcon />}
                            onClick={handleUpload}
                            disabled={!selectedFile}
                        >
                            Tentar novamente
                        </Button>
                    }
                >
                    {error}
                </Alert>
            )}

            <Button
                variant="contained"
                startIcon={<CloudUploadIcon />}
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
            >
                {uploading ? 'Processando...' : 'Importar PDF com IA'}
            </Button>
        </Stack>
    );
}
