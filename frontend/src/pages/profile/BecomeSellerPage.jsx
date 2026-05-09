import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';
import { useAuthStore } from '../../store/authStore';
import {
  FiUser, FiShoppingBag, FiTruck, FiFileText,
  FiPlus, FiX, FiArrowRight, FiCheck, FiUpload,
  FiExternalLink,
} from 'react-icons/fi';

const SELLER_TYPES = [
  { value: 'CASUAL',    label: 'Casual',    desc: 'Individual seller — sell your personal items',  icon: <FiUser size={20} /> },
  { value: 'RETAIL',    label: 'Retail',    desc: 'Small business — sell regularly on the platform', icon: <FiShoppingBag size={20} /> },
  { value: 'WHOLESALE', label: 'Wholesale', desc: 'Large-scale business operations',                icon: <FiTruck size={20} /> },
];

const DOC_TYPES = [
  'National ID',
  'Driver\'s License',
  'International Passport',
  'Business Registration',
  'CAC Document',
  'Utility Bill',
];

// Upload a single file to the backend, returns the saved doc object
async function uploadDocFile(file, docType) {
  const form = new FormData();
  form.append('file', file);
  form.append('doc_type', docType);
  const res = await apiClient.post('/users/me/seller-profile/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data; // { id, title, url, created_at }
}

export default function BecomeSellerPage() {
  const [sellerType, setSellerType] = useState('CASUAL');
  // Each entry: { id (temp), docType, file (File obj), status: 'pending'|'uploading'|'done'|'error', result: {...} }
  const [docs, setDocs] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm();
  const { showToast } = useToast();
  const { updateUser } = useAuthStore();
  const navigate = useNavigate();

  // Add a blank doc slot
  const addDocSlot = () =>
    setDocs(d => [...d, { id: Date.now(), docType: 'National ID', file: null, status: 'pending', result: null }]);

  const removeDoc = (id) => setDocs(d => d.filter(doc => doc.id !== id));

  const updateDocType = (id, docType) =>
    setDocs(d => d.map(doc => doc.id === id ? { ...doc, docType } : doc));

  // Stage the file locally — actual upload happens on form submit after profile is created
  const handleFileChange = (id, file) => {
    if (!file) return;
    setDocs(d => d.map(doc => doc.id === id ? { ...doc, file, status: 'pending' } : doc));
  };

  const onSubmit = async (data) => {
    if (docs.some(d => d.status === 'uploading')) {
      showToast('Please wait for all documents to finish uploading', 'error');
      return;
    }

    setSubmitting(true);
    try {
      // Step 1 — create the seller profile first (documents require it to exist)
      await apiClient.post('/users/me/seller-profile', {
        seller_type: sellerType,
        bio: data.bio,
        business_name: data.business_name || undefined,
      });

      // Step 2 — upload any pending documents now that the profile exists
      const pendingDocs = docs.filter(d => d.status === 'pending' && d.file);
      for (const doc of pendingDocs) {
        try {
          const result = await uploadDocFile(doc.file, doc.docType);
          setDocs(d => d.map(item => item.id === doc.id ? { ...item, status: 'done', result } : item));
        } catch {
          setDocs(d => d.map(item => item.id === doc.id ? { ...item, status: 'error' } : item));
        }
      }

      showToast('Application submitted! Pending verification.', 'success');

      // Refresh the store so the frontend reads the new PENDING status,
      // not the stale REJECTED status from the previous application
      const fresh = await apiClient.get('/users/me');
      updateUser(fresh.data);

      navigate('/seller/pending');
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to register as seller', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: 700 }}>
      <div className="mb-4">
        <h1 style={{ fontWeight: 800, fontSize: '1.75rem', margin: '0 0 0.25rem' }}>Become a Seller</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem', margin: 0 }}>
          Start listing items on KaraKaja and reach thousands of buyers.
        </p>
      </div>

      <div className="card" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="card-body p-4">
          <form onSubmit={handleSubmit(onSubmit)}>

            {/* Seller Type */}
            <div className="mb-4">
              <label className="form-label" style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>
                Seller Type
              </label>
              <div className="row g-3">
                {SELLER_TYPES.map((t) => (
                  <div className="col-md-4" key={t.value}>
                    <div
                      onClick={() => setSellerType(t.value)}
                      style={{
                        padding: '1rem', borderRadius: 'var(--radius-lg)', cursor: 'pointer',
                        border: `2px solid ${sellerType === t.value ? 'var(--primary)' : 'var(--border)'}`,
                        background: sellerType === t.value ? 'var(--primary-50)' : 'var(--card-bg)',
                        transition: 'var(--transition)', position: 'relative',
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
                <input
                  {...register('business_name', { required: 'Business name is required' })}
                  className={`form-control ${errors.business_name ? 'is-invalid' : ''}`}
                />
                {errors.business_name && <div className="invalid-feedback">{errors.business_name.message}</div>}
              </div>
            )}

            <div className="mb-4">
              <label className="form-label">Seller Bio</label>
              <textarea
                {...register('bio')}
                className="form-control"
                rows={3}
                placeholder="Tell buyers about yourself or your business…"
              />
            </div>

            {/* Verification Documents */}
            <div className="mb-4">
              <div className="d-flex align-items-center justify-content-between mb-1">
                <label className="form-label mb-0" style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>
                  <FiFileText size={15} style={{ marginRight: '0.35rem' }} />
                  Verification Documents
                </label>
                <button type="button" className="btn btn-outline-primary btn-sm" onClick={addDocSlot}>
                  <FiPlus size={13} /> Add Document
                </button>
              </div>

              {/* Helper note */}
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                Upload a PDF or image (JPEG, PNG) of your ID, business registration, or other supporting document.
                Max 10MB per file. Documents are reviewed by our team before your account is verified.
              </p>

              {docs.length === 0 && (
                <div style={{ padding: '1.5rem', background: 'var(--surface)', borderRadius: 'var(--radius)', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem', border: '1px dashed var(--border)' }}>
                  No documents added yet. Click &quot;Add Document&quot; to upload.
                </div>
              )}

              <div className="d-flex flex-column gap-2">
                {docs.map((doc) => (
                  <div key={doc.id} style={{ padding: '0.875rem', border: `1px solid ${doc.status === 'error' ? 'var(--danger)' : doc.status === 'done' ? 'var(--success)' : 'var(--border)'}`, borderRadius: 'var(--radius-lg)', background: doc.status === 'done' ? 'var(--success-light)' : 'var(--card-bg)' }}>
                    <div className="d-flex align-items-center gap-2 flex-wrap">
                      {/* Doc type selector */}
                      <select
                        className="form-select form-select-sm"
                        style={{ flex: '1 1 160px', maxWidth: 200 }}
                        value={doc.docType}
                        onChange={e => updateDocType(doc.id, e.target.value)}
                        disabled={doc.status === 'uploading' || doc.status === 'done'}
                      >
                        {DOC_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>

                      {/* File input — only show if not yet uploaded */}
                      {doc.status !== 'done' && (
                        <label style={{ flex: '2 1 200px', cursor: 'pointer' }}>
                          <div className="btn btn-outline-secondary btn-sm w-100" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}>
                            <FiUpload size={13} />
                            {doc.file ? doc.file.name : 'Choose file'}
                          </div>
                          <input
                            type="file"
                            accept=".pdf,.jpg,.jpeg,.png,.webp"
                            style={{ display: 'none' }}
                            disabled={doc.status === 'uploading'}
                            onChange={e => handleFileChange(doc.id, e.target.files[0])}
                          />
                        </label>
                      )}

                      {/* Uploaded — show link */}
                      {doc.status === 'done' && doc.result && (
                        <a
                          href={doc.result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ flex: '2 1 200px', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--success)' }}
                        >
                          <FiCheck size={14} /> Uploaded — {doc.result.title}
                          <FiExternalLink size={12} />
                        </a>
                      )}

                      {doc.status === 'error' && (
                        <span style={{ flex: '2 1 200px', fontSize: '0.8125rem', color: 'var(--danger)', fontWeight: 600 }}>
                          Upload failed — try again
                        </span>
                      )}

                      <button
                        type="button"
                        onClick={() => removeDoc(doc.id)}
                        disabled={doc.status === 'uploading'}
                        style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: '0.25rem', flexShrink: 0 }}
                      >
                        <FiX size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary w-100"
              disabled={submitting || docs.some(d => d.status === 'uploading')}
              style={{ padding: '0.625rem' }}
            >
              {submitting
                ? <><span className="spinner-sm" /> Submitting…</>
                : <>Submit for Verification <FiArrowRight size={16} /></>
              }
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
