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

export default function CertificationsSection({ fieldErrors }: Props) {
    const {
        formData,
        addCertification,
        removeCertification,
        updateCertification,
        aiFilledFields,
        isFromAiExtraction,
    } = useResumeFormStore();

    const certifications = formData.certifications;

    function isAiUnfilled(index: number): boolean {
        if (!isFromAiExtraction || !aiFilledFields) return false;
        return aiFilledFields.certifications[index] === false;
    }

    return (
        <Stack spacing={3}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Certificações</Typography>
                <Button
                    startIcon={<AddIcon />}
                    onClick={addCertification}
                    disabled={certifications.length >= 30}
                    size="small"
                >
                    Adicionar
                </Button>
            </Box>

            {certifications.length >= 30 && (
                <Alert severity="info">Máximo de 30 certificações atingido.</Alert>
            )}

            {certifications.length === 0 && (
                <Typography color="text.secondary" variant="body2">
                    Nenhuma certificação adicionada. Clique em "Adicionar" para incluir uma
                    certificação.
                </Typography>
            )}

            {certifications.map((cert, index) => (
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
                            Certificação {index + 1}
                        </Typography>
                        <IconButton
                            size="small"
                            color="error"
                            onClick={() => removeCertification(index)}
                            aria-label={`Remover certificação ${index + 1}`}
                        >
                            <DeleteIcon fontSize="small" />
                        </IconButton>
                    </Box>

                    <Stack spacing={2}>
                        <TextField
                            required
                            fullWidth
                            label="Nome da certificação"
                            value={cert.name}
                            onChange={(e) => updateCertification(index, { name: e.target.value })}
                            error={!!fieldErrors[`cert_${index}_name`]}
                            helperText={fieldErrors[`cert_${index}_name`]}
                            size="small"
                        />
                        <TextField
                            required
                            fullWidth
                            label="Instituição emissora"
                            value={cert.issuer}
                            onChange={(e) => updateCertification(index, { issuer: e.target.value })}
                            error={!!fieldErrors[`cert_${index}_issuer`]}
                            helperText={fieldErrors[`cert_${index}_issuer`]}
                            size="small"
                        />
                        <TextField
                            fullWidth
                            label="Data de obtenção"
                            type="date"
                            value={cert.obtained_at || ''}
                            onChange={(e) => updateCertification(index, { obtained_at: e.target.value || null })}
                            slotProps={{ inputLabel: { shrink: true } }}
                            size="small"
                        />
                    </Stack>
                </Paper>
            ))}
        </Stack>
    );
}
