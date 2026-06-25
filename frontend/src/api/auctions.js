/**
 * auctions.js — Auction & Category API actions
 *
 * All auction-related API calls for the KaraKaja marketplace.
 * Integrates with the configured apiClient (handles auth token injection).
 */

import apiClient from './client';

/**
 * Fetch a paginated list of auctions with optional filters.
 * GET /api/v1/auctions
 * @param {{ category_id?: string|number, sort_by?: string, page?: number, limit?: number }} params
 */
export const getAuctions = async ({ category_id, sort_by, view = 'active', page = 1, limit = 12 } = {}) => {
    const query = new URLSearchParams();
    if (category_id) query.set('category_id', String(category_id));
    if (sort_by) query.set('sort_by', sort_by);
    query.set('view', view);
    query.set('page', String(page));
    query.set('limit', String(limit));
    const response = await apiClient.get(`/auctions?${query.toString()}`);
    return response.data; // Expected: { items, total, page, limit, pages }
};

/**
 * Fetch all available auction categories.
 * GET /api/v1/categories
 */
export const getCategories = async () => {
    const response = await apiClient.get('/categories');
    return response.data; // Expected: array of { id, name, slug, ... }
};

/**
 * Fetch a single auction by its ID.
 * GET /api/v1/auctions/{auctionId}
 * @param {string|number} auctionId
 */
export const getAuction = async (auctionId) => {
    const response = await apiClient.get(`/auctions/${auctionId}`);
    return response.data;
};
