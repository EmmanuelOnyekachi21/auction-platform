import { useState } from 'react';
import { useForm } from 'react-hook-form';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';
import { FiShield, FiCheckCircle, FiXCircle, FiSend, FiInfo } from 'react-icons/fi';

export default function VerifySellersPage() {
  const [selectedSeller, setSelectedSeller] = useState(null);
  const { register, handleSubmit, reset } = useForm();
  const { showToast } = useToast();

  const verifySeller = async (userId, data) => {
    try {
      await apiClient.patch(`/users/${userId}/seller-profile/verify`, {
        is_verified: data.is_verified,
        rejection_reason: data.rejection_reason || null
      });
      showToast(data.is_verified ? 'Seller verified successfully!' : 'Seller application rejected', data.is_verified ? 'success' : 'info');
      setSelectedSeller(null);
      reset();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to verify seller', 'error');
    }
  };

  const onSubmit = (data) => {
    if (selectedSeller) verifySeller(selectedSeller, data);
  };

  return (
    <div className="page-container" style={{ maxWidth: 700 }}>
      <div className="d-flex align-items-center gap-2 mb-4">
        <div style={{ width: 40, height: 40, borderRadius: 'var(--radius)', background: 'var(--primary-50)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <FiShield size={20} />
        </div>
        <div>
          <h1 style={{ fontWeight: 800, fontSize: '1.5rem', margin: 0 }}>Verify Sellers</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', margin: 0 }}>Admin tool for managing seller applications</p>
        </div>
      </div>

      <div className="card mb-4" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="card-body p-4">
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="mb-3">
              <label className="form-label">User ID</label>
              <input type="text" className="form-control" placeholder="Enter user UUID"
                value={selectedSeller || ''} onChange={(e) => setSelectedSeller(e.target.value)} required />
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Paste the seller&rsquo;s user ID from the database or profile URL
              </div>
            </div>

            <div className="mb-3">
              <label className="form-label">Action</label>
              <div className="d-flex gap-3">
                <label style={{
                  flex: 1, padding: '0.875rem', borderRadius: 'var(--radius)',
                  border: '2px solid var(--border)', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                }}>
                  <input {...register('is_verified')} type="radio" value="true" defaultChecked style={{ accentColor: 'var(--success)' }} />
                  <FiCheckCircle size={16} style={{ color: 'var(--success)' }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--success)' }}>Approve</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Verify this seller</div>
                  </div>
                </label>
                <label style={{
                  flex: 1, padding: '0.875rem', borderRadius: 'var(--radius)',
                  border: '2px solid var(--border)', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                }}>
                  <input {...register('is_verified')} type="radio" value="false" style={{ accentColor: 'var(--danger)' }} />
                  <FiXCircle size={16} style={{ color: 'var(--danger)' }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--danger)' }}>Reject</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Deny verification</div>
                  </div>
                </label>
              </div>
            </div>

            <div className="mb-4">
              <label className="form-label">Rejection Reason</label>
              <textarea {...register('rejection_reason')} className="form-control" rows="3" placeholder="Required if rejecting..." />
            </div>

            <button type="submit" className="btn btn-primary">
              <FiSend size={14} /> Submit Verification
            </button>
          </form>
        </div>
      </div>

      {/* Instructions */}
      <div className="card" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="card-body p-4">
          <div className="d-flex align-items-center gap-2 mb-3">
            <FiInfo size={16} style={{ color: 'var(--primary)' }} />
            <h6 style={{ fontWeight: 700, margin: 0 }}>How to use</h6>
          </div>
          <ol style={{ color: 'var(--text-secondary)', fontSize: '0.8125rem', paddingLeft: '1.25rem', margin: 0, lineHeight: 2 }}>
            <li>A user registers as a seller via the &quot;Become a Seller&quot; page</li>
            <li>Get their user ID from the database or their profile URL</li>
            <li>Enter the user ID above</li>
            <li>Choose to approve or reject</li>
            <li>If rejecting, provide a reason</li>
            <li>Submit — the user will receive an email notification</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
