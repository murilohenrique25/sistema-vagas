/**
 * Global toast container that displays all active toasts as Material UI Snackbars.
 */
import { Alert, Snackbar, Stack } from '@mui/material';
import { useToastStore } from '../stores/toastStore';

export default function ToastContainer() {
    const { toasts, removeToast } = useToastStore();

    return (
        <Stack
            spacing={1}
            sx={{
                position: 'fixed',
                bottom: 24,
                right: 24,
                zIndex: 9999,
                maxWidth: 400,
            }}
        >
            {toasts.map((t) => (
                <Snackbar
                    key={t.id}
                    open={true}
                    anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                    sx={{ position: 'relative', bottom: 'auto', right: 'auto' }}
                >
                    <Alert
                        severity={t.severity}
                        variant="filled"
                        onClose={() => removeToast(t.id)}
                        sx={{
                            width: '100%',
                            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                            borderRadius: 2,
                        }}
                    >
                        {t.message}
                    </Alert>
                </Snackbar>
            ))}
        </Stack>
    );
}
