import api from './api';

export interface CompanyProfile {
    id?: string;
    name: string;
    legal_name: string;
    cnpj: string;
    description: string;
    website: string;
    email: string;
    phone: string;
    industry: string;
    company_size: string;
    city: string;
    state: string;
    address: string;
    logo_url: string;
    is_active?: boolean;
    cnpj_status?: string | null;
    cnpj_checked_at?: string | null;
    cnpj_source?: string | null;
}

export interface CnpjLookup {
    cnpj: string; legal_name: string; name: string; status: string;
    industry?: string | null; phone?: string | null; city?: string | null;
    state?: string | null; address?: string | null; source: string;
}

export async function getMyCompany(): Promise<CompanyProfile | null> {
    try {
        return (await api.get<CompanyProfile>('/v1/companies/me')).data;
    } catch (error: unknown) {
        const status = (error as { response?: { status?: number } }).response?.status;
        if (status === 404) return null;
        throw error;
    }
}

export async function saveMyCompany(data: CompanyProfile): Promise<CompanyProfile> {
    return (await api.put<CompanyProfile>('/v1/companies/me', data)).data;
}

export async function lookupCnpj(cnpj: string): Promise<CnpjLookup> {
    const digits = cnpj.replace(/\D/g, '');
    return (await api.get<CnpjLookup>(`/v1/companies/cnpj/${digits}`)).data;
}
