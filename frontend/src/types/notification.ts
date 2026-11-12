/**
 * Notification-related TypeScript types matching the backend API contract.
 */

export type NotificationChannel = 'platform' | 'email' | 'both';
export type DeliveryStatus = 'pending' | 'sent' | 'failed';

export interface Notification {
    id: string;
    user_id: string;
    title: string;
    message: string;
    channel: NotificationChannel;
    is_read: boolean;
    delivery_attempts: number;
    delivery_status: DeliveryStatus;
    sent_at: string | null;
    read_at: string | null;
    created_at: string;
}

export interface PaginatedNotificationsResponse {
    items: Notification[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface UnreadCountResponse {
    unread_count: number;
}
