/**
 * Job-related TypeScript types matching the backend API contract.
 */

export type JobModality = 'remote' | 'hybrid' | 'onsite';
export type ContractType = 'clt' | 'pj' | 'temporary' | 'internship';
export type JobStatus = 'active' | 'inactive' | 'closed' | 'draft';

export interface Job {
    id: string;
    company_id: string;
    title: string;
    modality: JobModality;
    location: string | null;
    responsibilities: string | null;
    required_skills: string | null;
    optional_skills: string | null;
    benefits: string | null;
    contract_type: ContractType;
    salary_min: number | null;
    salary_max: number | null;
    status: JobStatus;
    deadline: string | null;
    created_at: string;
    updated_at: string | null;
    is_highlighted?: boolean;
    company_name?: string;
}

export interface JobCreate {
    title: string;
    modality: JobModality;
    location: string;
    responsibilities: string;
    required_skills: string;
    contract_type: ContractType;
    deadline: string;
    optional_skills?: string;
    benefits?: string;
    salary_min?: number;
    salary_max?: number;
}

export interface JobUpdate {
    title?: string;
    modality?: JobModality;
    location?: string;
    responsibilities?: string;
    required_skills?: string;
    contract_type?: ContractType;
    deadline?: string;
    optional_skills?: string;
    benefits?: string;
    salary_min?: number;
    salary_max?: number;
}

export interface JobFilters {
    search?: string;
    modality?: JobModality;
    location?: string;
    salary_min?: number;
    salary_max?: number;
    contract_type?: ContractType;
    sort_by?: 'date' | 'salary' | 'relevance';
    page?: number;
    page_size?: number;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export const MODALITY_LABELS: Record<JobModality, string> = {
    remote: 'Remoto',
    hybrid: 'Híbrido',
    onsite: 'Presencial',
};

export const CONTRACT_TYPE_LABELS: Record<ContractType, string> = {
    clt: 'CLT',
    pj: 'PJ',
    temporary: 'Temporário',
    internship: 'Estágio',
};

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
    active: 'Ativa',
    inactive: 'Inativa',
    closed: 'Encerrada',
    draft: 'Rascunho',
};
