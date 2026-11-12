/**
 * Application-related TypeScript types matching the backend API contract.
 */

export type ApplicationStatus =
    | 'received'
    | 'in_review'
    | 'interview'
    | 'technical_test'
    | 'proposal'
    | 'hired'
    | 'rejected'
    | 'cancelled';

export interface Application {
    id: string;
    job_id: string;
    candidate_id: string;
    status: ApplicationStatus;
    applied_at: string;
    updated_at: string | null;
    job_title: string | null;
    company_name: string | null;
}

export interface PaginatedApplicationsResponse {
    items: Application[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
    received: 'Recebida',
    in_review: 'Em análise',
    interview: 'Entrevista',
    technical_test: 'Teste técnico',
    proposal: 'Proposta',
    hired: 'Contratado',
    rejected: 'Reprovado',
    cancelled: 'Cancelado',
};

export const APPLICATION_STATUS_COLORS: Record<
    ApplicationStatus,
    'default' | 'info' | 'primary' | 'secondary' | 'warning' | 'success' | 'error'
> = {
    received: 'default',
    in_review: 'info',
    interview: 'primary',
    technical_test: 'secondary',
    proposal: 'warning',
    hired: 'success',
    rejected: 'error',
    cancelled: 'default',
};

/**
 * Valid status transitions for the employer workflow.
 * Progressive: received → in_review → interview → technical_test → proposal → hired
 * Rejected: from any status except hired and cancelled
 * Cancelled: from any status except hired
 */
export const VALID_TRANSITIONS: Record<ApplicationStatus, ApplicationStatus[]> = {
    received: ['in_review', 'rejected', 'cancelled'],
    in_review: ['interview', 'rejected', 'cancelled'],
    interview: ['technical_test', 'rejected', 'cancelled'],
    technical_test: ['proposal', 'rejected', 'cancelled'],
    proposal: ['hired', 'rejected', 'cancelled'],
    hired: [],
    rejected: [],
    cancelled: [],
};
