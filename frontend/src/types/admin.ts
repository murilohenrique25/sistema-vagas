/**
 * Types for the admin panel.
 */

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

// Users
export interface AdminUser {
    id: string;
    name: string;
    email: string;
    role: 'employer' | 'candidate' | 'admin';
    is_active: boolean;
    created_at: string;
}

export interface AdminUserUpdate {
    name?: string;
    email?: string;
    role?: 'employer' | 'candidate' | 'admin';
}

// Companies
export interface AdminCompany {
    id: string;
    name: string;
    cnpj: string;
    email: string;
    status: 'active' | 'inactive';
    plan: string;
    created_at: string;
}

export interface AdminCompanyUpdate {
    name?: string;
    email?: string;
    status?: 'active' | 'inactive';
}

// Jobs
export interface AdminJob {
    id: string;
    title: string;
    company_name: string;
    status: 'draft' | 'active' | 'closed' | 'inactive';
    applications_count: number;
    created_at: string;
    deadline: string;
}

// Applications
export interface AdminApplication {
    id: string;
    candidate_name: string;
    job_title: string;
    company_name: string;
    status: string;
    created_at: string;
}

// Financials
export interface AdminTransaction {
    id: string;
    user_name: string;
    type: 'credit' | 'debit' | 'refund';
    amount: number;
    description: string;
    created_at: string;
}

export interface AdminPayment {
    id: string;
    user_name: string;
    method: 'pix' | 'credit_card' | 'checkout_pro';
    amount: number;
    status: 'pending' | 'confirmed' | 'failed' | 'expired';
    created_at: string;
}

export interface AdminRevenue {
    total_revenue: number;
    token_revenue: number;
    subscription_revenue: number;
    period_start: string;
    period_end: string;
}

// Audit Log
export interface AdminAuditLogEntry {
    id: string;
    admin_name: string;
    action: string;
    entity_type: string;
    entity_id: string;
    details: string;
    created_at: string;
}

// Metrics / KPIs
export type MetricPeriod = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';

export interface PlatformKpis {
    jobs_published: number;
    total_applications: number;
    hiring_rate: number;
    avg_time_to_hire_days: number;
    active_users: number;
    new_users: number;
}

export interface FinancialMetrics {
    total_revenue: number;
    token_revenue: number;
    subscription_revenue: number;
    avg_ticket: number;
    total_transactions: number;
}

export interface AiMetrics {
    total_analyses: number;
    token_consumption: number;
    avg_score: number;
    usage_rate_by_plan: Record<string, number>;
}
