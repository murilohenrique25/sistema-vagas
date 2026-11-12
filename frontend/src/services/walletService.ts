/** Wallet and Checkout Pro API calls. */
import api from './api';
import type {
    WalletBalance,
    WalletTransaction,
    PublicPaymentConfig,
    WalletCheckoutResponse,
    PaymentDetail,
} from '../types/payment';

export async function getPublicPaymentConfig(): Promise<PublicPaymentConfig> {
    const response = await api.get<PublicPaymentConfig>('/v1/payments/config');
    return response.data;
}

export async function getWalletBalance(): Promise<WalletBalance> {
    const response = await api.get<WalletBalance>('/v1/payments/wallet');
    return response.data;
}

export async function getWalletTransactions(): Promise<WalletTransaction[]> {
    const response = await api.get<WalletTransaction[]>('/v1/payments/wallet/transactions');
    return response.data;
}

export async function createWalletCheckout(amount: number): Promise<WalletCheckoutResponse> {
    const response = await api.post<WalletCheckoutResponse>('/v1/payments/checkout/wallet', { amount });
    return response.data;
}

export async function reconcileWalletCheckout(mercadoPagoPaymentId: string): Promise<PaymentDetail> {
    const response = await api.post<PaymentDetail>('/v1/payments/checkout/wallet/reconcile', {
        mercado_pago_payment_id: mercadoPagoPaymentId,
    });
    return response.data;
}

export async function getPaymentDetail(paymentId: string): Promise<PaymentDetail> {
    const response = await api.get<PaymentDetail>(`/v1/payments/${paymentId}`);
    return response.data;
}
