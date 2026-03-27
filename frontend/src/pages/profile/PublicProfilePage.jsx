import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../../api/client';
import { FiStar, FiCalendar, FiShoppingBag, FiShoppingCart, FiCheckCircle, FiAlertCircle, FiUser } from 'react-icons/fi';

export default function PublicProfilePage() {
  const { userId } = useParams();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => { fetchPublicProfile(); }, [userId]);

  const fetchPublicProfile = async () => {
    try {
      setLoading(true); setError(null);
      const response = await apiClient.get(`/users/${userId}`);
      setProfile(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const renderStars = (rating) => {
    const r = parseFloat(rating) || 0;
    return Array.from({ length: 5 }, (_, i) => (
      <FiStar key={i} size={16} style={{ color: i < Math.floor(r) ? 'var(--warning)' : 'var(--border)', fill: i < Math.floor(r) ? 'var(--warning)' : 'none' }} />
    ));
  };

  if (loading) {
    return (
      <div className="page-container" style={{ maxWidth: 700 }}>
        <div className="card" style={{ borderRadius: 'var(--radius-xl)' }}>
          <div className="card-body p-4">
            {[...Array(5)].map((_, i) => <div key={i} className="skeleton mb-3" style={{ height: 16, width: `${80 - i * 10}%` }} />)}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container text-center" style={{ maxWidth: 500 }}>
        <FiAlertCircle size={40} style={{ color: 'var(--danger)', marginBottom: '1rem' }} />
        <h4 style={{ fontWeight: 700 }}>Error</h4>
        <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="page-container text-center" style={{ maxWidth: 500 }}>
        <FiUser size={40} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} />
        <h4 style={{ fontWeight: 700 }}>User not found</h4>
      </div>
    );
  }

  const initials = `${(profile.first_name?.[0] || '').toUpperCase()}${(profile.last_name?.[0] || '').toUpperCase()}`;

  return (
    <div className="page-container" style={{ maxWidth: 700 }}>
      <div className="card" style={{ borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ background: 'linear-gradient(135deg, var(--primary), var(--primary-dark))', padding: '2rem 1.5rem 1.25rem', display: 'flex', alignItems: 'flex-end', gap: '1rem' }}>
          <div style={{ width: 64, height: 64, borderRadius: 'var(--radius-full)', background: '#fff', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem', fontWeight: 800, flexShrink: 0, border: '3px solid rgba(255,255,255,0.3)' }}>
            {initials}
          </div>
          <div style={{ color: '#fff', paddingBottom: '0.25rem' }}>
            <h3 style={{ fontWeight: 700, fontSize: '1.25rem', margin: 0 }}>{profile.first_name} {profile.last_name}</h3>
            <div style={{ opacity: 0.8, fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FiCalendar size={12} /> Joined {new Date(profile.member_since).toLocaleDateString('en-NG', { year: 'numeric', month: 'long' })}
            </div>
          </div>
        </div>

        <div className="card-body p-4">
          {/* Rating */}
          <div className="d-flex align-items-center gap-2 mb-4">
            <div className="d-flex gap-1">{renderStars(profile.rating)}</div>
            <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              ({parseFloat(profile.rating || 0).toFixed(1)} / 5.0)
            </span>
          </div>

          {/* Stats */}
          <div className="row g-3 mb-4">
            <div className="col-6">
              <div style={{ background: 'var(--success-light)', borderRadius: 'var(--radius)', padding: '1rem', textAlign: 'center' }}>
                <FiShoppingBag size={18} style={{ color: 'var(--success)', marginBottom: '0.25rem' }} />
                <div style={{ fontWeight: 800, fontSize: '1.25rem' }}>{profile.total_sales}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Sales</div>
              </div>
            </div>
            <div className="col-6">
              <div style={{ background: 'var(--primary-50)', borderRadius: 'var(--radius)', padding: '1rem', textAlign: 'center' }}>
                <FiShoppingCart size={18} style={{ color: 'var(--primary)', marginBottom: '0.25rem' }} />
                <div style={{ fontWeight: 800, fontSize: '1.25rem' }}>{profile.total_purchases}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Purchases</div>
              </div>
            </div>
          </div>

          {/* Verified Seller */}
          {profile.is_verified_seller && (
            <div style={{ padding: '0.875rem 1rem', background: 'var(--success-light)', borderRadius: 'var(--radius)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <FiCheckCircle size={20} style={{ color: 'var(--success)' }} />
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--success)' }}>Verified Seller</div>
                {profile.seller_type && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {profile.seller_type.charAt(0) + profile.seller_type.slice(1).toLowerCase()}
                  </div>
                )}
              </div>
            </div>
          )}

          {!profile.is_verified_seller && profile.total_sales === 0 && (
            <div style={{ padding: '0.875rem 1rem', background: 'var(--surface)', borderRadius: 'var(--radius)', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              This user hasn&rsquo;t made any sales yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
