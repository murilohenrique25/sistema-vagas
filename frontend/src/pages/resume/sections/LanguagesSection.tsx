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
import type { FluencyLevel } from '../../../services/resumeService';

interface Props {
    fieldErrors: Record<string, string>;
}

const FLUENCY_OPTIONS: { value: FluencyLevel; label: string }[] = [
    { value: 'basic', label: 'Básico' },
    { value: 'intermediate', label: 'Intermediário' },
    { value: 'advanced', label: 'Avançado' },
    { value: 'native', label: 'Nativo' },
];

export default function LanguagesSection({ fieldErrors }: Props) {
    const {
        formData,
        addLanguage,
        removeLanguage,
        updateLanguage,
        aiFilledFields,
        isFromAiExtraction,
    } = useResumeFormStore();

    const languages = formData.languages;

    function isAiUnfilled(index: number): boolean {
        if (!isFromAiExtraction || !aiFilledFields) return false;
        return aiFilledFields.languages[index] === false;
    }

    return (
        <Stack spacing={3}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Idiomas</Typography>
                <Button
                    startIcon={<AddIcon />}
                    onClick={addLanguage}
                    disabled={languages.length >= 30}
                    size="small"
                >
                    Adicionar
                </Button>
            </Box>

            {languages.length >= 30 && (
                <Alert severity="info">Máximo de 30 idiomas atingido.</Alert>
            )}

            {languages.length === 0 && (
                <Typography color="text.secondary" variant="body2">
                    Nenhum idioma adicionado. Clique em "Adicionar" para incluir um idioma.
                </Typography>
            )}

            {languages.map((lang, index) => (
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
                            label="Idioma"
                            value={lang.language}
                            onChange={(e) => updateLanguage(index, { language: e.target.value })}
                            error={!!fieldErrors[`lang_${index}_language`]}
                            helperText={fieldErrors[`lang_${index}_language`]}
                            size="small"
                        />
                        <FormControl sx={{ minWidth: 160 }} size="small">
                            <InputLabel id={`fluency-label-${index}`}>Nível</InputLabel>
                            <Select
                                labelId={`fluency-label-${index}`}
                                value={lang.fluency}
                                label="Nível"
                                onChange={(e) => updateLanguage(index, { fluency: e.target.value as FluencyLevel })}
                            >
                                {FLUENCY_OPTIONS.map((opt) => (
                                    <MenuItem key={opt.value} value={opt.value}>
                                        {opt.label}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <IconButton
                            size="small"
                            color="error"
                            onClick={() => removeLanguage(index)}
                            aria-label={`Remover idioma ${index + 1}`}
                        >
                            <DeleteIcon fontSize="small" />
                        </IconButton>
                    </Box>
                </Paper>
            ))}
        </Stack>
    );
}
