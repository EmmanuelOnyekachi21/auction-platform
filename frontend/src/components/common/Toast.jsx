/**
 * Toast.jsx — Global Toast Notification System
 * Fintech-grade, positioned top-right, using react-icons.
 */
import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { FiCheckCircle, FiAlertCircle, FiInfo, FiX } from 'react-icons/fi';

const ToastContext = createContext(null);

export const useToast = () => {
    const ctx = useContext(ToastContext);
    if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
    return ctx;
};

const ICONS = {
    success: <FiCheckCircle size={16} />,
    error: <FiAlertCircle size={16} />,
    info: <FiInfo size={16} />,
};

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);
    const counter = useRef(0);

    const showToast = useCallback((message, type = 'info', duration = 4500) => {
        const id = ++counter.current;
        setToasts((prev) => [...prev, { id, message, type, exiting: false }]);

        setTimeout(() => {
            setToasts((prev) =>
                prev.map((t) => (t.id === id ? { ...t, exiting: true } : t))
            );
        }, duration);

        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, duration + 400);
    }, []);

    const dismiss = useCallback((id) => {
        setToasts((prev) =>
            prev.map((t) => (t.id === id ? { ...t, exiting: true } : t))
        );
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 400);
    }, []);

    return (
        <ToastContext.Provider value={{ showToast }}>
            {children}
            <div className="toast-viewport" aria-live="polite" aria-atomic="true">
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        className={`toast-item toast-${toast.type} ${toast.exiting ? 'toast-exit' : 'toast-enter'}`}
                        role="alert"
                    >
                        <span className="toast-icon">
                            {ICONS[toast.type] || ICONS.info}
                        </span>
                        <span className="toast-message">{toast.message}</span>
                        <button
                            className="toast-close"
                            onClick={() => dismiss(toast.id)}
                            aria-label="Dismiss notification"
                        >
                            <FiX size={16} />
                        </button>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}
