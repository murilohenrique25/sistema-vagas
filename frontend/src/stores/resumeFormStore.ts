import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
    ExperienceCreate,
    EducationCreate,
    SkillCreate,
    CertificationCreate,
    LanguageCreate,
    DegreeLevel,
    ProficiencyLevel,
    FluencyLevel,
} from '../services/resumeService';

/**
 * Tracks which fields were filled by AI extraction.
 * Fields NOT filled by AI should be highlighted visually.
 */
export interface AiFilledFields {
    full_name: boolean;
    contact_email: boolean;
    phone: boolean;
    location: boolean;
    summary: boolean;
    experiences: boolean[];
    educations: boolean[];
    skills: boolean[];
    certifications: boolean[];
    languages: boolean[];
}

export interface ResumeFormData {
    full_name: string;
    contact_email: string;
    phone: string;
    location: string;
    summary: string;
    experiences: ExperienceCreate[];
    educations: EducationCreate[];
    skills: SkillCreate[];
    certifications: CertificationCreate[];
    languages: LanguageCreate[];
}

interface ResumeFormState {
    formData: ResumeFormData;
    aiFilledFields: AiFilledFields | null;
    isFromAiExtraction: boolean;
    isDirty: boolean;

    setFormData: (data: Partial<ResumeFormData>) => void;
    setFullFormData: (data: ResumeFormData) => void;
    setAiFilledFields: (fields: AiFilledFields) => void;
    setIsFromAiExtraction: (value: boolean) => void;
    resetForm: () => void;
    markDirty: () => void;

    // Section helpers
    addExperience: () => void;
    removeExperience: (index: number) => void;
    updateExperience: (index: number, data: Partial<ExperienceCreate>) => void;

    addEducation: () => void;
    removeEducation: (index: number) => void;
    updateEducation: (index: number, data: Partial<EducationCreate>) => void;

    addSkill: () => void;
    removeSkill: (index: number) => void;
    updateSkill: (index: number, data: Partial<SkillCreate>) => void;

    addCertification: () => void;
    removeCertification: (index: number) => void;
    updateCertification: (index: number, data: Partial<CertificationCreate>) => void;

    addLanguage: () => void;
    removeLanguage: (index: number) => void;
    updateLanguage: (index: number, data: Partial<LanguageCreate>) => void;
}

const emptyFormData: ResumeFormData = {
    full_name: '',
    contact_email: '',
    phone: '',
    location: '',
    summary: '',
    experiences: [],
    educations: [],
    skills: [],
    certifications: [],
    languages: [],
};

const emptyExperience: ExperienceCreate = {
    company: '',
    position: '',
    start_date: '',
    end_date: null,
    description: null,
};

const emptyEducation: EducationCreate = {
    institution: '',
    course: '',
    degree: 'bachelor' as DegreeLevel,
    start_date: '',
    end_date: null,
};

const emptySkill: SkillCreate = {
    name: '',
    proficiency: 'intermediate' as ProficiencyLevel,
};

const emptyCertification: CertificationCreate = {
    name: '',
    issuer: '',
    obtained_at: null,
};

const emptyLanguage: LanguageCreate = {
    language: '',
    fluency: 'intermediate' as FluencyLevel,
};

export const useResumeFormStore = create<ResumeFormState>()(
    persist(
        (set) => ({
            formData: { ...emptyFormData },
            aiFilledFields: null,
            isFromAiExtraction: false,
            isDirty: false,

            setFormData: (data) =>
                set((state) => ({
                    formData: { ...state.formData, ...data },
                    isDirty: true,
                })),

            setFullFormData: (data) =>
                set({ formData: data, isDirty: true }),

            setAiFilledFields: (fields) =>
                set({ aiFilledFields: fields }),

            setIsFromAiExtraction: (value) =>
                set({ isFromAiExtraction: value }),

            resetForm: () =>
                set({
                    formData: { ...emptyFormData },
                    aiFilledFields: null,
                    isFromAiExtraction: false,
                    isDirty: false,
                }),

            markDirty: () => set({ isDirty: true }),

            // Experiences
            addExperience: () =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        experiences: [...state.formData.experiences, { ...emptyExperience }],
                    },
                    isDirty: true,
                })),

            removeExperience: (index) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        experiences: state.formData.experiences.filter((_, i) => i !== index),
                    },
                    isDirty: true,
                })),

            updateExperience: (index, data) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        experiences: state.formData.experiences.map((exp, i) =>
                            i === index ? { ...exp, ...data } : exp
                        ),
                    },
                    isDirty: true,
                })),

            // Educations
            addEducation: () =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        educations: [...state.formData.educations, { ...emptyEducation }],
                    },
                    isDirty: true,
                })),

            removeEducation: (index) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        educations: state.formData.educations.filter((_, i) => i !== index),
                    },
                    isDirty: true,
                })),

            updateEducation: (index, data) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        educations: state.formData.educations.map((edu, i) =>
                            i === index ? { ...edu, ...data } : edu
                        ),
                    },
                    isDirty: true,
                })),

            // Skills
            addSkill: () =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        skills: [...state.formData.skills, { ...emptySkill }],
                    },
                    isDirty: true,
                })),

            removeSkill: (index) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        skills: state.formData.skills.filter((_, i) => i !== index),
                    },
                    isDirty: true,
                })),

            updateSkill: (index, data) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        skills: state.formData.skills.map((skill, i) =>
                            i === index ? { ...skill, ...data } : skill
                        ),
                    },
                    isDirty: true,
                })),

            // Certifications
            addCertification: () =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        certifications: [...state.formData.certifications, { ...emptyCertification }],
                    },
                    isDirty: true,
                })),

            removeCertification: (index) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        certifications: state.formData.certifications.filter((_, i) => i !== index),
                    },
                    isDirty: true,
                })),

            updateCertification: (index, data) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        certifications: state.formData.certifications.map((cert, i) =>
                            i === index ? { ...cert, ...data } : cert
                        ),
                    },
                    isDirty: true,
                })),

            // Languages
            addLanguage: () =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        languages: [...state.formData.languages, { ...emptyLanguage }],
                    },
                    isDirty: true,
                })),

            removeLanguage: (index) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        languages: state.formData.languages.filter((_, i) => i !== index),
                    },
                    isDirty: true,
                })),

            updateLanguage: (index, data) =>
                set((state) => ({
                    formData: {
                        ...state.formData,
                        languages: state.formData.languages.map((lang, i) =>
                            i === index ? { ...lang, ...data } : lang
                        ),
                    },
                    isDirty: true,
                })),
        }),
        {
            name: 'resume-form-storage',
            partialize: (state) => ({
                formData: state.formData,
                aiFilledFields: state.aiFilledFields,
                isFromAiExtraction: state.isFromAiExtraction,
                isDirty: state.isDirty,
            }),
        }
    )
);
