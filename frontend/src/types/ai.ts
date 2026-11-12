/**
 * AI-related TypeScript types matching the backend API contract.
 * Used for candidate analysis (employer) and job compatibility (candidate).
 */

export interface CandidateScore {
    candidate_id: string;
    candidate_name: string | null;
    score: number; // 0-100
    strengths: string[]; // 1-5 items
    concerns: string[]; // 1-5 items
    justification: string; // max 500 chars
}

export interface CandidateAnalysisResponse {
    job_id: string;
    results: CandidateScore[];
    tokens_consumed: number;
}

export interface JobMatch {
    job_id: string;
    job_title: string | null;
    company_name: string | null;
    compatibility_percentage: number; // 0-100
    justifications: string[];
    improvement_suggestions: string[]; // max 5 items
}

export interface JobMatchingResponse {
    candidate_id: string;
    matches: JobMatch[];
    tokens_consumed: number;
    message: string | null;
}
