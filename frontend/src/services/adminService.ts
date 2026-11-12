/**
 * Admin API service - handles all admin panel API calls.
 */
import api from './api';
import type {
    PaginatedResponse,
    AdminUser,
    AdminUserUpdate,
    AdminCompany,
    AdminCompanyUpdate,
    AdminJob,
    AdminApplication,
    AdminTransaction,
    AdminPayment,
    AdminRevenue,
    AdminAuditLogEntry,
    MetricPeriod,
    PlatformKpis,
    FinancialMetrics,
    AiMetrics,
} from '../types/admin';

// ─── Users ───────────────────────────────────────────────────────────────────

export async function getAdminUsers(
    page: number = 1,
    pageSize: number = 20,
    filters?: { role?: string; status?: string; search?: string }
): Promise<PaginatedResponse<AdminUser>> {
    const response = await api.get<PaginatedResponse<AdminUser>>('/v1/admin/users', {
        params: { page, page_size: pageSize, ...filters },
    });
    return response.data;
}

export async function updateAdminUser(
    id: string,
    data: AdminUserUpdate
): Promise<AdminUser> {
    const response = await api.patch<AdminUser>(`/v1/admin/users/${id}`, data);
    return response.data;
}

export async function activateUser(id: string): Promise<void> {
    await api.post(`/v1/admin/users/${id}/activate`);
}

export async function deactivateUser(id: string): Promise<void> {
    await api.post(`/v1/admin/users/${id}/deactivate`);
}

// ─── Companies ───────────────────────────────────────────────────────────────

export async function getAdminCompanies(
    page: number = 1,
    pageSize: number = 20
): Promise<PaginatedResponse<AdminCompany>> {
    const response = await api.get<PaginatedResponse<AdminCompany>>('/v1/admin/companies', {
        params: { page, page_size: pageSize },
    });
    return response.data;
}

export async function updateAdminCompany(
    id: string,
    data: AdminCompanyUpdate
): Promise<AdminCompany> {
    const response = await api.patch<AdminCompany>(`/v1/admin/companies/${id}`, data);
    return response.data;
}

// ─── Jobs ────────────────────────────────────────────────────────────────────

export async function getAdminJobs(
    page: number = 1,
    pageSize: number = 20,
    filters?: { status?: string }
): Promise<PaginatedResponse<AdminJob>> {
    const response = await api.get<PaginatedResponse<AdminJob>>('/v1/admin/jobs', {
        params: { page, page_size: pageSize, ...filters },
    });
    return response.data;
}

export async function updateJobStatus(
    id: string,
    status: string
): Promise<void> {
    await api.patch(`/v1/admin/jobs/${id}/status`, { status });
}

// ─── Applications ────────────────────────────────────────────────────────────

export async function getAdminApplications(
    page: number = 1,
    pageSize: number = 20
): Promise<PaginatedResponse<AdminApplication>> {
    const response = await api.get<PaginatedResponse<AdminApplication>>(
        '/v1/admin/applications',
        { params: { page, page_size: pageSize } }
    );
    return response.data;
}

// ─── Financials ──────────────────────────────────────────────────────────────

export async function getAdminTransactions(
    page: number = 1,
    pageSize: number = 20
): Promise<PaginatedResponse<AdminTransaction>> {
    const response = await api.get<PaginatedResponse<AdminTransaction>>(
        '/v1/admin/financials/transactions',
        { params: { page, page_size: pageSize } }
    );
    return response.data;
}

export async function getAdminPayments(
    page: number = 1,
    pageSize: number = 20
): Promise<PaginatedResponse<AdminPayment>> {
    const response = await api.get<PaginatedResponse<AdminPayment>>(
        '/v1/admin/financials/payments',
        { params: { page, page_size: pageSize } }
    );
    return response.data;
}

export async function getAdminRevenue(
    startDate: string,
    endDate: string
): Promise<AdminRevenue> {
    const response = await api.get<AdminRevenue>('/v1/admin/financials/revenue', {
        params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
}

// ─── Token Config ────────────────────────────────────────────────────────────


// ─── Audit Log ───────────────────────────────────────────────────────────────

export async function getAdminAuditLogs(
    page: number = 1,
    pageSize: number = 50
): Promise<PaginatedResponse<AdminAuditLogEntry>> {
    const response = await api.get<PaginatedResponse<AdminAuditLogEntry>>(
        '/v1/admin/audit-logs',
        { params: { page, page_size: Math.min(pageSize, 100) } }
    );
    return response.data;
}

// ─── Metrics / KPIs ──────────────────────────────────────────────────────────

export async function getPlatformKpis(
    period: MetricPeriod = 'monthly'
): Promise<PlatformKpis> {
    const response = await api.get<PlatformKpis>('/v1/admin/metrics/kpis', {
        params: { period },
    });
    return response.data;
}

export async function getFinancialMetrics(
    period: MetricPeriod = 'monthly'
): Promise<FinancialMetrics> {
    const response = await api.get<FinancialMetrics>('/v1/admin/metrics/financial', {
        params: { period },
    });
    return response.data;
}

export async function getAiMetrics(
    period: MetricPeriod = 'monthly'
): Promise<AiMetrics> {
    const response = await api.get<AiMetrics>('/v1/admin/metrics/ai', {
        params: { period },
    });
    return response.data;
}

// ─── Payment Settings ────────────────────────────────────────────────────────

export interface PaymentSettings {
    exists: boolean;
    pix_key_type?: string | null;
    pix_key?: string | null;
    pix_beneficiary_name?: string | null;
    gateway_provider?: string | null;
    gateway_api_key?: string | null;
    gateway_secret_key?: string | null;
    gateway_webhook_url?: string | null;
    bank_name?: string | null;
    bank_agency?: string | null;
    bank_account?: string | null;
    bank_account_type?: string | null;
    resume_analysis_price?: number;
    job_compatibility_price?: number;
    minimum_wallet_topup?: number;
    is_active?: boolean;
    updated_at?: string | null;
}

export async function getPaymentSettings(): Promise<PaymentSettings> {
    const response = await api.get<PaymentSettings>('/v1/admin/payment-settings');
    return response.data;
}

export async function updatePaymentSettings(
    data: Partial<PaymentSettings>
): Promise<{ message: string }> {
    const response = await api.put<{ message: string }>('/v1/admin/payment-settings', data);
    return response.data;
}
export interface JobReport { id:string; job_id:string; reporter_id:string; reason:string; details:string|null; status:string; created_at:string }
export async function getJobReports(){return (await api.get<JobReport[]>('/v1/admin/job-reports')).data;}
export async function updateJobReport(id:string,status:'reviewed'|'dismissed'|'actioned'){return (await api.patch<JobReport>(`/v1/admin/job-reports/${id}`,{status})).data;}

// ─── CSV Export ──────────────────────────────────────────────────────────────

export async function exportCsv(entity: string): Promise<void> {
    const response = await api.get(`/v1/admin/export/${entity}`, {
        params: { format: 'csv' },
        responseType: 'blob',
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${entity}_export.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
}
