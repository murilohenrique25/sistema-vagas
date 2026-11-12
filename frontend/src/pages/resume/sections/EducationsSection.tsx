import {
    TextField,
    Stack,
    Typography,
    Button,
    IconButton,
    Paper,
    Box,
    Alert,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { useResumeFormStore } from '../../../stores/resumeFormStore';
import type { DegreeLevel } from '../../../services/resumeService';

interface Props {
    fieldErrors: Record<string, string>;
}

const DEGREE_OPTIONS: { value: DegreeLevel; label: string }[] = [
    { value: 'high_school', label: 'Ensino Médio' },
    { value: 'technical', label: 'Técnico' },
    { value: 'bachelor', label: 'Graduação' },
    { value: 'master', label: 'Mestrado' },
    { value: 'doctorate', label: 'Doutorado' },
];

export default function EducationsSection({ fieldErrors }: Props) {
    const {
        formData,
        addEducation,
        removeEducation,
        updateEducation,
        aiFilledFields,
        isFromAiExtraction,
    } = useResumeFormStore();

    const educations = formData.educations;

    function isAiUnfilled(index: number): boolean {
        if (!isFromAiExtraction || !aiFilledFields) return false;
        return aiFilledFields.educations[index] === false;
    }

    return (
        <Stack spacing={3}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Formação Acadêmica</Typography>
                <Button
                    startIcon={<AddIcon />}
                    onClick={addEducation}
                    disabled={educations.length >= 30}
                    size="small"
                >
                    Adicionar
                </Button>
            </Box>

            {educations.length >= 30 && (
                <Alert severity="info">Máximo de 30 formações atingido.</Alert>
            )}

            {educations.length === 0 && (
                <Typography color="text.secondary" variant="body2">
                    Nenhuma formação adicionada. Clique em "Adicionar" para incluir uma formação
                    acadêmica.
                </Typography>
            )}

            {educations.map((edu, index) => (
                <Paper
                    key={index}
                    variant="outlined"
                    sx={{
                        p: 2,
                        borderColor: isAiUnfilled(index) ? 'warning.main' : undefined,
                        borderWidth: isAiUnfilled(index) ? 2 : 1,
                        backgroundColor: isAiUnfilled(index) ? 'rgba(255, 193, 7, 0.04)' : undefined,
                    }}
                >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                        <Typography variant="subtitle2">
                            Formação {index + 1}
                        </Typography>
                        <IconButton
                            size="small"
                            color="error"
                            onClick={() => removeEducation(index)}
                            aria-label={`Remover formação ${index + 1}`}
                        >
                            <DeleteIcon fontSize="small" />
                        </IconButton>
                    </Box>

                    <Stack spacing={2}>
                        <TextField
                            required
                            fullWidth
                            label="Instituição"
                            value={edu.institution}
                            onChange={(e) => updateEducation(index, { institution: e.target.value })}
                            error={!!fieldErrors[`edu_${index}_institution`]}
                            helperText={fieldErrors[`edu_${index}_institution`]}
                            size="small"
                        />
                        <TextField
                            required
                            fullWidth
                            label="Curso"
                            value={edu.course}
                            onChange={(e) => updateEducation(index, { course: e.target.value })}
                            error={!!fieldErrors[`edu_${index}_course`]}
                            helperText={fieldErrors[`edu_${index}_course`]}
                            size="small"
                        />
                        <FormControl fullWidth size="small">
                            <InputLabel id={`degree-label-${index}`}>Grau</InputLabel>
                            <Select
                                labelId={`degree-label-${index}`}
                                value={edu.degree}
                                label="Grau"
                                onChange={(e) => updateEducation(index, { degree: e.target.value as DegreeLevel })}
                            >
                                {DEGREE_OPTIONS.map((opt) => (
                                    <MenuItem key={opt.value} value={opt.value}>
                                        {opt.label}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <Stack direction="row" spacing={2}>
                            <TextField
                                required
                                fullWidth
                                label="Data de início"
                                type="date"
                                value={edu.start_date}
                                onChange={(e) => updateEducation(index, { start_date: e.target.value })}
                                error={!!fieldErrors[`edu_${index}_start_date`]}
                                helperText={fieldErrors[`edu_${index}_start_date`]}
                                slotProps={{ inputLabel: { shrink: true } }}
                                size="small"
                            />
                            <TextField
                                fullWidth
                                label="Data de conclusão"
                                type="date"
                                value={edu.end_date || ''}
                                onChange={(e) => updateEducation(index, { end_date: e.target.value || null })}
                                slotProps={{ inputLabel: { shrink: true } }}
                                size="small"
                                helperText="Deixe em branco se em andamento"
                            />
                        </Stack>
                    </Stack>
                </Paper>
            ))}
        </Stack>
    );
}
