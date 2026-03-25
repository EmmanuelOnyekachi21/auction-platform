import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';

export default function BecomeSellerPage() {
    const [sellerType, setSellerType] = useState('CASUAL');
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(false);
    const { register, handleSubmit, formState: { errors } } = useForm();
    const navigate = useNavigate();

    const addDocument = () => {
        setDocuments([...documents, { url: '', doc_type: 'National ID' }])
    };

    const updateDocument = (index, field, value) => {
        const updated = [...documents];
        updated[index][field] = value;
        setDocuments(updated);
    };

    const removeDocument = (index) => {
        setDocuments(documents.filter((_, i) => i !== index));
    };

    const onSubmit = async (data) => {
        setLoading(true);
        try {
            // Register as seller
            await apiClient.post('/users/me/seller-profile', {
                seller_type: sellerType,
                bio: data.bio,
                business_name: data.business_name
            });

            // Upload documents
            for (const doc of documents) {
                if (doc.url) {
                    await apiClient.post('/users/me/seller-profile/documents', null, {
                        params: { url: doc.url, doc_type: doc.doc_type }
                    });
                }
            }

            alert('Seller registration successful! Pending verification.');
            navigate('/profile');
        } catch (error) {
            console.error('Failed to register as seller:', error);
            alert(error.response?.data?.detail || 'Failed to register as seller');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container mt-5">
            <div className="row">
                <div className="col-md-8 mx-auto">
                    <div className="card">
                        <div className="card-header">
                            <h3>Become a Seller</h3>
                        </div>
                        <div className="card-body">
                            <form onSubmit={handleSubmit(onSubmit)}>
                                <div className="mb-3">
                                    <label className="form-label">Seller Type</label>
                                    <div>
                                        <div className="form-check">
                                            <input
                                                className="form-check-input"
                                                type="radio"
                                                value="CASUAL"
                                                checked={sellerType === 'CASUAL'}
                                                onChange={(e) => setSellerType(e.target.value)}
                                            />
                                            <label className="form-check-label">Casual - Individual seller</label>
                                        </div>
                                        <div className="form-check">
                                            <input
                                                className="form-check-input"
                                                type="radio"
                                                value="RETAIL"
                                                checked={sellerType === 'RETAIL'}
                                                onChange={(e) => setSellerType(e.target.value)}
                                            />
                                            <label className="form-check-label">Retail - Small business</label>
                                        </div>
                                        <div className="form-check">
                                            <input
                                                className="form-check-input"
                                                type="radio"
                                                value="WHOLESALE"
                                                checked={sellerType === 'WHOLESALE'}
                                                onChange={(e) => setSellerType(e.target.value)}
                                            />
                                            <label className="form-check-label">Wholesale - Large scale business</label>
                                        </div>
                                    </div>
                                </div>

                                {(sellerType === 'RETAIL' || sellerType === 'WHOLESALE') && (
                                    <div className="mb-3">
                                        <label className="form-label">Business Name *</label>
                                        <input
                                            {...register('business_name', { required: 'Business name is required for retail/wholesale' })}
                                            className="form-control"
                                        />
                                        {errors.business_name && (
                                            <div className="text-danger">{errors.business_name.message}</div>
                                        )}
                                    </div>
                                )}

                                <div className="mb-3">
                                    <label className="form-label">Bio</label>
                                    <textarea {...register('bio')} className="form-control" rows="3" />
                                </div>

                                <div className="mb-3">
                                    <label className="form-label">Verification Documents</label>
                                    <button type="button" className="btn btn-sm btn-secondary mb-2" onClick={addDocument}>
                                        Add Document
                                    </button>
                                    {documents.map((doc, index) => (
                                        <div key={index} className="card mb-2">
                                            <div className="card-body">
                                                <div className="row">
                                                    <div className="col-md-5">
                                                        <input
                                                            type="url"
                                                            className="form-control"
                                                            placeholder="Document URL"
                                                            value={doc.url}
                                                            onChange={(e) => updateDocument(index, 'url', e.target.value)}
                                                        />
                                                    </div>
                                                    <div className="col-md-5">
                                                        <select
                                                            className="form-select"
                                                            value={doc.doc_type}
                                                            onChange={(e) => updateDocument(index, 'doc_type', e.target.value)}
                                                        >
                                                            <option value="National ID">National ID</option>
                                                            <option value="Business Registration">Business Registration</option>
                                                            <option value="CAC">CAC Document</option>
                                                        </select>
                                                    </div>
                                                    <div className="col-md-2">
                                                        <button
                                                            type="button"
                                                            className="btn btn-danger btn-sm"
                                                            onClick={() => removeDocument(index)}
                                                        >
                                                            Remove
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                <button type="submit" className="btn btn-primary" disabled={loading}>
                                    {loading ? 'Submitting...' : 'Submit for Verification'}
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
