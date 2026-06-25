import apiClient from './client';

export const authActions = {
    // Register a new user
    register: async (data) => {
        const response = await apiClient.post('/auth/register', data);
        return response.data
    },
     // Login
    login: async (credentials) => {
        const response = await apiClient.post('/auth/login', {
        email: credentials.email, // Backend expects "username" field usually for OAuth2 logic
        password: credentials.password,
        });
        return response.data;
    },
    // Logout
    logout: async () => {
        await apiClient.post('/auth/logout');
    },
    // Refresh (though client.js handles this automatically!)
    refreshToken: async (token) => {
        const response = await apiClient.post('/auth/refresh', { refresh_token: token });
        return response.data;
    },
    // Verify Email
    verifyEmail: async (token) => {
        const response = await apiClient.get(`/auth/verify-email?token=${token}`);
        return response.data;
    },
    // Forgot Password
    forgotPassword: async (email) => {
        const response = await apiClient.post('/auth/forgot-password', { email });
        return response.data;
    },
    // Reset Password
    resetPassword: async (token, newPassword, confirmPassword) => {
        const response = await apiClient.post(`/auth/reset-password`, {
        token: token,
        new_password: newPassword,
        confirm_password: confirmPassword
        });
        return response.data;
    },
    // Resend Verification mail
    resendVerification: async (email) => {
        const response = await apiClient.post('/auth/resend-verification', { email });
        return response.data;
    }
}
