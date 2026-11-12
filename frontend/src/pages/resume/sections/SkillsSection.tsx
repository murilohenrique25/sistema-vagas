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
import type { ProficiencyLevel } from '../../../services/resumeService';

interface Props {
    fieldErrors: Record<string, string>;
}

const PROFICIENCY_OPTIONS: { value: ProficiencyLevel; label: string }[] = [
    { value: 'beginner', label: 'Iniciante' },
    { value: 'intermediate', label: 'Intermediário' },
    { value: 'advanced', label: 'Avançado' },
    { value: 'expert', label: 'Especialista' },
];

export default function SkillsSection({ fieldErrors }: Props) {
    const {
        formData,
        addSkill,
        removeSkill,
        updateSkill,
        aiFilledFields,
        isFromAiExtraction,
    } = useResumeFormStore();

    const skills = formData.skills;

    function isAiUnfilled(index: number): boolean {
        if (!isFromAiExtraction || !aiFilledFields) return false;
        return aiFilledFields.skills[index] === false;
    }

    return (
        <Stack spacing={3}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Habilidades Técnicas</Typography>
                <Button
                    startIcon={<AddIcon />}
                    onClick={addSkill}
                    disabled={skills.length >= 30}
                    size="small"
                >
                    Adicionar
                </Button>
            </Box>

            {skills.length >= 30 && (
                <Alert severity="info">Máximo de 30 habilidades atingido.</Alert>
            )}

            {skills.length === 0 && (
                <Typography color="text.secondary" variant="body2">
                    Nenhuma habilidade adicionada. Clique em "Adicionar" para incluir uma habilidade
                    técnica.
                </Typography>
            )}

            {skills.map((skill, index) => (
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
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <TextField
                            required
                            fullWidth
                            label="Habilidade"
                            value={skill.name}
                            onChange={(e) => updateSkill(index, { name: e.target.value })}
                            error={!!fieldErrors[`skill_${index}_name`]}
                            helperText={fieldErrors[`skill_${index}_name`]}
                            size="small"
                        />
                        <FormControl sx={{ minWidth: 160 }} size="small">
                            <InputLabel id={`proficiency-label-${index}`}>Nível</InputLabel>
                            <Select
                                labelId={`proficiency-label-${index}`}
                                value={skill.proficiency}
                                label="Nível"
                                onChange={(e) => updateSkill(index, { proficiency: e.target.value as ProficiencyLevel })}
                            >
                                {PROFICIENCY_OPTIONS.map((opt) => (
                                    <MenuItem key={opt.value} value={opt.value}>
                                        {opt.label}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <IconButton
                            size="small"
                            color="error"
                            onClick={() => removeSkill(index)}
                            aria-label={`Remover habilidade ${index + 1}`}
                        >
                            <DeleteIcon fontSize="small" />
                        </IconButton>
                    </Box>
                </Paper>
            ))}
        </Stack>
    );
}
