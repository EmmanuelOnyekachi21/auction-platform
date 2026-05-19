import { useQuery } from '@tanstack/react-query';
import {
  FiSettings, FiPercent, FiClock, FiTruck, FiShield, FiAlertCircle, FiDatabase, FiLock, FiInfo
} from 'react-icons/fi';
import apiClient from '../../api/client';

const fmt = (n) => n != null ? `₦${Number(n).toLocaleString('en-NG', { minimumFractionDigits: 2 })}` : '—';

export default function AdminSettingsPage() {
  const {
    data: config,
    isLoading,
    isError
  } = useQuery({
    queryKey: ['admin-platform-settings'],
    queryFn: () => apiClient.get('/admin/settings').then(r => r.data),
    staleTime: 60_000,
  });

  return (
    <div style={{ padding: '2rem', minHeight: '100vh' }}>

      {/* Header */}
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div className="d-flex align-items-center gap-3">
          <div style={{
            width: 44, height: 44, borderRadius: 'var(--radius)',
            background: 'var(--primary-50)', color: 'var(--primary)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <FiSettings size={22} />
          </div>
          <div>
            <h1 style={{ fontWeight: 800, fontSize: '1.5rem', margin: 0 }}>Platform System Settings</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
              Audit global platform fee configurations, auction constraints, and KYC transaction thresholds (Read-only)
            </p>
          </div>
        </div>

        {/* Read-Only Status Indicator */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          padding: '0.5rem 1rem', borderRadius: 'var(--radius)',
          background: '#F1F5F9', border: '1px solid var(--border)',
          fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-secondary)'
        }}>
          <FiLock size={14} className="text-muted" />
          <span>Read-Only Mode</span>
        </div>
      </div>

      {isLoading && (
        <div style={{ padding: '4rem 0' }}>
          <div className="skeleton mb-3" style={{ height: 120, borderRadius: 'var(--radius-xl)' }} />
          <div className="row g-4">
            <div className="col-md-6"><div className="skeleton" style={{ height: 200, borderRadius: 'var(--radius-xl)' }} /></div>
            <div className="col-md-6"><div className="skeleton" style={{ height: 200, borderRadius: 'var(--radius-xl)' }} /></div>
          </div>
        </div>
      )}

      {isError && (
        <div className="card text-center p-5 border-danger" style={{ borderRadius: 'var(--radius-xl)' }}>
          <div className="card-body">
            <FiAlertCircle size={40} className="text-danger mb-3" />
            <h4 style={{ fontWeight: 700 }}>Unable to retrieve platform settings</h4>
            <p className="text-muted small mx-auto" style={{ max_width: 400 }}>
              Verify backend service status and database configurations.
            </p>
          </div>
        </div>
      )}

      {!isLoading && !isError && config && (
        <div className="d-flex flex-column gap-4">

          {/* Top Panel: Platform Fee & BVN Verification Banner */}
          <div className="row g-4">

            {/* Commission Rate & Shipping Panel */}
            <div className="col-lg-6">
              <div className="card h-100" style={{ borderRadius: 'var(--radius-xl)' }}>
                <div className="card-body p-4 d-flex flex-column justify-content-between">
                  <div>
                    <h5 style={{ fontWeight: 800, fontSize: '1rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <FiPercent className="text-primary" /> Core Billing & Shipping Settings
                    </h5>

                    <div className="d-flex align-items-center gap-4 mb-4">
                      {/* Commission rate visual badge */}
                      <div style={{
                        width: 80, height: 80, borderRadius: 'var(--radius-xl)',
                        background: 'var(--primary-50)', color: 'var(--primary)',
                        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'
                      }}>
                        <span style={{ fontSize: '1.75rem', fontWeight: 900, lineHeight: 1 }}>{config.commission_rate * 100}</span>
                        <span style={{ fontSize: '0.65rem', fontWeight: 800 }}>PERCENT</span>
                      </div>
                      <div>
                        <h6 style={{ fontWeight: 700, margin: '0 0 0.25rem' }}>Platform Commission Fee</h6>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', margin: 0, max_width: 320 }}>
                          Fee percentage automatically deducted from escrow payouts upon successful delivery confirmation.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }} className="d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center gap-2">
                      <FiTruck className="text-muted" size={16} />
                      <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>Shipping Deadline:</span>
                    </div>
                    <span style={{ fontWeight: 800, fontSize: '0.9rem' }}>{config.shipping_deadline_days} Days</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Durations & BVN Verification Panel */}
            <div className="col-lg-6">
              <div className="card h-100" style={{ borderRadius: 'var(--radius-xl)' }}>
                <div className="card-body p-4 d-flex flex-column justify-content-between">
                  <div>
                    <h5 style={{ fontWeight: 800, fontSize: '1rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <FiShield className="text-primary" /> Platform Trust & Duration Rules
                    </h5>

                    <div className="d-flex align-items-center gap-4 mb-4">
                      {/* BVN glowing status badge */}
                      <div style={{
                        width: 80, height: 80, borderRadius: 'var(--radius-xl)',
                        background: config.bvn_verification_enabled ? 'var(--success-light)' : '#FEF3C7',
                        color: config.bvn_verification_enabled ? 'var(--success)' : '#D97706',
                        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'
                      }}>
                        <span style={{ fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase' }}>BVN GATE</span>
                        <span style={{ fontSize: '1rem', fontWeight: 900, marginTop: 4 }}>
                          {config.bvn_verification_enabled ? 'ON' : 'OFF'}
                        </span>
                      </div>
                      <div>
                        <h6 style={{ fontWeight: 700, margin: '0 0 0.25rem' }}>Bank Verification Number (BVN)</h6>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', margin: 0, max_width: 320 }}>
                          {config.bvn_verification_enabled
                            ? 'Strict BVN verification is actively enforced prior to bid approvals and payouts.'
                            : 'BVN verification is currently optional for legacy user accounts.'
                          }
                        </p>
                      </div>
                    </div>
                  </div>

                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }} className="d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center gap-2">
                      <FiClock className="text-muted" size={16} />
                      <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>Auction Duration Range:</span>
                    </div>
                    <span style={{ fontWeight: 800, fontSize: '0.9rem' }}>
                      {config.min_auction_duration_hours}h to {config.max_auction_duration_hours}h
                    </span>
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* KYC Limits Panel */}
          <div>
            <div className="d-flex align-items-center gap-2 mb-3">
              <h4 style={{ fontWeight: 800, fontSize: '1.1rem', margin: 0 }}>KYC Tier Transaction Limits</h4>
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
                fontSize: '0.7rem', color: 'var(--primary)', background: 'var(--primary-50)',
                padding: '0.15rem 0.5rem', borderRadius: 'var(--radius-full)', fontWeight: 700
              }}>
                <FiInfo size={10} />
                <span>Regulatory Thresholds</span>
              </div>
            </div>

            <div className="row g-3">
              {['tier_1', 'tier_2', 'tier_3'].map((tierKey, index) => {
                const limits = config.tier_limits[tierKey];
                const tierNumber = index + 1;

                return (
                  <div key={tierKey} className="col-md-4">
                    <div className="card h-100" style={{
                      borderRadius: 'var(--radius-xl)',
                      borderTop: `4px solid ${tierNumber === 1 ? '#94A3B8' : tierNumber === 2 ? 'var(--primary)' : 'var(--success)'}`
                    }}>
                      <div className="card-body p-4">
                        <div className="d-flex justify-content-between align-items-center mb-3">
                          <h6 style={{ fontWeight: 800, margin: 0, textTransform: 'uppercase', fontSize: '0.875rem' }}>
                            Tier {tierNumber} Status
                          </h6>
                          <span style={{
                            fontSize: '0.7rem', fontWeight: 800,
                            padding: '0.15rem 0.45rem', borderRadius: 'var(--radius)',
                            background: tierNumber === 1 ? '#F1F5F9' : tierNumber === 2 ? 'var(--primary-50)' : 'var(--success-light)',
                            color: tierNumber === 1 ? '#475569' : tierNumber === 2 ? 'var(--primary)' : 'var(--success)'
                          }}>
                            {tierNumber === 1 ? 'BASIC' : tierNumber === 2 ? 'VERIFIED' : 'PREMIUM'}
                          </span>
                        </div>

                        <div className="d-flex flex-column gap-3">

                          {/* Limit 1: Max Wallet Balance */}
                          <div>
                            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>
                              Max Wallet Balance
                            </span>
                            <span style={{ fontSize: '1rem', fontWeight: 800 }}>
                              {limits.max_wallet_balance >= 90000000 ? 'No Limit' : fmt(limits.max_wallet_balance)}
                            </span>
                          </div>

                          {/* Limit 2: Max Single Bid */}
                          <div>
                            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>
                              Max Bid Allowed
                            </span>
                            <span style={{ fontSize: '1rem', fontWeight: 800 }}>
                              {limits.max_bid >= 90000000 ? 'No Limit' : fmt(limits.max_bid)}
                            </span>
                          </div>

                          {/* Limit 3: Max Payout Withdrawal */}
                          <div>
                            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>
                              Withdrawal Limit
                            </span>
                            <span style={{ fontSize: '1rem', fontWeight: 800 }}>
                              {limits.max_withdrawal != null
                                ? (limits.max_withdrawal === 0 ? 'Not Supported' : fmt(limits.max_withdrawal))
                                : fmt(limits.max_daily_withdrawal) + ' / day'
                              }
                            </span>
                          </div>

                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Config Sync Notification */}
          <div className="card bg-light border-0" style={{ borderRadius: 'var(--radius-xl)' }}>
            <div className="card-body p-3 d-flex align-items-center gap-3">
              <FiDatabase size={20} className="text-primary flex-shrink-0" />
              <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                <strong>System Sync Notice:</strong> These read-only variables are dynamically synchronized with active `.env` configuration keys and system settings variables on initial server bootstrap.
              </span>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
