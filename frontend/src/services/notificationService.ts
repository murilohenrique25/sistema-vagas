/**
 * Notification API service - handles all notification-related API calls.
 */
import api from './api';
import type {
    PaginatedNotificationsResponse,
    UnreadCountResponse,
    Notification,
} from '../types/notification';

/**
 * Get paginated list of notifications (newest first).
 */
export async function getNotifications(
    page: number = 1,
    pageSize: number = 20
): Promise<PaginatedNotificationsResponse> {
    const response = await api.get<PaginatedNotificationsResponse>(
        '/v1/notifications',
        { params: { page, page_size: pageSize } }
    );
    return response.data;
}

/**
 * Get count of unread notifications.
 */
export async function getUnreadCount(): Promise<UnreadCountResponse> {
    const response = await api.get<UnreadCountResponse>(
        '/v1/notifications/unread-count'
    );
    return response.data;
}

/**
 * Mark a specific notification as read.
 */
export async function markAsRead(notificationId: string): Promise<Notification> {
    const response = await api.patch<Notification>(
        `/v1/notifications/${notificationId}/read`
    );
    return response.data;
}

/**
 * Mark all notifications as read.
 */
export async function markAllAsRead(): Promise<void> {
    await api.patch('/v1/notifications/read-all');
}
