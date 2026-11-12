export type PaymentMethod = 'checkout_pro';
export type PaymentStatus = 'pending' | 'confirmed' | 'failed' | 'expired' | 'cancelled';
export type ServicePaymentPurpose = 'resume_analysis' | 'job_compatibility' | 'wallet_topup';

export interface PublicPaymentConfig {
    currency: 'BRL';
    payments_enabled: boolean;
    minimum_wallet_topup: number;
    prices: {
        resume_analysis: number;
        job_compatibility: number;
    };
}

export interface WalletBalance { balance: number; currency: 'BRL'; }
export interface WalletTransaction {
    id: string;
    amount: number;
    balance_after: number;
    type: 'credit' | 'debit';
    reason: string;
    reference_id: string | null;
    created_at: string;
}

export interface WalletCheckoutResponse {
    payment_id: string;
    preference_id: string;
    checkout_url: string;
    amount: number;
    status: PaymentStatus;
}

export interface PaymentDetail {
    id: string;
    amount: number;
    status: PaymentStatus;
    confirmed_at: string | null;
}
