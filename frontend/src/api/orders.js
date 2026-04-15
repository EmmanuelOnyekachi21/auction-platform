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
 * Submit evidence for a dispute.
 * POST /api/v1/disputes/{disputeId}/evidence
 * @param {string} disputeId
 * @param {{ url: string, file_type: 'IMAGE'|'VIDEO'|'DOCUMENT', description?: string }} data
 */
export const submitEvidence = async (disputeId, data) => {
    const response = await apiClient.post(`/disputes/${disputeId}/evidence`, data);
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
 * Aggregate from /users/me/orders since no dedicated /me/disputes exists.
 */
export const getMyDisputes = async () => {
    const [buyerRes, sellerRes] = await Promise.all([
        apiClient.get('/users/me/orders?role=buyer&limit=100'),
        apiClient.get('/users/me/orders?role=seller&limit=100'),
    ]);
    const buyerOrders = buyerRes.data?.data ?? buyerRes.data?.items ?? [];
    const sellerOrders = sellerRes.data?.data ?? sellerRes.data?.items ?? [];
    const allOrders = [...buyerOrders, ...sellerOrders];

    // Extract orders that have a dispute attached
    return allOrders
        .filter(o => o.dispute != null)
        .map(o => ({
            ...o.dispute,
            order_id: o.id,
            order_amount: o.amount,
            order_item: o.item
        }));
};
