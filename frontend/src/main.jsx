import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import * as Sentry from '@sentry/react';
import 'bootstrap/dist/css/bootstrap.min.css';
import './index.css';
import App from './App';

// Initialise Sentry before rendering — captures errors that occur during
// React tree construction. Skips silently if DSN is not set (local dev).
const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    tracesSampleRate: 0.1,
    integrations: [Sentry.browserTracingIntegration()],
    sendDefaultPii: false,
    beforeSend(event) {
      const SENSITIVE = [
        'password', 'token', 'access_token', 'refresh_token',
        'authorization', 'bvn',
      ];
      function scrub(obj) {
        if (!obj || typeof obj !== 'object') return obj;
        if (Array.isArray(obj)) return obj.map(scrub);
        return Object.fromEntries(
          Object.entries(obj).map(([k, v]) =>
            SENSITIVE.includes(k.toLowerCase()) ? [k, '[Filtered]'] : [k, scrub(v)]
          )
        );
      }
      if (event.request?.data) event.request.data = scrub(event.request.data);
      if (event.request?.headers) event.request.headers = scrub(event.request.headers);
      return event;
    },
  });
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/*
      ErrorBoundary catches React render errors that would otherwise produce
      a blank white screen. Shows a user-friendly fallback and reports the
      error to Sentry automatically.
    */}
    <Sentry.ErrorBoundary
      fallback={
        <div style={{
          minHeight: '100vh', display: 'flex', alignItems: 'center',
          justifyContent: 'center', padding: '2rem', fontFamily: 'sans-serif',
        }}>
          <div style={{ maxWidth: 480, textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
            <h2 style={{ fontWeight: 700, marginBottom: '0.75rem', color: '#111' }}>
              Something went wrong
            </h2>
            <p style={{ color: '#555', marginBottom: '1.5rem', lineHeight: 1.6 }}>
              An unexpected error occurred. Our team has been notified and is
              looking into it.
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                background: '#2563EB', color: '#fff', border: 'none',
                borderRadius: 8, padding: '0.625rem 1.5rem',
                fontWeight: 600, cursor: 'pointer', fontSize: '0.9375rem',
              }}
            >
              Try Again
            </button>
          </div>
        </div>
      }
    >
      <App />
    </Sentry.ErrorBoundary>
  </StrictMode>
);
