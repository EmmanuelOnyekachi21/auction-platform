/**
 * wallet.js — Wallet API actions
 *
 * All wallet-related API calls for the auction platform.
 * Integrates with the configured apiClient (handles auth token injection).
 */

import apiClient from './client';

export const walletActions = {
    /**
     * Fetch the authenticated user's wallet balances.
     * GET /api/v1/wallets/me
     */
    getWallet: async () => {
        const response = await apiClient.get('/wallets/me');
        return response.data;
    },

    /**
     * Initiate a wallet funding request (Paystack redirect).
     * POST /api/v1/wallets/fund
     * @param {number} amount - Amount in Naira (min ₦100)
     */
    fundWallet: async (amount) => {
        const response = await apiClient.post('/wallets/fund', { amount });
        return response.data;
    },

    /**
     * Initiate a withdrawal to the user's registered bank account.
     * POST /api/v1/wallets/withdraw
     * @param {number} amount - Amount in Naira (min ₦100)
     */
    withdrawFunds: async (amount) => {
        const response = await apiClient.post('/wallets/withdraw', { amount });
        return response.data;
    },

    /**
     * Fetch paginated transaction history for the authenticated user.
     * GET /api/v1/wallets/me/transactions
     * @param {{ type?: string, direction?: string, page?: number, limit?: number }} params
     */
    getTransactions: async ({ type = '', direction = '', page = 1, limit = 20 } = {}) => {
        const query = new URLSearchParams();
        if (type) query.set('type', type);
        if (direction) query.set('direction', direction);
        query.set('page', String(page));
        query.set('limit', String(limit));
        const response = await apiClient.get(`/wallets/transactions?${query.toString()}`);
        return response.data; // Expected: { items, total, page, limit, pages }
    },
};
