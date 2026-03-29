import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export const useAuthStore = create(
    persist(
        (set) => ({
            // state
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,

            // Actions
            setAuth: (user, accessToken, refreshToken) =>
                set({
                    user,
                    accessToken,
                    refreshToken,
                    isAuthenticated: !!user
                }),

            updateUser: (userData) =>
                set((state) => ({
                    user: { ...state.user, ...userData }
                })),

            setLoading: (isLoading) => set({ isLoading }),

            logout: () => {
                set({
                user: null,
                accessToken: null,
                refreshToken: null,
                isAuthenticated: false,
                });
                // Clear local storage and redirect
                localStorage.removeItem('auth-storage');
                window.location.href = '/login';
            },

            // Zustand handles loadFromStorage automatically with 'persist'!
        }),
        {
            name: 'auth-storage',  // key in localstorage
            storage: createJSONStorage(() => localStorage)
        }
    )
);
