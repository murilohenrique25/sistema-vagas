/**
 * Application API service - handles all application-related API calls.
 */
import api from './api';
import type {
    Application,
    ApplicationStatus,
    PaginatedApplicationsResponse,
} from '../types/application';

/**
 * Create a new application (candidate applies to a job).
 */
export async function applyToJob(jobId: string): Promise<Application> {
    const response = await api.post<Application>('/v1/applications', {
        job_id: jobId,
    });
    return response.data;
}

/**
 * Get the current candidate's applications (paginated).
 */
export async function getMyApplications(
    page: number = 1,
    pageSize: number = 20
): Promise<PaginatedApplicationsResponse> {
    const response = await api.get<PaginatedApplicationsResponse>(
        '/v1/applications/me',
        { params: { page, page_size: pageSize } }
    );
    return response.data;
}

/**
 * Get applications for a specific job (employer view, paginated).
 */
export async function getJobApplications(
    jobId: string,
    page: number = 1,
    pageSize: number = 20
): Promise<PaginatedApplicationsResponse> {
    const response = await api.get<PaginatedApplicationsResponse>(
        `/v1/jobs/${jobId}/applications`,
        { params: { page, page_size: pageSize } }
    );
    return response.data;
}

/**
 * Change application status (employer workflow).
 */
export async function changeApplicationStatus(
    applicationId: string,
    status: ApplicationStatus
): Promise<Application> {
    const response = await api.patch<Application>(
        `/v1/applications/${applicationId}/status`,
        { status }
    );
    return response.data;
}

/**
 * Cancel an application (candidate action).
 */
export async function cancelApplication(
    applicationId: string
): Promise<Application> {
    const response = await api.patch<Application>(
        `/v1/applications/${applicationId}/cancel`
    );
    return response.data;
}

/**
 * Get count of applications with "received" status for a specific job.
 * Used for the real-time counter that updates every 60 seconds (requirement 7.7).
 */
export async function getReceivedCount(jobId: string): Promise<number> {
    const response = await api.get<PaginatedApplicationsResponse>(
        `/v1/jobs/${jobId}/applications`,
        { params: { page: 1, page_size: 100, status: 'received' } }
    );
    return response.data.total;
}


/**
 * Get a candidate's resume (employer view).
 */
export async function getCandidateResume(candidateId: string): Promise<unknown> {
    const response = await api.get(`/v1/resumes/candidate/${candidateId}`);
    return response.data;
}
