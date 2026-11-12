import { TextField, Stack, Typography } from '@mui/material';
import type { SxProps, Theme } from '@mui/material/styles';
import { useResumeFormStore } from '../../../stores/resumeFormStore';

interface Props {
    fieldErrors: Record<string, string>;
}

export default function PersonalDataSection({ fieldErrors }: Props) {
    const { formData, setFormData, aiFilledFields, isFromAiExtraction } = useResumeFormStore();

    function getFieldSx(fieldName: string): SxProps<Theme> | undefined {
        if (!isFromAiExtraction || !aiFilledFields) return undefined;
        const isFilled = aiFilledFields[fieldName as keyof typeof aiFilledFields];
        if (isFilled === false) {
            return {
                '& .MuiOutlinedInput-root': {
                    backgroundColor: 'rgba(255, 193, 7, 0.08)',
                    '& fieldset': {
                        borderColor: 'warning.main',
                        borderWidth: 2,
                    },
                },
            };
        }
        return undefined;
    }

    function getHelperText(fieldName: string, errorKey: string) {
        if (fieldErrors[errorKey]) return fieldErrors[errorKey];
        if (isFromAiExtraction && aiFilledFields) {
            const isFilled = aiFilledFields[fieldName as keyof typeof aiFilledFields];
            if (isFilled === false) return 'Campo não preenchido pela IA — preencha manualmente';
        }
        return '';
    }

    return (
        <Stack spacing={3}>
            <Typography variant="h6">Dados Pessoais</Typography>

            <TextField
                required
                fullWidth
                label="Nome completo"
                value={formData.full_name}
                onChange={(e) => setFormData({ full_name: e.target.value })}
                error={!!fieldErrors.full_name}
                helperText={getHelperText('full_name', 'full_name')}
                slotProps={{ htmlInput: { maxLength: 200 } }}
                sx={getFieldSx('full_name')}
            />

            <TextField
                required
                fullWidth
                label="Email de contato"
                type="email"
                value={formData.contact_email}
                onChange={(e) => setFormData({ contact_email: e.target.value })}
                error={!!fieldErrors.contact_email}
                helperText={getHelperText('contact_email', 'contact_email')}
                sx={getFieldSx('contact_email')}
            />

            <TextField
                fullWidth
                label="Telefone"
                value={formData.phone}
                onChange={(e) => setFormData({ phone: e.target.value })}
                sx={getFieldSx('phone')}
                helperText={
                    isFromAiExtraction && aiFilledFields && !aiFilledFields.phone
                        ? 'Campo não preenchido pela IA — preencha manualmente'
                        : ''
                }
            />

            <TextField
                fullWidth
                label="Localização"
                placeholder="Ex: São Paulo, SP"
                value={formData.location}
                onChange={(e) => setFormData({ location: e.target.value })}
                sx={getFieldSx('location')}
                helperText={
                    isFromAiExtraction && aiFilledFields && !aiFilledFields.location
                        ? 'Campo não preenchido pela IA — preencha manualmente'
                        : ''
                }
            />

            <TextField
                fullWidth
                label="Resumo profissional"
                multiline
                rows={4}
                value={formData.summary}
                onChange={(e) => setFormData({ summary: e.target.value })}
                sx={getFieldSx('summary')}
                helperText={
                    isFromAiExtraction && aiFilledFields && !aiFilledFields.summary
                        ? 'Campo não preenchido pela IA — preencha manualmente'
                        : ''
                }
            />
        </Stack>
    );
}
