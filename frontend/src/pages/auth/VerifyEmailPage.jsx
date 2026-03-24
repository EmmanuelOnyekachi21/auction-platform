import { useEffect, useState, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { authActions } from "../../api/auth";

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('verifying'); // 'verifying', 'success', 'error'
  const [message, setMessage] = useState('');

  // Prevents react from calling the API twice in Dev mode
  const hasRun = useRef(false);

  useEffect(() => {
    // If we've already run this, stop immediately
    if (hasRun.current) return;
    hasRun.current = true;

    const token = searchParams.get('token');

    const verify = async () => {
      if (!token) {
        setStatus('error');
        setMessage('No verification token found in the URL.');
        return;
      }

      try {
        await authActions.verifyEmail(token);
        setStatus('success');
        setMessage('Your email has been successfully verified! You can now log in.');
      } catch (err) {
        setStatus('error');
        setMessage(err.response?.data?.detail || 'Verification failed. The link may be expired.');
      }
    };

    verify();
  }, [searchParams]);

  return (
    <div className="container mt-5 text-center">
      <div className="row justify-content-center">
        <div className="col-md-6 card shadow p-5">
          {status === 'verifying' && (
            <div>
              <div className="spinner-border text-primary mb-3" role="status" />
              <h3>Verifying your email...</h3>
              <p>Please wait a moment while we process your request.</p>
            </div>
          )}

          {status === 'success' && (
            <div>
              <div className="h1 text-success mb-3">✅</div>
              <h2 className="mb-4">Verification Successful!</h2>
              <p className="lead">{message}</p>
              <Link to="/login" className="btn btn-primary mt-3">
                Go to Login
              </Link>
            </div>
          )}

          {status === 'error' && (
            <div>
              <div className="h1 text-danger mb-3">❌</div>
              <h2 className="mb-4">Verification Failed</h2>
              <p className="text-muted">{message}</p>
              <hr />
              <p>Didn't get the email? Or the link expired?</p>
              <Link to="/login" className="btn btn-outline-primary">
                Return to Login
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
