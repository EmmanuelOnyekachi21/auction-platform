import axios from "axios";
import { useAuthStore } from "../store/authStore";

// Use an environment variable of fallback to localhost
const baseURL = import.meta.env.VITE_API_URL || 'http://ivkjuebk6qm9t2qsbyf9jx9k.187.124.210.55.sslip.io/api/v1';
// const baseURL = 'http://ivkjuebk6qm9t2qsbyf9jx9k.187.124.210.55.sslip.io:2102/api/v1';

const apiClient = axios.create({
    baseURL,
    headers: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true',
    },
});

// Request interceptot: Attach the token to every outgoing request
apiClient.interceptors.request.use((config) => {
    // Get token directly from the Zustand store
    const { accessToken } = useAuthStore.getState();
    if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`
    }
    return config;
});

// Response interceptors: Handle errors and auto-refresh tokens
apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // If i get a 401 (Unauthorized) and haven't tried refreshing yet
        if (error.response?.status == 401 && !originalRequest._retry && !originalRequest.url.includes('/auth/login')) {
            originalRequest._retry = true;

            try {
                const { refreshToken, setAuth, logout } = useAuthStore.getState();

                if (!refreshToken) throw new Error('No refresh token available');

                // call the refresh endpoint
                const response = await axios.post(`${baseURL}/auth/refresh`, {
                    refresh_token: refreshToken,
                });

                const { access_token, refresh_token: new_refresh_token } = response.data;
                const { user, refreshToken: currentRefreshToken } = useAuthStore.getState();

                // Save the new tokens — keep existing refresh token if backend doesn't rotate
                setAuth(user, access_token, new_refresh_token || currentRefreshToken);

                // Retry the original request with the NEW token
                originalRequest.headers.Authorization = `Bearer ${access_token}`;
                return apiClient(originalRequest);
            } catch (refreshError) {
                // If refreshing fails, must log the user out
                useAuthStore.getState().logout();
                return Promise.reject(refreshError);
            }
        }
        return Promise.reject(error);
    }
);

/**
 * Extract a user-friendly error message from an Axios error.
 * Handles both our custom backend shape { message, code } and
 * FastAPI's default shape { detail }.
 */
export function getErrorMessage(error, fallback = 'Something went wrong') {
  const data = error?.response?.data;
  if (!data) return fallback;
  // Our custom exception handler returns { message, code, status }
  if (typeof data.message === 'string' && data.message) return data.message;
  // FastAPI default validation errors return { detail: string | array }
  if (typeof data.detail === 'string' && data.detail) return data.detail;
  if (Array.isArray(data.detail) && data.detail.length > 0) {
    return data.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
  }
  return fallback;
}

export default apiClient;
