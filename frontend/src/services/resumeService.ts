import api from './api';

// Types matching backend schemas

export interface ExperienceCreate {
    company: string;
    position: string;
    start_date: string;
    end_date?: string | null;
    description?: string | null;
}

export interface EducationCreate {
    institution: string;
    course: string;
    degree: DegreeLevel;
    start_date: string;
    end_date?: string | null;
}

export interface SkillCreate {
    name: string;
    proficiency: ProficiencyLevel;
}

export interface CertificationCreate {
    name: string;
    issuer: string;
    obtained_at?: string | null;
}

export interface LanguageCreate {
    language: string;
    fluency: FluencyLevel;
}

export interface ResumeCreate {
    full_name: string;
    contact_email: string;
    phone?: string | null;
    location?: string | null;
    summary?: string | null;
    experiences: ExperienceCreate[];
    educations: EducationCreate[];
    skills: SkillCreate[];
    certifications: CertificationCreate[];
    languages: LanguageCreate[];
}

export interface ResumeResponse {
    id: string;
    user_id: string;
    full_name: string;
    contact_email: string | null;
    phone: string | null;
    location: string | null;
    summary: string | null;
    experiences: ExperienceResponse[];
    educations: EducationResponse[];
    skills: SkillResponse[];
    certifications: CertificationResponse[];
    languages: LanguageResponse[];
    created_at: string;
    updated_at: string;
}

export interface ExperienceResponse {
    id: string;
    company: string;
    position: string;
    start_date: string;
    end_date: string | null;
    description: string | null;
    sort_order: number;
}

export interface EducationResponse {
    id: string;
    institution: string;
    course: string;
    degree: DegreeLevel;
    start_date: string;
    end_date: string | null;
    sort_order: number;
}

export interface SkillResponse {
    id: string;
    name: string;
    proficiency: ProficiencyLevel;
}

export interface CertificationResponse {
    id: string;
    name: string;
    issuer: string;
    obtained_at: string | null;
}

export interface LanguageResponse {
    id: string;
    language: string;
    fluency: FluencyLevel;
}

export type DegreeLevel = 'high_school' | 'bachelor' | 'master' | 'doctorate' | 'technical';
export type ProficiencyLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert';
export type FluencyLevel = 'basic' | 'intermediate' | 'advanced' | 'native';

// Extracted resume from AI PDF processing
export interface ExtractedResume {
    personal_data: {
        full_name: string | null;
        contact_email: string | null;
        phone: string | null;
        location: string | null;
    };
    experiences: Array<{
        company: string | null;
        position: string | null;
        start_date: string | null;
        end_date: string | null;
        description: string | null;
    }>;
    educations: Array<{
        institution: string | null;
        course: string | null;
        degree: string | null;
        start_date: string | null;
        end_date: string | null;
    }>;
    skills: Array<{
        name: string | null;
        proficiency: string | null;
    }>;
    certifications: Array<{
        name: string | null;
        issuer: string | null;
        obtained_at: string | null;
    }>;
    languages: Array<{
        language: string | null;
        fluency: string | null;
    }>;
}

export interface PdfImportResponse {
    extracted_data: ExtractedResume;
    message: string;
}

/**
 * Get the current user's resume.
 */
export async function getMyResume(): Promise<ResumeResponse> {
    const response = await api.get<ResumeResponse>('/v1/resumes/me');
    return response.data;
}

/**
 * Create or update the current user's resume.
 */
export async function createOrUpdateResume(data: ResumeCreate): Promise<ResumeResponse> {
    const response = await api.post<ResumeResponse>('/v1/resumes', data);
    return response.data;
}

/**
 * Import a resume from PDF using AI extraction.
 * Returns extracted data for review before saving.
 */
export async function importResumePdf(
    file: File,
    onProgress?: (progress: number) => void
): Promise<PdfImportResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<PdfImportResponse>('/v1/resumes/import-pdf', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
        timeout: 65000, // 65s to account for the 60s backend timeout
        onUploadProgress: (progressEvent) => {
            if (onProgress && progressEvent.total) {
                const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onProgress(percent);
            }
        },
    });
    return response.data;
}
