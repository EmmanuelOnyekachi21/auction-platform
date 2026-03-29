/**
 * SellerPendingPage.jsx — Seller application under review screen
 *
 * Shown when user has applied to become a seller but
 * seller_profile.is_verified === false.
 */

import { Link } from 'react-router-dom';
import { FiClock, FiCheckCircle, FiArrowLeft, FiMail } from 'react-icons/fi';
import { useAuthStore } from '../../store/authStore';

const SELLER_TYPE_LABELS = {
    individual: 'Individual Seller',
    business:   'Business / Company',
    enterprise: 'Enterprise',
};

export default function SellerPendingPage() {
    const { user } = useAuthStore();
    const profile      = user?.seller_profile;
    const sellerType   = SELLER_TYPE_LABELS[profile?.seller_type] ?? profile?.seller_type ?? 'Seller';
    const submittedAt  = profile?.created_at
        ? new Date(profile.created_at).toLocaleDateString('en-NG', { day: 'numeric', month: 'long', year: 'numeric' })
        : null;

    return (
        <div style={{ minHeight: '70vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem 1.5rem' }}>
            <div style={{ maxWidth: 520, width: '100%' }}>

                {/* Icon */}
                <div style={{
                    width: 80, height: 80, borderRadius: 'var(--radius-full)',
                    background: 'var(--warning-light)', color: 'var(--warning)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    margin: '0 auto 1.75rem',
                    boxShadow: '0 0 0 8px rgba(217,119,6,0.08)',
                }}>
                    <FiClock size={36} />
                </div>

                {/* Heading */}
                <h1 style={{
                    textAlign: 'center', fontWeight: 800, fontSize: '1.625rem',
                    letterSpacing: '-0.03em', color: 'var(--text-primary)', marginBottom: '0.75rem',
                }}>
                    Application Under Review
                </h1>
                <p style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9375rem', lineHeight: 1.7, marginBottom: '2rem' }}>
                    Your seller application has been received and is currently being reviewed by our team.
                    This usually takes <strong>1–2 business days</strong>.
                </p>

                {/* Details card */}
                <div className="card" style={{ borderRadius: 'var(--radius-xl)', marginBottom: '1.5rem', overflow: 'hidden' }}>
                    <div style={{ padding: '0.875rem 1.25rem', background: 'var(--surface)', borderBottom: '1px solid var(--border)', fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-muted)' }}>
                        Application Details
                    </div>
                    <div style={{ padding: '0 1.25rem' }}>
                        {[
                            { label: 'Account Type',  value: sellerType },
                            { label: 'Applicant',     value: `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || user?.email },
                            { label: 'Status',        value: (
                                <span style={{ display:'inline-flex', alignItems:'center', gap:'0.35rem', fontWeight:700, color:'var(--warning)' }}>
                                    <FiClock size={13}/> Pending Review
                                </span>
                            )},
                            ...(submittedAt ? [{ label: 'Submitted', value: submittedAt }] : []),
                        ].map(({ label, value }, i, arr) => (
                            <div key={label} style={{
                                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                padding: '0.875rem 0',
                                borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none',
                                gap: '1rem',
                            }}>
                                <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontWeight: 600, flexShrink: 0 }}>{label}</span>
                                <span style={{ fontSize: '0.875rem', color: 'var(--text-primary)', fontWeight: 600, textAlign: 'right' }}>{value}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* What happens next */}
                <div className="card" style={{ borderRadius: 'var(--radius-xl)', marginBottom: '1.75rem', overflow: 'hidden' }}>
                    <div style={{ padding: '0.875rem 1.25rem', background: 'var(--primary-50)', borderBottom: '1px solid var(--primary-light)', fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--primary)' }}>
                        What Happens Next
                    </div>
                    <div style={{ padding: '1rem 1.25rem' }}>
                        {[
                            { icon: <FiCheckCircle size={15} style={{ color: 'var(--primary)', flexShrink: 0, marginTop: 2 }} />, text: 'Our team verifies your submitted information and documentation.' },
                            { icon: <FiMail size={15} style={{ color: 'var(--primary)', flexShrink: 0, marginTop: 2 }} />, text: `You will receive an email at ${user?.email ?? 'your registered address'} once a decision is made.` },
                            { icon: <FiCheckCircle size={15} style={{ color: 'var(--success)', flexShrink: 0, marginTop: 2 }} />, text: 'Once approved, you can immediately create and publish auctions.' },
                        ].map(({ icon, text }, i) => (
                            <div key={i} style={{ display: 'flex', gap: '0.75rem', marginBottom: i < 2 ? '0.875rem' : 0 }}>
                                {icon}
                                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{text}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <Link
                        to="/dashboard"
                        className="btn btn-primary"
                        style={{ flex: 1, justifyContent: 'center' }}
                        id="pending-back-dashboard-btn"
                    >
                        <FiArrowLeft size={15} /> Back to Dashboard
                    </Link>
                    <Link
                        to="/profile"
                        className="btn btn-outline-primary"
                        style={{ flex: 1, justifyContent: 'center' }}
                    >
                        View My Profile
                    </Link>
                </div>
            </div>
        </div>
    );
}
