import { useState, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    FiArrowLeft, FiUser, FiCheckCircle, FiClock,
    FiPaperclip, FiImage, FiVideo, FiFile, FiExternalLink,
    FiPackage, FiArrowRight, FiShield, FiAlertCircle, FiXCircle,
    FiMail, FiPhone
} from 'react-icons/fi';
import { getDispute, uploadEvidenceFile, resolveDispute, markDisputeUnderReview } from '../../api/orders';
import { useAuthStore } from '../../store/authStore';
import { useToast } from '../../components/common/Toast';

const formatNaira = (amount) =>
    Number(amount || 0).toLocaleString('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0 });

const DISPUTE_STATUS = {
    OPEN:         { label: 'Open',         bg: '#FEF3C7',              color: '#D97706' },
    UNDER_REVIEW: { label: 'Under Review', bg: 'var(--info-light)',    color: 'var(--info)' },
    RESOLVED:     { label: 'Resolved',     bg: 'var(--success-light)', color: 'var(--success)' },
    DISMISSED:    { label: 'Dismissed',    bg: '#F1F5F9',              color: 'var(--text-muted)' },
};

const ORDER_STATUS_CONFIG = {
    pending_shipment: { label: 'Awaiting Shipment', bg: '#FEF3C7', color: '#D97706' },
    shipped: { label: 'Shipped', bg: 'var(--info-light)', color: 'var(--info)' },
    delivered: { label: 'Delivered', bg: '#CCFBF1', color: '#0D9488' },
    completed: { label: 'Completed', bg: 'var(--success-light)', color: 'var(--success)' },
    cancelled: { label: 'Cancelled', bg: '#F1F5F9', color: 'var(--text-muted)' },
    disputed: { label: 'Disputed', bg: 'var(--danger-light)', color: 'var(--danger)' },
    refunded: { label: 'Refunded', bg: '#F3E8FF', color: '#7C3AED' }
};

export default function DisputeDetailPage() {
    const { disputeId } = useParams();
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const { showToast } = useToast();
    const queryClient = useQueryClient();

    const [evidenceFile, setEvidenceFile] = useState(null);
    const [evidenceDesc, setEvidenceDesc] = useState('');
    const [evidencePreview, setEvidencePreview] = useState(null);

    // Admin resolution state
    const [resolution, setResolution] = useState('in_favour_of_buyer');
    const [resolutionNotes, setResolutionNotes] = useState('');
    const [showConfirmResolve, setShowConfirmResolve] = useState(false);

    const { data: dispute, isLoading, isError, refetch } = useQuery({
        queryKey: ['dispute', disputeId],
        queryFn: () => getDispute(disputeId),
    });

    const evidenceMutation = useMutation({
        mutationFn: () => uploadEvidenceFile(disputeId, evidenceFile, evidenceDesc || null),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['dispute', disputeId] });
            showToast('Evidence uploaded successfully', 'success');
            setEvidenceFile(null);
            setEvidencePreview(null);
            setEvidenceDesc('');
        },
        onError: (error) => {
            showToast(error?.response?.data?.detail || 'Failed to upload evidence', 'error');
        }
    });

    const resolveMutation = useMutation({
        mutationFn: (data) => resolveDispute(disputeId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['dispute', disputeId] });
            showToast('Dispute resolved successfully', 'success');
            setShowConfirmResolve(false);
        },
        onError: (error) => {
            showToast(error?.response?.data?.detail || 'Failed to resolve dispute', 'error');
            setShowConfirmResolve(false);
        }
    });

    const underReviewMutation = useMutation({
        mutationFn: () => markDisputeUnderReview(disputeId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['dispute', disputeId] });
            queryClient.invalidateQueries({ queryKey: ['admin-disputes'] });
            showToast('Dispute marked as under review', 'success');
        },
        onError: (error) => showToast(error?.response?.data?.detail || 'Failed to update status', 'error'),
    });

    const resolutionDirection = useMemo(() => {
        if (!dispute || dispute.status !== 'RESOLVED') return null;
        // Infer direction from order status if available
        if (dispute.order?.status === 'REFUNDED') return 'Buyer';
        if (dispute.order?.status === 'COMPLETED') return 'Seller';
        // Fallback to text search in resolution notes
        if (dispute.resolution?.toLowerCase().includes('buyer')) return 'Buyer';
        if (dispute.resolution?.toLowerCase().includes('seller')) return 'Seller';
        return null;
    }, [dispute]);

    if (isLoading) {
        return (
            <div className="container py-5">
                <div className="row g-4">
                    <div className="col-lg-7">
                        <div className="skeleton mb-4" style={{ height: 180, borderRadius: 'var(--radius-lg)' }} />
                        <div className="skeleton mb-4" style={{ height: 220, borderRadius: 'var(--radius-lg)' }} />
                        <div className="skeleton" style={{ height: 350, borderRadius: 'var(--radius-lg)' }} />
                    </div>
                    <div className="col-lg-5">
                        <div className="skeleton mb-4" style={{ height: 180, borderRadius: 'var(--radius-lg)' }} />
                        <div className="skeleton" style={{ height: 280, borderRadius: 'var(--radius-lg)' }} />
                    </div>
                </div>
            </div>
        );
    }

    if (isError || !dispute) {
        return (
            <div className="container py-5 text-center">
                <div className="card p-5 mx-auto" style={{ maxWidth: 500, borderRadius: 'var(--radius-lg)', borderStyle: 'solid' }}>
                    <FiAlertCircle size={48} className="text-danger mb-3 mx-auto" />
                    <h3 style={{ fontWeight: 700 }}>Dispute not found</h3>
                    <p className="text-muted">The dispute you are looking for does not exist or has been removed.</p>
                    <button className="btn btn-primary mx-auto" onClick={() => refetch()}>Retry</button>
                </div>
            </div>
        );
    }

    const statusConfig = DISPUTE_STATUS[dispute.status] || DISPUTE_STATUS.OPEN;
    const isOwner = String(user?.id) === String(dispute.raised_by_id)
        || String(user?.id) === String(dispute.against_id)
        || String(user?.id) === String(dispute.raised_by?.id)
        || String(user?.id) === String(dispute.against?.id);
    const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPERUSER';
    const canSubmitEvidence = (dispute.status === 'OPEN' || dispute.status === 'UNDER_REVIEW') && isOwner && !isAdmin;
    const canAdminResolve = (dispute.status === 'OPEN' || dispute.status === 'UNDER_REVIEW') && isAdmin;

    const getFileIcon = (type) => {
        if (type === 'IMAGE') return <FiImage size={20} />;
        if (type === 'VIDEO') return <FiVideo size={20} />;
        return <FiFile size={20} />;
    };

    return (
        <div style={{ backgroundColor: 'var(--bg-color)', minHeight: 'calc(100vh - 72px)', padding: '2rem 0' }}>
            <div className="container" style={{ maxWidth: 1100 }}>
                {/* Header */}
                <div className="mb-4">
                    <button
                        onClick={() => navigate(dispute.order ? `/orders/${dispute.order.id}` : '/my-orders')}
                        style={{ border: 'none', background: 'none', padding: 0, color: 'var(--text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, fontSize: '0.9375rem', marginBottom: '1rem' }}
                    >
                        <FiArrowLeft /> {dispute.order ? 'Back to Order' : 'Back to My Orders'}
                    </button>
                    <div className="d-flex align-items-center gap-3 flex-wrap">
                        <h1 style={{ fontSize: '1.75rem', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
                            Dispute #{dispute.id.slice(-8)}
                        </h1>
                        <span className="badge" style={{ backgroundColor: statusConfig.bg, color: statusConfig.color, borderRadius: 'var(--radius-full)', padding: '0.4em 0.8em', fontSize: '0.875rem', fontWeight: 700 }}>
                            {statusConfig.label}
                        </span>
                    </div>
                    <p style={{ margin: '0.5rem 0 0', color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
                        Raised: {new Date(dispute.created_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'long', year: 'numeric' })}
                    </p>
                </div>

                <div className="row g-4">
                    {/* LEFT COLUMN */}
                    <div className="col-lg-7">
                        {/* Dispute Details Card */}
                        <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', padding: '1.5rem', border: '1px solid var(--border)' }}>
                            <h5 style={{ fontWeight: 800, color: 'var(--text-primary)', marginBottom: '1rem' }}>{dispute.title}</h5>
                            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>{dispute.description}</p>
                        </div>

                        {/* Parties Card */}
                        <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', padding: '1.5rem', border: '1px solid var(--border)' }}>
                            {[
                                { label: 'Raised By (Buyer)', party: dispute.raised_by, accentBg: 'var(--primary-50)', accentColor: 'var(--primary)' },
                                { label: 'Against (Seller)', party: dispute.against, accentBg: 'var(--surface)', accentColor: 'var(--text-secondary)' },
                            ].map(({ label, party, accentBg, accentColor }, i) => (
                                <div key={i} className={i === 0 ? 'mb-4' : ''}>
                                    <div className="text-muted mb-2" style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>{label}</div>
                                    <div className="d-flex align-items-start gap-3">
                                        <div style={{ width: 44, height: 44, borderRadius: 'var(--radius)', backgroundColor: accentBg, color: accentColor, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                            <FiUser size={20} />
                                        </div>
                                        <div className="flex-grow-1">
                                            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                                                {party?.first_name || '—'} {party?.last_name || ''}
                                            </div>
                                            {isAdmin && party?.email && (
                                                <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                                    <FiMail size={12} />
                                                    <a href={`mailto:${party.email}`} style={{ color: 'var(--primary)' }}>{party.email}</a>
                                                </div>
                                            )}
                                            {isAdmin && party?.phone_number && (
                                                <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.2rem' }}>
                                                    <FiPhone size={12} /> {party.phone_number}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Evidence Section */}
                        <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', padding: '1.5rem', border: '1px solid var(--border)' }}>
                            <div className="d-flex align-items-center justify-content-between mb-4">
                                <h6 style={{ fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                    <FiPaperclip size={18} className="text-primary" /> Evidence Submitted
                                </h6>
                                <span className="badge bg-light text-dark" style={{ borderRadius: 'var(--radius-full)' }}>{(dispute.evidence || []).length}</span>
                            </div>

                            {(!dispute.evidence || dispute.evidence.length === 0) ? (
                                <p className="text-muted text-center py-4" style={{ fontSize: '0.9375rem', margin: 0 }}>No evidence submitted yet.</p>
                            ) : (
                                <div className="d-flex flex-column gap-3">
                                    {dispute.evidence.map((item, i) => (
                                        <div key={item.id}>
                                            {i > 0 && <hr style={{ margin: '0 0 1rem', opacity: 0.1 }} />}
                                            <div className="d-flex gap-3 align-items-center">
                                                <div style={{ width: 36, height: 36, borderRadius: 'var(--radius)', backgroundColor: 'var(--surface)', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                                    {getFileIcon(item.file_type)}
                                                </div>
                                                <div className="flex-grow-1 min-w-0">
                                                    <div style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--text-primary)', textTransform: 'capitalize' }}>{item.file_type.toLowerCase()}</div>
                                                    {item.description && <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.description}</div>}
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                                        Uploaded by: {item.uploaded_by_id === dispute.raised_by_id ? 'Buyer' : 'Seller'} · {new Date(item.created_at).toLocaleDateString()}
                                                    </div>
                                                </div>
                                                <a href={item.url} target="_blank" rel="noopener noreferrer" className="btn btn-outline-secondary btn-sm" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}>
                                                    <FiExternalLink size={14} /> View
                                                </a>                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Upload Evidence Form */}
                        {canSubmitEvidence && (
                            <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', border: '1px solid var(--primary-light)', padding: '1.5rem' }}>
                                <h6 style={{ fontWeight: 800, marginBottom: '1.25rem' }}>Upload Evidence</h6>
                                <div className="mb-3">
                                    <label className="form-label" style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                                        File (Image or Video)
                                    </label>
                                    <input
                                        type="file"
                                        className="form-control"
                                        accept="image/jpeg,image/png,image/webp,video/mp4,video/avi,video/mov,video/mkv"
                                        onChange={(e) => {
                                            const f = e.target.files?.[0] ?? null;
                                            setEvidenceFile(f);
                                            if (f && f.type.startsWith('image/')) {
                                                setEvidencePreview(URL.createObjectURL(f));
                                            } else {
                                                setEvidencePreview(null);
                                            }
                                        }}
                                        disabled={evidenceMutation.isPending}
                                    />
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                        Images: JPG, PNG, WebP (max 10MB) · Videos: MP4, AVI, MOV, MKV (max 100MB)
                                    </div>
                                </div>
                                {evidencePreview && (
                                    <div className="mb-3">
                                        <img
                                            src={evidencePreview}
                                            alt="Preview"
                                            style={{ maxHeight: 160, borderRadius: 'var(--radius)', objectFit: 'cover', border: '1px solid var(--border)' }}
                                        />
                                    </div>
                                )}
                                <div className="mb-3">
                                    <label className="form-label" style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                                        Description <span style={{ fontWeight: 400 }}>(optional)</span>
                                    </label>
                                    <input
                                        type="text"
                                        className="form-control"
                                        placeholder="Briefly describe this file"
                                        value={evidenceDesc}
                                        onChange={e => setEvidenceDesc(e.target.value)}
                                        disabled={evidenceMutation.isPending}
                                    />
                                </div>
                                <button
                                    className="btn btn-primary w-100"
                                    style={{ fontWeight: 700 }}
                                    onClick={() => evidenceMutation.mutate()}
                                    disabled={evidenceMutation.isPending || !evidenceFile}
                                >
                                    {evidenceMutation.isPending ? 'Uploading...' : 'Upload Evidence'}
                                </button>
                            </div>
                        )}

                        {/* Resolution Card */}
                        {(dispute.status === 'RESOLVED' || dispute.status === 'DISMISSED') && (
                            <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', overflow: 'hidden', border: '1px solid ' + (dispute.status === 'RESOLVED' ? 'var(--success-light)' : 'var(--border)') }}>
                                <div style={{ backgroundColor: dispute.status === 'RESOLVED' ? 'var(--success-50)' : 'var(--surface)', padding: '1.5rem' }}>
                                    <div className="d-flex align-items-center gap-3 mb-3">
                                        {dispute.status === 'RESOLVED' ? (
                                            <FiCheckCircle size={32} className="text-success" />
                                        ) : (
                                            <FiXCircle size={32} className="text-muted" />
                                        )}
                                        <div>
                                            <h5 style={{ fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
                                                {dispute.status === 'RESOLVED'
                                                    ? (resolutionDirection ? `Resolved in favour of ${resolutionDirection}` : 'Resolved')
                                                    : 'Dispute Dismissed'}
                                            </h5>
                                            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                                                Closed on {new Date(dispute.resolved_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'long', year: 'numeric' })}
                                            </div>
                                        </div>
                                    </div>
                                    {dispute.resolution && (
                                        <blockquote style={{
                                            backgroundColor: '#fff',
                                            borderRadius: 'var(--radius)',
                                            borderLeft: '4px solid ' + (dispute.status === 'RESOLVED' ? 'var(--success)' : 'var(--border)'),
                                            padding: '1rem',
                                            margin: '0 0 1rem',
                                            fontSize: '0.9375rem',
                                            color: 'var(--text-secondary)',
                                            fontStyle: 'italic'
                                        }}>
                                            "{dispute.resolution}"
                                        </blockquote>
                                    )}
                                    <div className="d-flex align-items-center gap-2" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                                        <FiShield size={14} /> Resolved by platform administrator
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* RIGHT COLUMN */}
                    <div className="col-lg-5">
                        {/* Mini Order Card */}
                        <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', padding: '1.25rem', border: '1px solid var(--border)' }}>
                            <div className="d-flex align-items-center gap-2 mb-3">
                                <FiPackage size={18} className="text-primary" />
                                <h6 style={{ fontWeight: 800, margin: 0 }}>Related Order</h6>
                            </div>

                            {dispute.order ? (
                                <>
                                    <div className="d-flex align-items-center gap-3 mb-4">
                                        <div style={{ width: 40, height: 40, borderRadius: 'var(--radius)', overflow: 'hidden', backgroundColor: 'var(--surface)', flexShrink: 0 }}>
                                            {dispute.order.item?.primary_image_url ? (
                                                <img src={dispute.order.item.primary_image_url} alt={dispute.order.item.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                            ) : (
                                                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                                                    <FiPackage size={20} />
                                                </div>
                                            )}
                                        </div>
                                        <div className="min-w-0">
                                            <div style={{ fontWeight: 700, fontSize: '0.875rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {dispute.order.item?.title || 'Unknown Item'}
                                            </div>
                                            <div style={{ fontWeight: 800, color: 'var(--primary)', fontSize: '0.9375rem' }}>
                                                {formatNaira(dispute.order.amount)}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="d-flex justify-content-between align-items-center mb-4">
                                        <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontWeight: 600 }}>Status</span>
                                        {(() => {
                                            const cfg = ORDER_STATUS_CONFIG[dispute.order.status.toLowerCase()] || { label: dispute.order.status, bg: '#f1f5f9', color: '#64748b' };
                                            return (
                                                <span className="badge" style={{ backgroundColor: cfg.bg, color: cfg.color, borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700 }}>
                                                    {cfg.label}
                                                </span>
                                            );
                                        })()}
                                    </div>

                                    <Link to={`/orders/${dispute.order.id}`} className="btn btn-outline-primary w-100" style={{ fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', fontSize: '0.875rem' }}>
                                        View Full Order <FiArrowRight size={14} />
                                    </Link>
                                </>
                            ) : (
                                <p className="text-muted text-center py-2" style={{ fontSize: '0.875rem', margin: 0 }}>Order details unavailable.</p>
                            )}
                        </div>

                        {/* Dispute Timeline */}
                        <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', padding: '1.25rem', border: '1px solid var(--border)' }}>
                            <div className="d-flex align-items-center gap-2 mb-4">
                                <FiClock size={18} className="text-primary" />
                                <h6 style={{ fontWeight: 800, margin: 0 }}>Dispute Timeline</h6>
                            </div>

                            <div className="timeline" style={{ paddingLeft: '0.5rem' }}>
                                {[
                                    { label: 'Dispute Raised', date: dispute.created_at, done: true },
                                    { label: 'Under Review', date: null, done: ['UNDER_REVIEW', 'RESOLVED', 'DISMISSED'].includes(dispute.status) },
                                    { label: 'Resolved', date: dispute.resolved_at, done: ['RESOLVED', 'DISMISSED'].includes(dispute.status) },
                                ].map((step, i, arr) => (
                                    <div key={i} className="d-flex gap-3 mb-4 last-mb-0" style={{ position: 'relative' }}>
                                        {i < arr.length - 1 && (
                                            <div style={{ position: 'absolute', left: 7, top: 20, bottom: -20, width: 2, backgroundColor: arr[i+1].done ? 'var(--primary)' : 'var(--border)' }}></div>
                                        )}
                                        <div style={{
                                            width: 16, height: 16, borderRadius: '50%',
                                            backgroundColor: step.done ? 'var(--primary)' : 'var(--card-bg)',
                                            border: `2px solid ${step.done ? 'var(--primary)' : 'var(--border)'}`,
                                            flexShrink: 0, marginTop: 4, zIndex: 1,
                                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                                        }}>
                                            {step.done && <div style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#fff' }}></div>}
                                        </div>
                                        <div className="flex-grow-1 min-w-0">
                                            <div style={{ fontWeight: 700, fontSize: '0.875rem', color: step.done ? 'var(--text-primary)' : 'var(--text-muted)' }}>{step.label}</div>
                                            {step.done && step.date && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(step.date).toLocaleDateString()}</div>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Admin Actions Panel */}
                        {canAdminResolve && (
                            <div className="card" style={{ border: '2px solid var(--warning)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                                <div style={{ backgroundColor: 'var(--warning-50)', padding: '1rem 1.25rem', borderBottom: '1px solid var(--warning-light)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                    <FiShield className="text-warning" size={18} />
                                    <h6 style={{ margin: 0, fontWeight: 800, color: '#92400e' }}>Admin Actions</h6>
                                </div>
                                <div className="card-body p-3">
                                    {dispute.status === 'OPEN' && (
                                        <button
                                            className="btn btn-outline-warning w-100 mb-3"
                                            style={{ fontWeight: 700 }}
                                            onClick={() => underReviewMutation.mutate()}
                                            disabled={underReviewMutation.isPending}
                                        >
                                            {underReviewMutation.isPending ? 'Updating...' : 'Mark as Under Review'}
                                        </button>
                                    )}
                                    <div className="mb-3">
                                        <div className="d-flex gap-1 p-1 bg-light rounded-pill border mb-3">
                                            {[
                                                { val: 'in_favour_of_buyer', label: 'Buyer' },
                                                { val: 'in_favour_of_seller', label: 'Seller' }
                                            ].map(opt => {
                                                const isActive = resolution === opt.val;
                                                return (
                                                    <button
                                                        key={opt.val}
                                                        onClick={() => setResolution(opt.val)}
                                                        className="btn flex-grow-1"
                                                        style={{
                                                            borderRadius: 'var(--radius-full)',
                                                            fontSize: '0.75rem',
                                                            fontWeight: 700,
                                                            padding: '0.4rem',
                                                            border: 'none',
                                                            backgroundColor: isActive ? 'var(--warning)' : 'transparent',
                                                            color: isActive ? '#fff' : 'var(--text-secondary)',
                                                            boxShadow: isActive ? 'var(--shadow-sm)' : 'none',
                                                            transition: 'all 0.2s'
                                                        }}
                                                    >
                                                        {opt.label}
                                                    </button>
                                                );
                                            })}
                                        </div>

                                        <div className="d-flex justify-content-between mb-1">
                                            <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Resolution Notes</label>
                                            <span style={{ fontSize: '0.7rem', color: resolutionNotes.length < 20 ? 'var(--danger)' : 'var(--success)' }}>{resolutionNotes.length}/20</span>
                                        </div>
                                        <textarea
                                            className="form-control mb-3"
                                            rows={3}
                                            placeholder="Explain the decision..."
                                            value={resolutionNotes}
                                            onChange={e => setResolutionNotes(e.target.value)}
                                            style={{ fontSize: '0.875rem', resize: 'none' }}
                                        />
                                    </div>

                                    {!showConfirmResolve ? (
                                        <button
                                            className="btn btn-warning w-100"
                                            style={{ fontWeight: 800, color: '#fff' }}
                                            onClick={() => setShowConfirmResolve(true)}
                                            disabled={resolutionNotes.length < 20}
                                        >
                                            Resolve Dispute
                                        </button>
                                    ) : (
                                        <div className="p-2 border rounded bg-white text-center">
                                            <div style={{ fontSize: '0.8125rem', fontWeight: 600, marginBottom: '0.75rem' }}>Finalise decision? Irreversible.</div>
                                            <div className="d-flex gap-2">
                                                <button className="btn btn-sm btn-light flex-grow-1" style={{ fontWeight: 700 }} onClick={() => setShowConfirmResolve(false)}>No</button>
                                                <button
                                                    className="btn btn-sm btn-warning flex-grow-1 text-white"
                                                    style={{ fontWeight: 700 }}
                                                    onClick={() => resolveMutation.mutate({ resolution, resolution_notes: resolutionNotes })}
                                                    disabled={resolveMutation.isPending}
                                                >
                                                    {resolveMutation.isPending ? '...' : 'Yes, resolve'}
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
