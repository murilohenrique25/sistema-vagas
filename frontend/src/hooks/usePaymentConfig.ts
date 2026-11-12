import { useQuery } from '@tanstack/react-query';
import { getPublicPaymentConfig } from '../services/walletService';
import type { PublicPaymentConfig } from '../types/payment';

export const defaultPaymentConfig: PublicPaymentConfig = {
    currency: 'BRL',
    payments_enabled: true,
    minimum_wallet_topup: 1,
    prices: {
        resume_analysis: 5,
        job_compatibility: 5,
    },
};

export function usePaymentConfig(): PublicPaymentConfig {
    const { data } = useQuery({
        queryKey: ['payment-config'],
        queryFn: getPublicPaymentConfig,
        staleTime: 30 * 1000,
        refetchOnMount: 'always',
        refetchOnWindowFocus: true,
        retry: 1,
    });
    return data ?? defaultPaymentConfig;
}
