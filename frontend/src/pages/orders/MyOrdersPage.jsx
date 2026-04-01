import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    FiShoppingBag, FiArrowRight, FiClock,
    FiCheckCircle, FiAlertCircle, FiXCircle,
    FiInbox, FiTruck, FiPackage, FiRotateCcw, FiHelpCircle, FiX
} from 'react-icons/fi';
import { getMyOrders, shipOrder, confirmDelivery, raiseDispute } from '../../api/orders';
import { useAuthStore } from '../../store/authStore';
import { useToast } from '../../components/common/Toast';

const formatNaira = (amount) =>
    Number(amount || 0).toLocaleString('en-NG', { style: 'currency', currency: 'NGN', minimumFractionDigits: 0 });

const PAGE_SIZE = 20;

const STATUS_CONFIG = {
    pending_shipment: { label: 'Awaiting Shipment', bg: '#FEF3C7', color: '#D97706' },
    shipped: { label: 'Shipped', bg: 'var(--info-light)', color: 'var(--info)' },
    delivered: { label: 'Delivered', bg: '#CCFBF1', color: '#0D9488' },
    completed: { label: 'Completed', bg: 'var(--success-light)', color: 'var(--success)' },
    cancelled: { label: 'Cancelled', bg: '#F1F5F9', color: 'var(--text-muted)' },
    disputed: { label: 'Disputed', bg: 'var(--danger-light)', color: 'var(--danger)' },
    refunded: { label: 'Refunded', bg: '#F3E8FF', color: '#7C3AED' }
};

// --- Modal Components ---

function ShipOrderModal({ show, onClose, orderId }) {
    const [trackingNumber, setTrackingNumber] = useState('');
    const { showToast } = useToast();
    const queryClient = useQueryClient();

    const mutation = useMutation({
        mutationFn: (data) => shipOrder(orderId, data),
        onSuccess: () => {
            showToast('Order marked as shipped!', 'success');
            queryClient.invalidateQueries({ queryKey: ['order', orderId] });
            queryClient.invalidateQueries({ queryKey: ['my-orders'] });
            onClose();
        },
        onError: (error) => {
            showToast(error?.response?.data?.detail || 'Failed to mark as shipped', 'error');
        }
    });

    if (!show) return null;

    return (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050, padding: '1rem' }} onClick={onClose}>
            <div style={{ backgroundColor: 'var(--card-bg)', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: 450, overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
                <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ width: 40, height: 40, borderRadius: 'var(--radius)', backgroundColor: 'var(--primary-50)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <FiTruck size={20} />
                        </div>
                        <h5 style={{ margin: 0, fontWeight: 700 }}>Ship Order</h5>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)' }}><FiX size={20} /></button>
                </div>
                <div style={{ padding: '1.5rem' }}>
                    <div className="mb-3">
                        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                            Confirm that you have handed the item to a courier or delivery service for shipment.
                        </p>
                        <label className="form-label" style={{ fontSize: '0.875rem', fontWeight: 600 }}>
                            Tracking Number <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(optional)</span>
                        </label>
                        <input
                            type="text"
                            className="form-control"
                            placeholder="e.g. GIGL-123456 — leave blank if unavailable"
                            value={trackingNumber}
                            onChange={e => setTrackingNumber(e.target.value)}
                            disabled={mutation.isPending}
                        />
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                            If your courier gave you a tracking code, enter it here so the buyer can follow up. You can skip this if you don't have one.
                        </div>
                    </div>
                </div>
                <div style={{ padding: '1.25rem', borderTop: '1px solid var(--border)', backgroundColor: 'var(--surface)', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                    <button className="btn btn-light" style={{ fontWeight: 600 }} onClick={onClose} disabled={mutation.isPending}>Cancel</button>
                    <button className="btn btn-primary" style={{ fontWeight: 600 }} onClick={() => mutation.mutate({ tracking_number: trackingNumber })} disabled={mutation.isPending}>
                        {mutation.isPending ? 'Processing...' : 'Confirm Shipment'}
                    </button>
                </div>
            </div>
        </div>
    );
}

function ConfirmDeliveryModal({ show, onClose, orderId }) {
    const { showToast } = useToast();
    const queryClient = useQueryClient();

    const mutation = useMutation({
        mutationFn: () => confirmDelivery(orderId),
        onSuccess: () => {
            showToast('Payment released to seller', 'success');
            queryClient.invalidateQueries({ queryKey: ['order', orderId] });
            queryClient.invalidateQueries({ queryKey: ['my-orders'] });
            onClose();
        },
        onError: (error) => {
            showToast(error?.response?.data?.detail || 'Failed to confirm delivery', 'error');
        }
    });

    if (!show) return null;

    return (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050, padding: '1rem' }} onClick={onClose}>
            <div style={{ backgroundColor: 'var(--card-bg)', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: 450, overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
                <div style={{ padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ width: 56, height: 56, borderRadius: '50%', backgroundColor: 'var(--success-light)', color: 'var(--success)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.25rem' }}>
                        <FiCheckCircle size={32} />
                    </div>
                    <h5 style={{ fontWeight: 700, marginBottom: '0.75rem' }}>Confirm Delivery?</h5>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem', lineHeight: 1.6 }}>
                        Confirming delivery will release payment to the seller. Are you sure?
                    </p>
                </div>
                <div style={{ padding: '1.25rem', borderTop: '1px solid var(--border)', backgroundColor: 'var(--surface)', display: 'flex', gap: '0.75rem' }}>
                    <button className="btn btn-light w-100" style={{ fontWeight: 600 }} onClick={onClose} disabled={mutation.isPending}>Cancel</button>
                    <button className="btn btn-primary w-100" style={{ fontWeight: 600 }} onClick={() => mutation.mutate()} disabled={mutation.isPending}>
                        {mutation.isPending ? 'Confirming...' : 'Confirm Delivery'}
                    </button>
                </div>
            </div>
        </div>
    );
}

function RaiseDisputeModal({ show, onClose, orderId }) {
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const { showToast } = useToast();
    const queryClient = useQueryClient();

    const mutation = useMutation({
        mutationFn: (data) => raiseDispute(orderId, data),
        onSuccess: () => {
            showToast('Dispute raised successfully', 'success');
            queryClient.invalidateQueries({ queryKey: ['order', orderId] });
            queryClient.invalidateQueries({ queryKey: ['my-orders'] });
            onClose();
        },
        onError: (error) => {
            showToast(error?.response?.data?.detail || 'Failed to raise dispute', 'error');
        }
    });

    if (!show) return null;

    const isValid = title.trim() && description.trim().length >= 50;

    return (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050, padding: '1rem' }} onClick={onClose}>
            <div style={{ backgroundColor: 'var(--card-bg)', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: 500, overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
                <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ width: 40, height: 40, borderRadius: 'var(--radius)', backgroundColor: 'var(--danger-light)', color: 'var(--danger)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <FiAlertCircle size={20} />
                        </div>
                        <h5 style={{ margin: 0, fontWeight: 700 }}>Raise Dispute</h5>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)' }}><FiX size={20} /></button>
                </div>
                <div style={{ padding: '1.5rem' }}>
                    <div className="mb-3">
                        <label className="form-label" style={{ fontSize: '0.875rem', fontWeight: 600 }}>Dispute Title</label>
                        <input
                            type="text"
                            className="form-control"
                            placeholder="Briefly state the issue"
                            value={title}
                            onChange={e => setTitle(e.target.value)}
                            disabled={mutation.isPending}
                        />
                    </div>
                    <div className="mb-3">
                        <label className="form-label" style={{ fontSize: '0.875rem', fontWeight: 600 }}>Detailed Description</label>
                        <textarea
                            className="form-control"
                            rows={4}
                            placeholder="Describe what happened. Be as detailed as possible."
                            value={description}
                            onChange={e => setDescription(e.target.value)}
                            style={{ resize: 'none' }}
                            disabled={mutation.isPending}
                        />
                        <div className="d-flex justify-content-between mt-1">
                            <span style={{ fontSize: '0.75rem', color: description.length < 50 ? 'var(--danger)' : 'var(--success)' }}>
                                {description.length < 50 ? `Minimum 50 characters: ${description.length}/50` : `${description.length} characters`}
                            </span>
                        </div>
                    </div>
                </div>
                <div style={{ padding: '1.25rem', borderTop: '1px solid var(--border)', backgroundColor: 'var(--surface)', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                    <button className="btn btn-light" style={{ fontWeight: 600 }} onClick={onClose} disabled={mutation.isPending}>Cancel</button>
                    <button className="btn btn-danger" style={{ fontWeight: 600 }} onClick={() => mutation.mutate({ title, description })} disabled={mutation.isPending || !isValid}>
                        {mutation.isPending ? 'Submitting...' : 'Raise Dispute'}
                    </button>
                </div>
            </div>
        </div>
    );
}

// --- List Items ---

function OrderCard({ order, role, onShip, onConfirm, onDispute }) {
    const navigate = useNavigate();
    const item = order.item || {};
    const status = (order.status || 'pending_shipment').toLowerCase();
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending_shipment;

    const isBuyer = role === 'buyer';
    const isSeller = role === 'seller';

    // Action Logic
    const renderActions = () => {
        if (isSeller && status === 'pending_shipment') {
            return <button className="btn btn-primary btn-sm w-100 mt-2" onClick={(e) => { e.stopPropagation(); onShip(order.id); }}>Mark as Shipped</button>;
        }
        if (isBuyer && status === 'shipped') {
            return (
                <div className="d-flex gap-2 mt-2 w-100">
                    <button className="btn btn-primary btn-sm flex-grow-1" onClick={(e) => { e.stopPropagation(); onConfirm(order.id); }}>Confirm Delivery</button>
                    <button className="btn btn-outline-danger btn-sm" onClick={(e) => { e.stopPropagation(); onDispute(order.id); }} style={{ whiteSpace: 'nowrap' }}>Dispute</button>
                </div>
            );
        }
        if (status === 'disputed') {
            return <button className="btn btn-outline-secondary btn-sm w-100 mt-2" onClick={(e) => { e.stopPropagation(); navigate(`/orders/${order.id}`); }}>View Dispute</button>;
        }

        // Cancel logic
        if (isBuyer && status === 'pending_shipment') {
             const deadline = new Date(order.shipping_deadline_at);
             if (deadline < new Date()) {
                 return <button className="btn btn-outline-danger btn-sm w-100 mt-2" onClick={(e) => { e.stopPropagation(); navigate(`/orders/${order.id}`); }}>Cancel Order</button>;
             }
        }

        return <button className="btn btn-outline-secondary btn-sm w-100 mt-2" onClick={(e) => { e.stopPropagation(); navigate(`/orders/${order.id}`); }}>View Details</button>;
    };

    return (
        <div
            className="card mb-3"
            style={{ borderRadius: 'var(--radius-lg)', padding: '1rem', cursor: 'pointer', border: '1px solid var(--border)' }}
            onClick={() => navigate(`/orders/${order.id}`)}
        >
            <div className="d-flex gap-3 align-items-center">
                {/* Left: Thumbnail */}
                <div style={{ width: 64, height: 64, borderRadius: 'var(--radius)', overflow: 'hidden', backgroundColor: '#F1F5F9', flexShrink: 0 }}>
                    {item.primary_image_url ? (
                        <img src={item.primary_image_url} alt={item.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                            <FiPackage size={24} />
                        </div>
                    )}
                </div>

                {/* Middle: Details */}
                <div className="flex-grow-1 min-w-0">
                    <div style={{ fontWeight: 700, fontSize: '0.9375rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--text-primary)' }}>
                        {item.title || 'Unknown Item'}
                    </div>
                    <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>
                        Ordered {new Date(order.created_at).toLocaleDateString('en-NG', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </div>
                    <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.125rem' }}>
                        {isBuyer ? `Seller: ${order.seller?.first_name ?? ''} ${order.seller?.last_name ?? ''}`.trim() || 'Seller info unavailable' : `Buyer: ${order.buyer?.first_name ?? ''} ${order.buyer?.last_name ?? ''}`.trim() || 'Buyer info unavailable'}
                    </div>
                </div>

                {/* Right: Price & Status */}
                <div className="text-end d-none d-sm-block" style={{ minWidth: 120 }}>
                    <div style={{ fontWeight: 800, fontSize: '1.0625rem', color: 'var(--text-primary)' }}>
                        {formatNaira(order.amount)}
                    </div>
                    <span
                        className="badge mt-1"
                        style={{
                            borderRadius: 'var(--radius-full)', fontSize: '0.7rem', fontWeight: 700,
                            padding: '0.3em 0.75em', backgroundColor: config.bg, color: config.color
                        }}
                    >
                        {config.label}
                    </span>
                </div>
            </div>

            {/* Mobile Footer & Actions */}
            <div className="mt-2 pt-2 border-top d-sm-none d-flex justify-content-between align-items-center">
                <div style={{ fontWeight: 700 }}>{formatNaira(order.amount)}</div>
                <span
                    className="badge"
                    style={{
                        borderRadius: 'var(--radius-full)', fontSize: '0.65rem', fontWeight: 700,
                        padding: '0.3em 0.75em', backgroundColor: config.bg, color: config.color
                    }}
                >
                    {config.label}
                </span>
            </div>

            <div className="d-block">
                {renderActions()}
            </div>
        </div>
    );
}

// --- Main Page ---

export default function MyOrdersPage() {
    const navigate = useNavigate();
    const { user } = useAuthStore();
    const [role, setRole] = useState('buyer'); // 'buyer' or 'seller'
    const [page, setPage] = useState(1);
    const [allOrders, setAllOrders] = useState([]);

    // Modal states
    const [shipModalOrder, setShipModalOrder] = useState(null);
    const [confirmModalOrder, setConfirmModalOrder] = useState(null);
    const [disputeModalOrder, setDisputeModalOrder] = useState(null);

    const { data: orderResponse, isLoading, isError, isFetching } = useQuery({
        queryKey: ['my-orders', role, page],
        queryFn: () => getMyOrders({ role, page, limit: PAGE_SIZE }),
        placeholderData: (prev) => prev,
    });

    const orders = orderResponse?.data || [];
    const pagination = orderResponse?.pagination || {};
    const hasMore = page < (pagination?.total_pages || 1);

    useEffect(() => {
        if (page === 1) {
            setAllOrders(orders);
        } else {
            setAllOrders(prev => {
                const existingIds = new Set(prev.map(o => o.id));
                const filtered = orders.filter(o => !existingIds.has(o.id));
                return [...prev, ...filtered];
            });
        }
    }, [orders, page]);

    const handleRoleChange = (newRole) => {
        setRole(newRole);
        setPage(1);
        setAllOrders([]);
    };

    return (
        <div style={{ minHeight: 'calc(100vh - 72px)', backgroundColor: 'var(--bg-color)', padding: '2rem 0' }}>
            <div className="container" style={{ maxWidth: 800 }}>
                {/* Header */}
                <div className="d-flex align-items-center gap-3 mb-4">
                    <div style={{ width: 48, height: 48, borderRadius: 'var(--radius)', backgroundColor: 'var(--primary-50)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <FiShoppingBag size={24} />
                    </div>
                    <div>
                        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>My Orders</h1>
                        <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-muted)' }}>Manage your purchases and sales</p>
                    </div>
                </div>

                {/* Tabs */}
                <div className="d-flex mb-4 gap-2">
                    {['buyer', 'seller'].map(r => (
                        <button
                            key={r}
                            onClick={() => handleRoleChange(r)}
                            style={{
                                padding: '0.5rem 1.25rem',
                                borderRadius: 'var(--radius-full)',
                                fontSize: '0.875rem',
                                fontWeight: 700,
                                border: '1px solid ' + (role === r ? 'var(--primary)' : 'var(--border)'),
                                backgroundColor: role === r ? 'var(--primary)' : 'var(--card-bg)',
                                color: role === r ? '#fff' : 'var(--text-secondary)',
                                transition: 'all 0.2s'
                            }}
                        >
                            {r.charAt(0).toUpperCase() + r.slice(1)}
                        </button>
                    ))}
                </div>

                {/* Content */}
                {isError ? (
                    <div className="card p-5 text-center" style={{ borderRadius: 'var(--radius-lg)' }}>
                        <FiAlertCircle size={40} className="text-danger mb-3 mx-auto" />
                        <h5>Failed to load orders</h5>
                        <p className="text-muted">There was an error connecting to the server.</p>
                        <button className="btn btn-primary d-inline-block mx-auto mt-2" onClick={() => window.location.reload()}>Retry</button>
                    </div>
                ) : !isLoading && allOrders.length === 0 ? (
                    <div className="card p-5 text-center" style={{ borderRadius: 'var(--radius-lg)', borderStyle: 'dashed', backgroundColor: 'transparent' }}>
                        <FiInbox size={48} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} className="mx-auto" />
                        <h5 style={{ fontWeight: 700 }}>{role === 'buyer' ? 'No purchases yet' : 'No sales yet'}</h5>
                        <p className="text-muted" style={{ fontSize: '0.9375rem' }}>
                            {role === 'buyer' ? 'Find something to bid on!' : 'List an item to get started!'}
                        </p>
                        <button
                            className="btn btn-primary mx-auto mt-3"
                            onClick={() => navigate(role === 'buyer' ? '/auctions' : '/seller/create-auction')}
                        >
                            {role === 'buyer' ? 'Browse Auctions' : 'Create Auction'}
                        </button>
                    </div>
                ) : (
                    <>
                        <div className="order-list">
                            {allOrders.map(order => (
                                <OrderCard
                                    key={order.id}
                                    order={order}
                                    role={role}
                                    onShip={setShipModalOrder}
                                    onConfirm={setConfirmModalOrder}
                                    onDispute={setDisputeModalOrder}
                                />
                            ))}
                        </div>

                        {isLoading && (
                            <div className="d-flex flex-column gap-3">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="card p-3 d-flex flex-row gap-3" style={{ borderRadius: 'var(--radius-lg)' }}>
                                        <div className="skeleton" style={{ width: 64, height: 64, borderRadius: 'var(--radius)' }}></div>
                                        <div className="flex-grow-1">
                                            <div className="skeleton" style={{ height: 16, width: '60%', marginBottom: 8 }}></div>
                                            <div className="skeleton" style={{ height: 12, width: '40%' }}></div>
                                        </div>
                                        <div className="text-end">
                                            <div className="skeleton" style={{ height: 20, width: 80, marginLeft: 'auto', marginBottom: 8 }}></div>
                                            <div className="skeleton" style={{ height: 16, width: 60, marginLeft: 'auto' }}></div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {!isLoading && hasMore && (
                            <div className="text-center mt-4">
                                <button
                                    className="btn btn-outline-primary"
                                    style={{ borderRadius: 'var(--radius-full)', padding: '0.625rem 2rem', fontWeight: 700 }}
                                    onClick={() => setPage(p => p + 1)}
                                    disabled={isFetching}
                                >
                                    {isFetching ? 'Loading...' : 'Load More Orders'}
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* Modals */}
            <ShipOrderModal show={!!shipModalOrder} orderId={shipModalOrder} onClose={() => setShipModalOrder(null)} />
            <ConfirmDeliveryModal show={!!confirmModalOrder} orderId={confirmModalOrder} onClose={() => setConfirmModalOrder(null)} />
            <RaiseDisputeModal show={!!disputeModalOrder} orderId={disputeModalOrder} onClose={() => setDisputeModalOrder(null)} />
        </div>
    );
}
