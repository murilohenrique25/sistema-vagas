import api, { API_URL } from './api';

export interface RegisterPayload {
    name: string;
    email: string;
    password: string;
    role: 'employer' | 'candidate';
    accept_terms: true;
    accept_privacy: true;
}

export interface LoginPayload {
    email: string;
    password: string;
    otp_code?: string;
}

export async function setupAdmin2FA() { return (await api.post<{secret:string;otpauth_uri:string}>('/v1/auth/2fa/setup')).data; }
export async function confirmAdmin2FA(code:string) { return (await api.post<{message:string}>('/v1/auth/2fa/confirm',{code})).data; }

export interface AuthUser {
    id: string;
    email: string;
    name: string;
    role: 'employer' | 'candidate' | 'admin';
}

export interface AuthResponse {
    access_token: string;
    refresh_token: string;
    user: AuthUser;
}

interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

/**
 * Decode a JWT payload without verifying signature (client-side only).
 */
function decodeJwtPayload(token: string): Record<string, unknown> {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
        atob(base64)
            .split('')
            .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
            .join('')
    );
    return JSON.parse(jsonPayload);
}

export async function register(payload: RegisterPayload): Promise<{ message: string; email: string }> {
    const response = await api.post<{ message: string; email: string }>('/v1/auth/register', payload);
    return response.data;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
    const response = await api.post<TokenResponse>('/v1/auth/login', payload);
    const data = response.data;
    const decoded = decodeJwtPayload(data.access_token);

    return {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        user: {
            id: decoded.sub as string,
            email: payload.email,
            name: '',
            role: decoded.role as 'employer' | 'candidate' | 'admin',
        },
    };
}

export async function refreshToken(refresh_token: string): Promise<{ access_token: string }> {
    const response = await api.post<{ access_token: string }>('/v1/auth/refresh', {
        refresh_token,
    });
    return response.data;
}

export function oauthRedirect(provider: 'google' | 'linkedin'): void {
    window.location.href = `${API_URL}/v1/auth/oauth/${provider}`;
}

export async function requestEmailVerification(email: string): Promise<string> {
    const response = await api.post<{ message: string }>('/v1/auth/email-verification/request', { email });
    return response.data.message;
}

export async function confirmEmailVerification(token: string): Promise<string> {
    const response = await api.post<{ message: string }>('/v1/auth/email-verification/confirm', { token });
    return response.data.message;
}

export async function requestPasswordReset(email: string): Promise<string> {
    const response = await api.post<{ message: string }>('/v1/auth/password/forgot', { email });
    return response.data.message;
}

export async function resetPassword(token: string, newPassword: string): Promise<string> {
    const response = await api.post<{ message: string }>('/v1/auth/password/reset', {
        token,
        new_password: newPassword,
    });
    return response.data.message;
}

export async function deleteAccount(confirmation: string, password?: string): Promise<string> {
    const response = await api.delete<{ message: string }>('/v1/account', {
        data: { confirmation, password: password || null },
    });
    return response.data.message;
}
