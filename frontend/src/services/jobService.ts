/**
 * Job API service - handles all job-related API calls.
 */
import api from './api';
import type {
    Job,
    JobCreate,
    JobUpdate,
    JobFilters,
    JobStatus,
    PaginatedResponse,
} from '../types/job';

export async function getJobs(filters: JobFilters = {}): Promise<PaginatedResponse<Job>> {
    const params: Record<string, string | number> = {};

    if (filters.search) params.q = filters.search;
    if (filters.modality) params.modality = filters.modality;
    if (filters.location) params.location = filters.location;
    if (filters.salary_min) params.salary_min = filters.salary_min;
    if (filters.salary_max) params.salary_max = filters.salary_max;
    if (filters.contract_type) params.contract_type = filters.contract_type;
    if (filters.sort_by) params.sort_by = filters.sort_by;
    if (filters.page) params.page = filters.page;
    if (filters.page_size) params.page_size = filters.page_size;

    const response = await api.get<PaginatedResponse<Job> | Job[]>('/v1/jobs', { params });
    const payload = response.data;
    if (Array.isArray(payload)) {
        return { items: payload, total: payload.length, page: 1, page_size: payload.length, total_pages: 1 };
    }
    return {
        items: Array.isArray(payload?.items) ? payload.items : [],
        total: Number(payload?.total ?? 0),
        page: Number(payload?.page ?? 1),
        page_size: Number(payload?.page_size ?? 20),
        total_pages: Number(payload?.total_pages ?? 1),
    };
}

export async function getFeaturedJobs(): Promise<Job[]> {
    const response = await api.get<PaginatedResponse<Job>>('/v1/jobs', {
        params: { highlighted: true, page_size: 10 },
    });
    return Array.isArray(response.data?.items) ? response.data.items : [];
}

export async function getJob(jobId: string): Promise<Job> {
    const response = await api.get<Job>(`/v1/jobs/${jobId}`);
    return response.data;
}

export async function createJob(data: JobCreate): Promise<Job> {
    const response = await api.post<Job>('/v1/jobs', data, { headers: { 'Idempotency-Key': crypto.randomUUID() } });
    return response.data;
}

export async function updateJob(jobId: string, data: JobUpdate): Promise<Job> {
    const response = await api.put<Job>(`/v1/jobs/${jobId}`, data);
    return response.data;
}

export async function duplicateJob(jobId: string): Promise<Job> {
    const response = await api.post<Job>(`/v1/jobs/${jobId}/duplicate`);
    return response.data;
}

export async function changeJobStatus(jobId: string, status: JobStatus): Promise<Job> {
    const response = await api.patch<Job>(`/v1/jobs/${jobId}/status`, { status });
    return response.data;
}

export async function extendJobDeadline(jobId: string, newDate: string): Promise<Job> {
    const response = await api.patch<Job>(`/v1/jobs/${jobId}/extend`, { new_date: newDate });
    return response.data;
}

export async function getEmployerJobs(filters: JobFilters = {}): Promise<PaginatedResponse<Job>> {
    const params: Record<string, string | number> = { my_jobs: 1 };

    if (filters.search) params.q = filters.search;
    if (filters.page) params.page = filters.page;
    if (filters.page_size) params.page_size = filters.page_size;

    const response = await api.get<PaginatedResponse<Job>>('/v1/jobs', { params });
    return response.data;
}

export async function reportJob(jobId:string, reason:string, details?:string):Promise<void>{
    await api.post(`/v1/jobs/${jobId}/reports`,{reason,details});
}
