/**
 * orders.js — Order API actions
 *
 * All order-related API calls for the KaraKaja marketplace.
 * Integrates with the configured apiClient (handles auth token injection).
 */

import apiClient from './client';

/**
 * Fetch paginated list of user's orders (as buyer or seller).
 * GET /api/v1/users/me/orders
 * @param {{ role: string, page?: number, limit?: number }} params
 */
export const getMyOrders = async ({ role, page = 1, limit = 20 }) => {
    const query = new URLSearchParams();
    query.set('role', role);
    query.set('page', String(page));
    query.set('limit', String(limit));
    const response = await apiClient.get(`/users/me/orders?${query.toString()}`);
    return response.data;
};

/**
 * Fetch a single order by its ID.
 * GET /api/v1/orders/{orderId}
 * @param {string} orderId
 */
export const getOrder = async (orderId) => {
    const response = await apiClient.get(`/orders/${orderId}`);
    return response.data;
};

/**
 * Update order status to 'shipped'.
 * PATCH /api/v1/orders/{orderId}/ship
 * @param {string} orderId
 * @param {{ tracking_number?: string }} data
 */
export const shipOrder = async (orderId, data) => {
    const response = await apiClient.patch(`/orders/${orderId}/ship`, data);
    return response.data;
};

/**
 * Confirm order delivery.
 * PATCH /api/v1/orders/{orderId}/confirm-delivery
 * @param {string} orderId
 */
export const confirmDelivery = async (orderId) => {
    const response = await apiClient.patch(`/orders/${orderId}/confirm-delivery`);
    return response.data;
};

/**
 * Raise a dispute for an order.
 * POST /api/v1/orders/{orderId}/dispute
 * @param {string} orderId
 * @param {{ title: string, description: string }} data
 */
export const raiseDispute = async (orderId, data) => {
    const response = await apiClient.post(`/orders/${orderId}/dispute`, data);
    return response.data;
};

/**
 * Fetch a single dispute by its ID.
 * GET /api/v1/disputes/{disputeId}
 * @param {string} disputeId
 */
export const getDispute = async (disputeId) => {
    const response = await apiClient.get(`/disputes/${disputeId}`);
    return response.data;
};

/**
 * Upload a file as evidence for a dispute.
 * POST /api/v1/disputes/{disputeId}/evidence/upload
 * @param {string} disputeId
 * @param {File} file
 * @param {string|null} description
 */
export const uploadEvidenceFile = async (disputeId, file, description = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (description) formData.append('description', description);
    const response = await apiClient.post(
        `/disputes/${disputeId}/evidence/upload`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
};

/**
 * Cancel an order (buyer only, after shipping deadline passed).
 * PATCH /api/v1/orders/{orderId}/cancel
 */
export const cancelOrder = async (orderId) => {
    const response = await apiClient.patch(`/orders/${orderId}/cancel`);
    return response.data;
};

/**
 * Mark a dispute as under review (admin only).
 * PATCH /api/v1/disputes/{disputeId}/mark-under-review
 */
export const markDisputeUnderReview = async (disputeId) => {
    const response = await apiClient.patch(`/disputes/${disputeId}/mark-under-review`);
    return response.data;
};

/**
 * Resolve a dispute (admin only).
 * PATCH /api/v1/disputes/{disputeId}/resolve
 * @param {string} disputeId
 * @param {{ resolution: 'in_favour_of_buyer'|'in_favour_of_seller', resolution_notes: string }} data
 */
export const resolveDispute = async (disputeId, data) => {
    const response = await apiClient.patch(`/disputes/${disputeId}/resolve`, data);
    return response.data;
};

/**
 * Fetch all disputes where the user is either the buyer or the seller.
 * GET /api/v1/users/me/disputes
 */
export const getMyDisputes = async ({ page = 1, limit = 20 } = {}) => {
    const response = await apiClient.get(`/users/me/disputes?page=${page}&limit=${limit}`);
    return response.data;
};
