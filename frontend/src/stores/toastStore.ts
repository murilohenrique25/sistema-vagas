/**
 * Global toast/snackbar store using Zustand.
 * Provides feedback messages to the user for all system actions.
 */
import { create } from 'zustand';

export type ToastSeverity = 'success' | 'error' | 'warning' | 'info';

interface Toast {
    id: string;
    message: string;
    severity: ToastSeverity;
}

interface ToastState {
    toasts: Toast[];
    addToast: (message: string, severity?: ToastSeverity) => void;
    removeToast: (id: string) => void;
}

let toastCounter = 0;

export const useToastStore = create<ToastState>()((set) => ({
    toasts: [],
    addToast: (message, severity = 'info') => {
        const id = `toast-${++toastCounter}`;
        set((state) => ({
            toasts: [...state.toasts, { id, message, severity }],
        }));
        // Auto-remove after 5 seconds
        setTimeout(() => {
            set((state) => ({
                toasts: state.toasts.filter((t) => t.id !== id),
            }));
        }, 5000);
    },
    removeToast: (id) =>
        set((state) => ({
            toasts: state.toasts.filter((t) => t.id !== id),
        })),
}));

// Helper functions for easy use
export const toast = {
    success: (message: string) => useToastStore.getState().addToast(message, 'success'),
    error: (message: string) => useToastStore.getState().addToast(message, 'error'),
    warning: (message: string) => useToastStore.getState().addToast(message, 'warning'),
    info: (message: string) => useToastStore.getState().addToast(message, 'info'),
};
