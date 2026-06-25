import { useState, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    FiArrowLeft, FiPackage, FiTruck, FiCheckCircle,
    FiShield, FiUser, FiAlertCircle, FiInfo, FiClock,
    FiMapPin, FiHash, FiCreditCard, FiX
} from 'react-icons/fi';
import { getOrder, shipOrder, confirmDelivery, raiseDispute, cancelOrder, uploadEvidenceFile } from '../../api/orders';
import { useAuthStore } from '../../store/authStore';
import { useToast } from '../../components/common/Toast';

const formatNaira = (amount) =>
    Number(amount || 0).toLocaleString('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0 });

const STATUS_CONFIG = {
    pending_shipment: { label: 'Awaiting Shipment', bg: '#FEF3C7', color: '#D97706' },
    shipped: { label: 'Shipped', bg: 'var(--info-light)', color: 'var(--info)' },
    delivered: { label: 'Delivered', bg: '#CCFBF1', color: '#0D9488' },
    completed: { label: 'Completed', bg: 'var(--success-light)', color: 'var(--success)' },
    cancelled: { label: 'Cancelled', bg: '#F1F5F9', color: 'var(--text-muted)' },
    disputed: { label: 'Disputed', bg: 'var(--danger-light)', color: 'var(--danger)' },
    refunded: { label: 'Refunded', bg: '#F3E8FF', color: '#7C3AED' }
};

// --- Modal Components (Same as MyOrdersPage for consistency) ---

function ShipOrderModal({ show, onClose, orderId, onSuccess }) {
    const [trackingNumber, setTrackingNumber] = useState('');
    const { showToast } = useToast();
    const queryClient = useQueryClient();
    const mutation = useMutation({
        mutationFn: (data) => shipOrder(orderId, data),
        onSuccess: () => {
            showToast('Order marked as shipped!', 'success');
            queryClient.invalidateQueries({ queryKey: ['order', orderId] });
            queryClient.invalidateQueries({ queryKey: ['my-orders'] });
            onSuccess?.();
            onClose();
        },
        onError: (error) => showToast(error?.response?.data?.detail || 'Failed to mark as shipped', 'error')
    });
    if (!show) return null;
    return (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050, padding: '1rem' }} onClick={onClose}>
            <div style={{ backgroundColor: 'var(--card-bg)', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: 450, overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
                <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}><FiTruck size={20} className="text-primary"/><h5 style={{ margin: 0, fontWeight: 700 }}>Ship Order</h5></div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none' }}><FiX size={20} /></button>
                </div>
                <div style={{ padding: '1.5rem' }}>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                        Confirm that you have handed the item to a courier or delivery service for shipment.
                    </p>
                    <label className="form-label" style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                        Tracking Number <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(optional)</span>
                    </label>
                    <input type="text" className="form-control" placeholder="e.g. GIGL-123456 — leave blank if unavailable" value={trackingNumber} onChange={e => setTrackingNumber(e.target.value)} disabled={mutation.isPending} />
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                        If your courier gave you a tracking code, enter it here so the buyer can follow up. You can skip this if you don't have one.
                    </div>
                </div>
                <div style={{ padding: '1.25rem', borderTop: '1px solid var(--border)', backgroundColor: 'var(--surface)', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                    <button className="btn btn-light" onClick={onClose}>Cancel</button>
                    <button className="btn btn-primary" onClick={() => mutation.mutate({ tracking_number: trackingNumber })} disabled={mutation.isPending}>Confirm Shipment</button>
                </div>
            </div>
        </div>
    );
}

function ConfirmDeliveryModal({ show, onClose, orderId, onSuccess }) {
    const { showToast } = useToast();
    const queryClient = useQueryClient();
    const mutation = useMutation({
        mutationFn: () => confirmDelivery(orderId),
        onSuccess: () => {
            showToast('Order delivery confirmed', 'success');
            queryClient.invalidateQueries({ queryKey: ['order', orderId] });
            queryClient.invalidateQueries({ queryKey: ['my-orders'] });
            onSuccess?.();
            onClose();
        },
        onError: (error) => showToast(error?.response?.data?.detail || 'Failed to confirm', 'error')
    });
    if (!show) return null;
    return (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050, padding: '1rem' }} onClick={onClose}>
            <div style={{ backgroundColor: 'var(--card-bg)', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: 450, overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
                <div style={{ padding: '1.5rem', textAlign: 'center' }}>
                    <h5 style={{ fontWeight: 700 }}>Confirm Delivery?</h5>
                    <p className="text-muted">Confirming delivery will release payment to the seller. Are you sure?</p>
                </div>
                <div style={{ padding: '1.25rem', borderTop: '1px solid var(--border)', display: 'flex', gap: '0.75rem' }}>
                    <button className="btn btn-light w-100" onClick={onClose}>Cancel</button>
                    <button className="btn btn-primary w-100" onClick={() => mutation.mutate()} disabled={mutation.isPending}>Confirm Delivery</button>
                </div>
            </div>
        </div>
    );
}

function RaiseDisputeModal({ show, onClose, orderId, onSuccess }) {
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [files, setFiles] = useState([]);
    const { showToast } = useToast();
    const queryClient = useQueryClient();
    const mutation = useMutation({
        mutationFn: async (data) => {
            const dispute = await raiseDispute(orderId, data);
            if (files.length > 0) {
                for (const f of files) {
                    try { await uploadEvidenceFile(dispute.id, f); } catch { /* non-fatal */ }
                }
            }
            return dispute;
        },
        onSuccess: () => {
            showToast('Dispute raised successfully', 'success');
            queryClient.invalidateQueries({ queryKey: ['order', orderId] });
            queryClient.invalidateQueries({ queryKey: ['my-orders'] });
            onSuccess?.();
            onClose();
        },
        onError: (error) => showToast(error?.response?.data?.detail || 'Failed to raise dispute', 'error')
    });
    if (!show) return null;
    return (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050, padding: '1rem' }} onClick={onClose}>
            <div style={{ backgroundColor: 'var(--card-bg)', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: 500, overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
                <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <h5 style={{ margin: 0, fontWeight: 700 }}>Raise Dispute</h5>
                    <button onClick={onClose} style={{ background: 'none', border: 'none' }}><FiX size={20} /></button>
                </div>
                <div style={{ padding: '1.5rem' }}>
                    <input type="text" className="form-control mb-3" placeholder="Dispute Title" value={title} onChange={e => setTitle(e.target.value)} />
                    <textarea className="form-control mb-2" rows={4} placeholder="Describe the issue (min 50 chars)" value={description} onChange={e => setDescription(e.target.value)} />
                    <div className="mb-3" style={{ fontSize: '0.75rem', color: description.length < 50 ? 'var(--danger)' : 'var(--success)' }}>{description.length}/50 chars</div>
                    <div>
                        <label className="form-label" style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                            Attach Evidence <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(optional)</span>
                        </label>
                        <input
                            type="file"
                            className="form-control"
                            accept="image/jpeg,image/png,image/webp,video/mp4,video/avi,video/mov,video/mkv"
                            multiple
                            onChange={e => setFiles(Array.from(e.target.files).slice(0, 10))}
                        />
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                            Images or Videos · up to 10 files
                        </div>
                        {files.length > 0 && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--primary)', marginTop: '0.25rem', fontWeight: 600 }}>
                                {files.length} file{files.length > 1 ? 's' : ''} selected
                            </div>
                        )}
                    </div>
                </div>
                <div style={{ padding: '1.25rem', borderTop: '1px solid var(--border)', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                    <button className="btn btn-light" onClick={onClose}>Cancel</button>
                    <button className="btn btn-danger" onClick={() => mutation.mutate({ title, description })} disabled={mutation.isPending || description.length < 50 || !title.trim()}>
                        {mutation.isPending ? 'Submitting...' : 'Raise Dispute'}
                    </button>
                </div>
            </div>
        </div>
    );
}

// --- Main Page ---

export default function OrderDetailPage() {
    const { orderId } = useParams();
    const navigate = useNavigate();
    const { user: authUser } = useAuthStore();
    const { showToast } = useToast();
    const queryClient = useQueryClient();
    const [showShipModal, setShowShipModal] = useState(false);
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [showDisputeModal, setShowDisputeModal] = useState(false);

    const cancelMutation = useMutation({
        mutationFn: () => cancelOrder(orderId),
        onSuccess: () => {
            showToast('Order cancelled and refund initiated', 'success');
            refetch();
        },
        onError: (err) => showToast(err?.response?.data?.detail || 'Failed to cancel order', 'error'),
    });

    const { data: order, isLoading, isError, refetch } = useQuery({
        queryKey: ['order', orderId],
        queryFn: () => getOrder(orderId),
        staleTime: 0,
    });

    const isBuyer = String(authUser?.id) === String(order?.buyer?.id);
    const isSeller = String(authUser?.id) === String(order?.seller?.id);
    const status = (order?.status || 'pending_shipment').toLowerCase();
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending_shipment;

    // Timeline Steps
    const timelineSteps = useMemo(() => {
        if (!order) return [];
        return [
            { label: 'Order Created', date: order.created_at, done: true },
            { label: 'Seller Ships', date: order.shipped_at, done: !!order.shipped_at },
            { label: 'Delivery Confirmed', date: order.delivered_at, done: !!order.delivered_at },
            { label: 'Completed', date: order.completed_at, done: !!order.completed_at },
        ];
    }, [order]);

    if (isLoading) {
        return (
            <div className="container py-5" style={{ maxWidth: 900 }}>
                <div className="skeleton" style={{ height: 32, width: 200, marginBottom: 24 }}></div>
                <div className="row g-4">
                    <div className="col-md-7"><div className="skeleton" style={{ height: 400, borderRadius: 'var(--radius-lg)' }}></div></div>
                    <div className="col-md-5"><div className="skeleton" style={{ height: 300, borderRadius: 'var(--radius-lg)' }}></div></div>
                </div>
            </div>
        );
    }

    if (isError || !order) {
        return (
            <div className="container py-5 text-center" style={{ maxWidth: 600 }}>
                <FiAlertCircle size={48} className="text-danger mb-3" />
                <h3>Order not found</h3>
                <p className="text-muted">We couldn't retrieve the details for this order.</p>
                <button className="btn btn-primary" onClick={() => navigate('/my-orders')}>Back to Orders</button>
            </div>
        );
    }

    const item = order.item || {};

    return (
        <div style={{ backgroundColor: 'var(--bg-color)', minHeight: 'calc(100vh - 72px)', padding: '2rem 0' }}>
            <div className="container" style={{ maxWidth: 1000 }}>
                {/* Back Button */}
                <button
                    onClick={() => navigate('/my-orders')}
                    style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem', fontWeight: 600 }}
                >
                    <FiArrowLeft /> Back to My Orders
                </button>

                <div className="row g-4">
                    {/* LEFT COLUMN */}
                    <div className="col-lg-7">
                        {/* Item Card */}
                        <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                            {item.primary_image_url && (
                                <img src={item.primary_image_url} alt={item.title} style={{ width: '100%', height: 260, objectFit: 'cover', borderBottom: '1px solid var(--border)' }} />
                            )}
                            <div className="card-body p-4">
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                    <h4 style={{ fontWeight: 800, margin: 0 }}>{item.title}</h4>
                                    <span className="badge" style={{ backgroundColor: 'var(--primary-50)', color: 'var(--primary)', textTransform: 'capitalize' }}>
                                        {item.condition?.replace('_', ' ')}
                                    </span>
                                </div>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                    {item.description}
                                </p>
                            </div>
                        </div>

                        {/* Timeline Card */}
                        <div className="card" style={{ borderRadius: 'var(--radius-lg)', padding: '1.5rem' }}>
                            <h6 style={{ fontWeight: 700, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <FiClock /> Tracking Timeline
                            </h6>
                            <div className="timeline">
                                {timelineSteps.map((step, i) => (
                                    <div key={i} className="d-flex gap-3 mb-4 last-mb-0" style={{ position: 'relative' }}>
                                        {i < timelineSteps.length - 1 && (
                                            <div style={{ position: 'absolute', left: 6, top: 20, bottom: -20, width: 2, backgroundColor: timelineSteps[i+1].done ? 'var(--success)' : 'var(--border)' }}></div>
                                        )}
                                        <div style={{ width: 14, height: 14, borderRadius: '50%', backgroundColor: step.done ? 'var(--success)' : 'var(--border)', flexShrink: 0, marginTop: 4, zIndex: 1 }}></div>
                                        <div>
                                            <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: step.done ? 'var(--text-primary)' : 'var(--text-muted)' }}>{step.label}</div>
                                            {step.date && (
                                                <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                                                    {new Date(step.date).toLocaleString('en-NG', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* RIGHT COLUMN */}
                    <div className="col-lg-5">
                        {/* Summary Card */}
                        <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', padding: '1.5rem' }}>
                            <h6 style={{ fontWeight: 700, marginBottom: '1.25rem' }}>Order Summary</h6>
                            <div className="d-flex justify-content-between mb-3">
                                <span className="text-muted">Order ID</span>
                                <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>#{order.id.slice(0, 8)}...</span>
                            </div>
                            <div className="d-flex justify-content-between mb-3">
                                <span className="text-muted">Status</span>
                                <span className="badge" style={{ backgroundColor: config.bg, color: config.color, borderRadius: 'var(--radius-full)' }}>{config.label}</span>
                            </div>
                            <hr />
                            <div className="d-flex justify-content-between mb-2" style={{ fontSize: '1.125rem', fontWeight: 800 }}>
                                <span>Total Amount</span>
                                <span className="text-primary">{formatNaira(order.amount)}</span>
                            </div>
                            {isSeller && (
                                <>
                                    <div className="d-flex justify-content-between mb-1" style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                        <span>Platform Commission</span>
                                        <span>- {formatNaira(order.commission_amount)}</span>
                                    </div>
                                    <div className="d-flex justify-content-between" style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                                        <span>Your Earnings</span>
                                        <span>{formatNaira(order.seller_payout)}</span>
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Escrow Card */}
                        <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', padding: '1.5rem', border: '1px solid var(--info-light)', backgroundColor: 'var(--info-50)' }}>
                            <div className="d-flex align-items-center gap-2 mb-2">
                                <FiShield className="text-info" size={18} />
                                <h6 style={{ margin: 0, fontWeight: 700 }}>SafePay Escrow</h6>
                            </div>
                            <div className="mb-2">
                                <span className="badge" style={{ backgroundColor: 'var(--info)', color: '#fff' }}>
                                    {order.escrow?.status}
                                </span>
                            </div>
                            {order.escrow?.status === 'HOLDING' && order.escrow?.auto_release_at && (
                                <div style={{ fontSize: '0.8125rem', color: 'var(--info-600)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                    <FiClock /> Funds auto-release on {new Date(order.escrow.auto_release_at).toLocaleDateString()}
                                </div>
                            )}
                            {order.escrow?.status === 'RELEASED' && order.escrow?.released_at && (
                                <div style={{ fontSize: '0.8125rem', color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                    <FiCheckCircle /> Payment released to seller
                                </div>
                            )}
                        </div>

                        {/* Parties Card */}
                        <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', padding: '1.25rem' }}>
                            <div className="mb-3">
                                <div className="text-muted mb-2" style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Seller</div>
                                <div className="d-flex align-items-center gap-2">
                                    <div style={{ width: 32, height: 32, borderRadius: '50%', backgroundColor: 'var(--surface)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        <FiUser />
                                    </div>
                                    <span style={{ fontWeight: 600 }}>{order.seller?.first_name} {order.seller?.last_name}</span>
                                    {order.seller?.is_verified_seller && <FiCheckCircle className="text-primary" size={14} />}
                                </div>
                            </div>
                            <div>
                                <div className="text-muted mb-2" style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Buyer</div>
                                <div className="d-flex align-items-center gap-2">
                                    <div style={{ width: 32, height: 32, borderRadius: '50%', backgroundColor: 'var(--surface)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        <FiUser />
                                    </div>
                                    <span style={{ fontWeight: 600 }}>{order.buyer?.first_name} {order.buyer?.last_name}</span>
                                </div>
                            </div>
                        </div>

                        {/* Tracking Card */}
                        {order.shipped_at && (
                            <div className="card mb-4" style={{ borderRadius: 'var(--radius-lg)', padding: '1.25rem' }}>
                                <h6 style={{ fontSize: '0.875rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <FiTruck className="text-primary" /> Delivery Details
                                </h6>
                                <div className="d-flex align-items-center gap-2 mb-2">
                                    <span className="text-muted" style={{ fontSize: '0.875rem' }}>Tracking:</span>
                                    <span style={{ fontWeight: 700, fontFamily: 'monospace' }}>{order.tracking_number || 'No tracking provided'}</span>
                                </div>
                            </div>
                        )}

                        {/* Actions Card */}
                        <div className="card" style={{ borderRadius: 'var(--radius-lg)', padding: '1.5rem', backgroundColor: 'var(--surface)' }}>
                            {isBuyer && status === 'pending_shipment' && (
                                <>
                                    {order.shipping_deadline_at && new Date(order.shipping_deadline_at) < new Date() && (
                                        <>
                                            <button
                                                className="btn btn-outline-danger w-100 mb-2"
                                                onClick={() => cancelMutation.mutate()}
                                                disabled={cancelMutation.isPending}
                                            >
                                                {cancelMutation.isPending ? 'Cancelling...' : 'Cancel Order & Get Refund'}
                                            </button>
                                            <p className="text-muted text-center" style={{ fontSize: '0.75rem', margin: 0 }}>
                                                Seller missed the shipping deadline. You are eligible for a full refund.
                                            </p>
                                        </>
                                    )}
                                    {order.shipping_deadline_at && new Date(order.shipping_deadline_at) >= new Date() && (
                                        <p className="text-muted text-center" style={{ fontSize: '0.8125rem', margin: 0 }}>
                                            Waiting for seller to ship. Deadline: {new Date(order.shipping_deadline_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short', year: 'numeric' })}
                                        </p>
                                    )}
                                </>
                            )}
                            {isSeller && status === 'pending_shipment' && (
                                <>
                                    <button className="btn btn-primary w-100 mb-2" onClick={() => setShowShipModal(true)}>Mark as Shipped</button>
                                    <p className="text-muted text-center" style={{ fontSize: '0.75rem', margin: 0 }}>Update the order once you have handed it to the courier.</p>
                                </>
                            )}
                            {isBuyer && status === 'shipped' && (
                                <>
                                    <button className="btn btn-primary w-100 mb-2" onClick={() => setShowConfirmModal(true)}>Confirm Delivery</button>
                                    <button className="btn btn-outline-danger w-100 mb-2" onClick={() => setShowDisputeModal(true)}>Raise Dispute</button>
                                    <p className="text-muted text-center" style={{ fontSize: '0.75rem', margin: 0 }}>Confirming will release funds to the seller. Use dispute if item is missing or damaged.</p>
                                </>
                            )}
                            {status === 'disputed' && (
                                <div>
                                    <div className="d-flex align-items-center gap-2 mb-3">
                                        <FiAlertCircle size={20} className="text-danger" />
                                        <h6 style={{ fontWeight: 700, margin: 0 }}>Dispute Raised</h6>
                                    </div>
                                    {order.dispute && (
                                        <div style={{ backgroundColor: 'var(--danger-light)', borderRadius: 'var(--radius)', padding: '1rem', marginBottom: '1rem' }}>
                                            <div style={{ fontWeight: 700, fontSize: '0.9375rem', marginBottom: '0.4rem' }}>
                                                {order.dispute.title}
                                            </div>
                                            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', lineHeight: 1.5 }}>
                                                {order.dispute.description}
                                            </div>
                                            <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                                                Raised by: {String(order.dispute.raised_by_id) === String(order.buyer?.id) ? 'Buyer' : 'Seller'}
                                            </div>
                                            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                                Opened: {new Date(order.dispute.created_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short', year: 'numeric' })}
                                            </div>
                                            {/* Evidence thumbnails preview */}
                                            {order.dispute.evidence?.length > 0 && (
                                                <div style={{ marginTop: '0.75rem' }}>
                                                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                                                        {order.dispute.evidence.length} evidence file{order.dispute.evidence.length > 1 ? 's' : ''} attached
                                                    </div>
                                                    <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                                                        {order.dispute.evidence.slice(0, 4).map((ev) => (
                                                            ev.file_type === 'IMAGE' ? (
                                                                <a key={ev.id} href={ev.url} target="_blank" rel="noopener noreferrer">
                                                                    <img src={ev.url} alt="evidence" style={{ width: 44, height: 44, objectFit: 'cover', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }} />
                                                                </a>
                                                            ) : (
                                                                <a key={ev.id} href={ev.url} target="_blank" rel="noopener noreferrer" style={{ width: 44, height: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: '0.6875rem', color: 'var(--text-muted)', fontWeight: 700 }}>
                                                                    VID
                                                                </a>
                                                            )
                                                        ))}
                                                        {order.dispute.evidence.length > 4 && (
                                                            <div style={{ width: 44, height: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700 }}>
                                                                +{order.dispute.evidence.length - 4}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    <p className="text-muted" style={{ fontSize: '0.8125rem', margin: '0 0 1rem' }}>
                                        Our support team is reviewing this dispute. Both parties will be notified of the outcome.
                                    </p>
                                    {order.dispute?.id && (
                                        <button
                                            className="btn btn-outline-danger w-100"
                                            style={{ fontWeight: 600 }}
                                            onClick={() => navigate(`/disputes/${order.dispute.id}`)}
                                        >
                                            View Dispute Details
                                        </button>
                                    )}
                                </div>
                            )}
                            {status === 'completed' && (
                                <div className="text-center py-2">
                                    <FiCheckCircle size={32} className="text-success mb-2" />
                                    <h6 style={{ fontWeight: 700, margin: 0 }}>Order Completed</h6>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <ShipOrderModal show={showShipModal} orderId={orderId} onClose={() => setShowShipModal(false)} onSuccess={refetch} />
            <ConfirmDeliveryModal show={showConfirmModal} orderId={orderId} onClose={() => setShowConfirmModal(false)} onSuccess={refetch} />
            <RaiseDisputeModal show={showDisputeModal} orderId={orderId} onClose={() => setShowDisputeModal(false)} onSuccess={refetch} />
        </div>
    );
}
