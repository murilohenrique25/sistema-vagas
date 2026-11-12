/**
 * AI API service - handles AI analysis and job matching API calls.
 * Requirements: 8.1, 8.2, 9.1, 9.2, 9.3
 */
import api from './api';
import type { CandidateAnalysisResponse, JobMatchingResponse } from '../types/ai';

/**
 * Analyze candidates for a specific job (employer).
 * POST /v1/ai/analyze-candidates
 */
export async function analyzeCandidates(jobId: string): Promise<CandidateAnalysisResponse> {
    const response = await api.post<CandidateAnalysisResponse>('/v1/ai/analyze-candidates', {
        job_id: jobId,
    }, { headers: { 'Idempotency-Key': crypto.randomUUID() } });
    return response.data;
}

/**
 * Get job compatibility analysis for the authenticated candidate.
 * POST /v1/ai/job-matching
 */
export async function getJobCompatibility(): Promise<JobMatchingResponse> {
    const response = await api.post<JobMatchingResponse>('/v1/ai/job-matching', undefined, { headers: { 'Idempotency-Key': crypto.randomUUID() } });
    return response.data;
}
