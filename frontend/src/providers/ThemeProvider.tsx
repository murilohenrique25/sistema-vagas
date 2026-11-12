import { ThemeProvider as MuiThemeProvider, createTheme, CssBaseline } from '@mui/material';
import type { ReactNode } from 'react';

const theme = createTheme({
    palette: {
        primary: {
            main: '#283593',
            light: '#5c6bc0',
            dark: '#1a237e',
        },
        secondary: {
            main: '#00bcd4',
            light: '#4dd0e1',
            dark: '#0097a7',
        },
        background: {
            default: '#f5f7fa',
            paper: '#ffffff',
        },
        text: {
            primary: '#1a2027',
            secondary: '#546e7a',
        },
    },
    typography: {
        fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
        h1: { fontWeight: 700 },
        h2: { fontWeight: 700 },
        h3: { fontWeight: 700 },
        h4: { fontWeight: 600 },
        h5: { fontWeight: 600 },
        h6: { fontWeight: 600 },
        subtitle1: { fontWeight: 500 },
        button: { fontWeight: 600, textTransform: 'none' },
    },
    shape: {
        borderRadius: 12,
    },
    shadows: [
        'none',
        '0px 2px 4px rgba(0,0,0,0.05)',
        '0px 4px 8px rgba(0,0,0,0.06)',
        '0px 6px 12px rgba(0,0,0,0.07)',
        '0px 8px 16px rgba(0,0,0,0.08)',
        '0px 10px 20px rgba(0,0,0,0.09)',
        '0px 12px 24px rgba(0,0,0,0.10)',
        '0px 14px 28px rgba(0,0,0,0.11)',
        '0px 16px 32px rgba(0,0,0,0.12)',
        '0px 18px 36px rgba(0,0,0,0.13)',
        '0px 20px 40px rgba(0,0,0,0.14)',
        '0px 22px 44px rgba(0,0,0,0.15)',
        '0px 24px 48px rgba(0,0,0,0.16)',
        '0px 26px 52px rgba(0,0,0,0.17)',
        '0px 28px 56px rgba(0,0,0,0.18)',
        '0px 30px 60px rgba(0,0,0,0.19)',
        '0px 32px 64px rgba(0,0,0,0.20)',
        '0px 34px 68px rgba(0,0,0,0.21)',
        '0px 36px 72px rgba(0,0,0,0.22)',
        '0px 38px 76px rgba(0,0,0,0.23)',
        '0px 40px 80px rgba(0,0,0,0.24)',
        '0px 42px 84px rgba(0,0,0,0.25)',
        '0px 44px 88px rgba(0,0,0,0.26)',
        '0px 46px 92px rgba(0,0,0,0.27)',
        '0px 48px 96px rgba(0,0,0,0.28)',
    ],
    components: {
        MuiAppBar: {
            styleOverrides: {
                root: {
                    background: 'linear-gradient(135deg, #1a237e 0%, #1565c0 100%)',
                    boxShadow: '0 4px 20px rgba(26, 35, 126, 0.3)',
                    borderRadius: 0,
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: 16,
                    boxShadow: '0px 4px 20px rgba(0, 0, 0, 0.06)',
                    border: '1px solid rgba(0, 0, 0, 0.04)',
                    transition: 'transform 0.25s ease, box-shadow 0.25s ease',
                    '&:hover': {
                        transform: 'translateY(-4px)',
                        boxShadow: '0px 12px 32px rgba(26, 35, 126, 0.12)',
                    },
                },
            },
        },
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: 10,
                    padding: '10px 24px',
                    fontWeight: 600,
                },
                contained: {
                    boxShadow: '0 4px 14px rgba(40, 53, 147, 0.25)',
                    '&:hover': {
                        boxShadow: '0 6px 20px rgba(40, 53, 147, 0.35)',
                    },
                },
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: {
                    borderRadius: 16,
                },
            },
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    '& .MuiOutlinedInput-root': {
                        borderRadius: 10,
                    },
                },
            },
        },
    },
});

interface ThemeProviderProps {
    children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
    return (
        <MuiThemeProvider theme={theme}>
            <CssBaseline />
            {children}
        </MuiThemeProvider>
    );
}
