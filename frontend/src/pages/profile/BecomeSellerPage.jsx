import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';
import { FiUser, FiShoppingBag, FiTruck, FiFileText, FiPlus, FiX, FiArrowRight, FiCheck } from 'react-icons/fi';

const SELLER_TYPES = [
    { value: 'CASUAL', label: 'Casual', desc: 'Individual seller — sell your personal items', icon: <FiUser size={20} /> },
    { value: 'RETAIL', label: 'Retail', desc: 'Small business — sell regularly on the platform', icon: <FiShoppingBag size={20} /> },
    { value: 'WHOLESALE', label: 'Wholesale', desc: 'Large-scale business operations', icon: <FiTruck size={20} /> },
];

export default function BecomeSellerPage() {
    const [sellerType, setSellerType] = useState('CASUAL');
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(false);
    const { register, handleSubmit, formState: { errors } } = useForm();
    const { showToast } = useToast();
    const navigate = useNavigate();

    const addDocument = () => setDocuments([...documents, { url: '', doc_type: 'National ID' }]);
    const updateDocument = (index, field, value) => { const u = [...documents]; u[index][field] = value; setDocuments(u); };
    const removeDocument = (index) => setDocuments(documents.filter((_, i) => i !== index));

    const onSubmit = async (data) => {
        setLoading(true);
        try {
            await apiClient.post('/users/me/seller-profile', { seller_type: sellerType, bio: data.bio, business_name: data.business_name });
            for (const doc of documents) {
                if (doc.url) await apiClient.post('/users/me/seller-profile/documents', null, { params: { url: doc.url, doc_type: doc.doc_type } });
            }
            showToast('Seller registration successful! Pending verification.', 'success');
            navigate('/profile');
        } catch (error) {
            showToast(error.response?.data?.detail || 'Failed to register as seller', 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page-container" style={{ maxWidth: 700 }}>
            <div className="mb-4">
                <h1 style={{ fontWeight: 800, fontSize: '1.75rem', margin: '0 0 0.25rem' }}>Become a Seller</h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem', margin: 0 }}>Start listing items on Nohans and reach thousands of buyers.</p>
            </div>

            <div className="card" style={{ borderRadius: 'var(--radius-xl)' }}>
                <div className="card-body p-4">
                    <form onSubmit={handleSubmit(onSubmit)}>
                        {/* Seller Type */}
                        <div className="mb-4">
                            <label className="form-label" style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>Seller Type</label>
                            <div className="row g-3">
                                {SELLER_TYPES.map((t) => (
                                    <div className="col-md-4" key={t.value}>
                                        <div
                                            onClick={() => setSellerType(t.value)}
                                            style={{
                                                padding: '1rem',
                                                borderRadius: 'var(--radius-lg)',
                                                border: `2px solid ${sellerType === t.value ? 'var(--primary)' : 'var(--border)'}`,
                                                background: sellerType === t.value ? 'var(--primary-50)' : 'var(--card-bg)',
                                                cursor: 'pointer',
                                                transition: 'var(--transition)',
                                                position: 'relative',
                                            }}
                                        >
                                            {sellerType === t.value && (
                                                <div style={{ position: 'absolute', top: 8, right: 8, width: 20, height: 20, borderRadius: 'var(--radius-full)', background: 'var(--primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                    <FiCheck size={12} />
                                                </div>
                                            )}
                                            <div style={{ color: sellerType === t.value ? 'var(--primary)' : 'var(--text-muted)', marginBottom: '0.5rem' }}>{t.icon}</div>
                                            <div style={{ fontWeight: 700, fontSize: '0.875rem', marginBottom: '0.25rem' }}>{t.label}</div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t.desc}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {(sellerType === 'RETAIL' || sellerType === 'WHOLESALE') && (
                            <div className="mb-3">
                                <label className="form-label">Business Name</label>
                                <input {...register('business_name', { required: 'Business name is required' })} className={`form-control ${errors.business_name ? 'is-invalid' : ''}`} />
                                {errors.business_name && <div className="invalid-feedback">{errors.business_name.message}</div>}
                            </div>
                        )}

                        <div className="mb-4">
                            <label className="form-label">Seller Bio</label>
                            <textarea {...register('bio')} className="form-control" rows="3" placeholder="Tell buyers about yourself or your business..." />
                        </div>

                        {/* Documents */}
                        <div className="mb-4">
                            <div className="d-flex align-items-center justify-content-between mb-2">
                                <label className="form-label mb-0" style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>
                                    <FiFileText size={15} style={{ marginRight: '0.25rem' }} /> Verification Documents
                                </label>
                                <button type="button" className="btn btn-outline-primary btn-sm" onClick={addDocument}>
                                    <FiPlus size={13} /> Add
                                </button>
                            </div>
                            {documents.length === 0 && (
                                <div style={{ padding: '1.5rem', background: 'var(--surface)', borderRadius: 'var(--radius)', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                                    No documents added yet. Click &quot;Add&quot; to upload verification documents.
                                </div>
                            )}
                            {documents.map((doc, index) => (
                                <div key={index} style={{ padding: '0.75rem', border: '1px solid var(--border)', borderRadius: 'var(--radius)', marginBottom: '0.5rem', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                                    <input type="url" className="form-control form-control-sm" placeholder="Document URL" value={doc.url} onChange={(e) => updateDocument(index, 'url', e.target.value)} style={{ flex: '2 1 200px' }} />
                                    <select className="form-select form-select-sm" value={doc.doc_type} onChange={(e) => updateDocument(index, 'doc_type', e.target.value)} style={{ flex: '1 1 150px' }}>
                                        <option value="National ID">National ID</option>
                                        <option value="Business Registration">Business Registration</option>
                                        <option value="CAC">CAC Document</option>
                                    </select>
                                    <button type="button" className="btn btn-sm" style={{ color: 'var(--danger)' }} onClick={() => removeDocument(index)}>
                                        <FiX size={16} />
                                    </button>
                                </div>
                            ))}
                        </div>

                        <button type="submit" className="btn btn-primary w-100" disabled={loading} style={{ padding: '0.625rem' }}>
                            {loading ? <><span className="spinner-sm" /> Submitting...</> : <>Submit for Verification <FiArrowRight size={16} /></>}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
