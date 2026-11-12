import {
    TextField,
    Stack,
    Typography,
    Button,
    IconButton,
    Paper,
    Box,
    Alert,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { useResumeFormStore } from '../../../stores/resumeFormStore';

interface Props {
    fieldErrors: Record<string, string>;
}

export default function ExperiencesSection({ fieldErrors }: Props) {
    const {
        formData,
        addExperience,
        removeExperience,
        updateExperience,
        aiFilledFields,
        isFromAiExtraction,
    } = useResumeFormStore();

    const experiences = formData.experiences;

    function isAiUnfilled(index: number): boolean {
        if (!isFromAiExtraction || !aiFilledFields) return false;
        return aiFilledFields.experiences[index] === false;
    }

    return (
        <Stack spacing={3}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Experiência Profissional</Typography>
                <Button
                    startIcon={<AddIcon />}
                    onClick={addExperience}
                    disabled={experiences.length >= 30}
                    size="small"
                >
                    Adicionar
                </Button>
            </Box>

            {experiences.length >= 30 && (
                <Alert severity="info">Máximo de 30 experiências atingido.</Alert>
            )}

            {experiences.length === 0 && (
                <Typography color="text.secondary" variant="body2">
                    Nenhuma experiência adicionada. Clique em "Adicionar" para incluir uma experiência
                    profissional.
                </Typography>
            )}

            {experiences.map((exp, index) => (
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
                            Experiência {index + 1}
                        </Typography>
                        <IconButton
                            size="small"
                            color="error"
                            onClick={() => removeExperience(index)}
                            aria-label={`Remover experiência ${index + 1}`}
                        >
                            <DeleteIcon fontSize="small" />
                        </IconButton>
                    </Box>

                    <Stack spacing={2}>
                        <TextField
                            required
                            fullWidth
                            label="Empresa"
                            value={exp.company}
                            onChange={(e) => updateExperience(index, { company: e.target.value })}
                            error={!!fieldErrors[`exp_${index}_company`]}
                            helperText={fieldErrors[`exp_${index}_company`]}
                            size="small"
                        />
                        <TextField
                            required
                            fullWidth
                            label="Cargo"
                            value={exp.position}
                            onChange={(e) => updateExperience(index, { position: e.target.value })}
                            error={!!fieldErrors[`exp_${index}_position`]}
                            helperText={fieldErrors[`exp_${index}_position`]}
                            size="small"
                        />
                        <Stack direction="row" spacing={2}>
                            <TextField
                                required
                                fullWidth
                                label="Data de início"
                                type="date"
                                value={exp.start_date}
                                onChange={(e) => updateExperience(index, { start_date: e.target.value })}
                                error={!!fieldErrors[`exp_${index}_start_date`]}
                                helperText={fieldErrors[`exp_${index}_start_date`]}
                                slotProps={{ inputLabel: { shrink: true } }}
                                size="small"
                            />
                            <TextField
                                fullWidth
                                label="Data de término"
                                type="date"
                                value={exp.end_date || ''}
                                onChange={(e) => updateExperience(index, { end_date: e.target.value || null })}
                                slotProps={{ inputLabel: { shrink: true } }}
                                size="small"
                                helperText="Deixe em branco se atual"
                            />
                        </Stack>
                        <TextField
                            fullWidth
                            label="Descrição"
                            multiline
                            rows={3}
                            value={exp.description || ''}
                            onChange={(e) => updateExperience(index, { description: e.target.value })}
                            error={!!fieldErrors[`exp_${index}_description`]}
                            helperText={
                                fieldErrors[`exp_${index}_description`] ||
                                `${(exp.description || '').length}/2000 caracteres`
                            }
                            slotProps={{ htmlInput: { maxLength: 2000 } }}
                            size="small"
                        />
                    </Stack>
                </Paper>
            ))}
        </Stack>
    );
}
