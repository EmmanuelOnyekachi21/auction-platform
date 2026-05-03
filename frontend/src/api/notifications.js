/**
 * notifications.js — In-app notification API actions
 */

import apiClient from './client';

export const getUnreadCount = async () => {
    const res = await apiClient.get('/notifications/unread-count');
    return res.data;
};

export const getNotifications = async ({ page = 1, limit = 10, unread_only = false } = {}) => {
    const res = await apiClient.get(`/notifications?page=${page}&limit=${limit}&unread_only=${unread_only}`);
    return res.data;
};

export const markNotificationRead = async (notificationId) => {
    const res = await apiClient.patch(`/notifications/${notificationId}/read`);
    return res.data;
};

export const markAllNotificationsRead = async () => {
    await apiClient.patch('/notifications/read-all');
};
