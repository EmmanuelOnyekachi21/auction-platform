import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';
import { useAuthStore } from '../../store/authStore';
import {
  FiUser, FiBriefcase, FiFileText,
  FiPlus, FiX, FiArrowRight, FiCheck, FiUpload, FiExternalLink,
} from 'react-icons/fi';

// ── Seller type config ─────────────────────────────────────────────────────────
const SELLER_TYPES = [
  {
    value: 'INDIVIDUAL',
    label: 'Individual',
    desc: 'Selling personal items as a private individual',
    icon: <FiUser size={20} />,
    requiredDocs: ['NIN (National ID Number)', 'Passport Photo', 'Utility Bill'],
    optionalDocs: ["Driver's License", 'International Passport'],
    hint: 'You will need to provide a government-issued ID to verify your identity.',
  },
  {
    value: 'BUSINESS',
    label: 'Business',
    desc: 'Selling as a registered company or enterprise',
    icon: <FiBriefcase size={20} />,
    requiredDocs: ['CAC Certificate', 'Business Registration Document'],
    optionalDocs: ['Director ID', 'Utility Bill', 'Tax Clearance Certificate'],
    hint: 'You will need to provide your CAC registration documents to verify your business.',
  },
];

// ── Document upload helper ─────────────────────────────────────────────────────
async function uploadDocFile(file, docType) {
  const form = new FormData();
  form.append('file', file);
  form.append('doc_type', docType);
  const res = await apiClient.post('/users/me/seller-profile/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

// ── Document row component ─────────────────────────────────────────────────────
function DocRow({ doc, docOptions, onTypeChange, onFileChange, onRemove }) {
  return (
    <div style={{
      padding: '0.875rem',
      border: `1px solid ${doc.status === 'error' ? 'var(--danger)' : doc.status === 'done' ? 'var(--success)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-lg)',
      background: doc.status === 'done' ? 'var(--success-light)' : 'var(--card-bg)',
    }}>
      <div className="d-flex align-items-center gap-2 flex-wrap">
        <select
          className="form-select form-select-sm"
          style={{ flex: '1 1 180px', maxWidth: 220 }}
          value={doc.docType}
          onChange={e => onTypeChange(doc.id, e.target.value)}
          disabled={doc.status === 'done'}
        >
          {docOptions.map(t => <option key={t} value={t}>{t}</option>)}
        </select>

        {doc.status !== 'done' && (
          <label style={{ flex: '2 1 200px', cursor: 'pointer' }}>
            <div className="btn btn-outline-secondary btn-sm w-100" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}>
              <FiUpload size={13} />
              {doc.file ? doc.file.name : 'Choose file'}
            </div>
            <input type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" style={{ display: 'none' }}
              onChange={e => onFileChange(doc.id, e.target.files[0])} />
          </label>
        )}

        {doc.status === 'done' && doc.result && (
          <a href={doc.result.url} target="_blank" rel="noopener noreferrer"
            style={{ flex: '2 1 200px', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--success)' }}>
            <FiCheck size={14} /> {doc.result.title} <FiExternalLink size={12} />
          </a>
        )}

        {doc.status === 'error' && (
          <span style={{ flex: '2 1 200px', fontSize: '0.8125rem', color: 'var(--danger)', fontWeight: 600 }}>
            Upload failed — try again
          </span>
        )}

        <button type="button" onClick={() => onRemove(doc.id)}
          style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: '0.25rem', flexShrink: 0 }}>
          <FiX size={16} />
        </button>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function BecomeSellerPage() {
  const [sellerType, setSellerType] = useState('INDIVIDUAL');
  const [docs, setDocs] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const { register, handleSubmit, formState: { errors }, reset } = useForm();
  const { showToast } = useToast();
  const { updateUser } = useAuthStore();
  const navigate = useNavigate();

  const selectedConfig = SELLER_TYPES.find(t => t.value === sellerType);
  const allDocOptions = [...(selectedConfig?.requiredDocs || []), ...(selectedConfig?.optionalDocs || [])];

  // Reset docs when seller type changes — different types need different documents
  const handleTypeChange = (type) => {
    setSellerType(type);
    setDocs([]);
    reset({ bio: '', business_name: '' });
  };

  const addDocSlot = () =>
    setDocs(d => [...d, { id: Date.now(), docType: allDocOptions[0] || 'Document', file: null, status: 'pending', result: null }]);

  const removeDoc = (id) => setDocs(d => d.filter(doc => doc.id !== id));
  const updateDocType = (id, docType) => setDocs(d => d.map(doc => doc.id === id ? { ...doc, docType } : doc));
  const handleFileChange = (id, file) => {
    if (!file) return;
    setDocs(d => d.map(doc => doc.id === id ? { ...doc, file, status: 'pending' } : doc));
  };

  const onSubmit = async (data) => {
    setSubmitting(true);
    try {
      // Step 1 — create seller profile
      await apiClient.post('/users/me/seller-profile', {
        seller_type: sellerType,
        bio: data.bio || undefined,
        business_name: sellerType === 'BUSINESS' ? data.business_name : undefined,
      });

      // Step 2 — upload staged documents
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

      // Sync store with fresh profile data
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
                  <div className="col-6" key={t.value}>
                    <div
                      onClick={() => handleTypeChange(t.value)}
                      style={{
                        padding: '1.25rem', borderRadius: 'var(--radius-lg)', cursor: 'pointer',
                        border: `2px solid ${sellerType === t.value ? 'var(--primary)' : 'var(--border)'}`,
                        background: sellerType === t.value ? 'var(--primary-50)' : 'var(--card-bg)',
                        transition: 'var(--transition)', position: 'relative', height: '100%',
                      }}
                    >
                      {sellerType === t.value && (
                        <div style={{ position: 'absolute', top: 10, right: 10, width: 20, height: 20, borderRadius: 'var(--radius-full)', background: 'var(--primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <FiCheck size={12} />
                        </div>
                      )}
                      <div style={{ color: sellerType === t.value ? 'var(--primary)' : 'var(--text-muted)', marginBottom: '0.625rem' }}>{t.icon}</div>
                      <div style={{ fontWeight: 700, fontSize: '0.9375rem', marginBottom: '0.25rem' }}>{t.label}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>{t.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Type-specific hint */}
            {selectedConfig?.hint && (
              <div style={{ padding: '0.75rem 1rem', background: 'var(--primary-50)', borderRadius: 'var(--radius)', border: '1px solid var(--primary-light)', fontSize: '0.8125rem', color: 'var(--primary)', marginBottom: '1.25rem' }}>
                {selectedConfig.hint}
              </div>
            )}

            {/* Business name — only for BUSINESS */}
            {sellerType === 'BUSINESS' && (
              <div className="mb-3">
                <label className="form-label">Business / Company Name <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input
                  {...register('business_name', { required: 'Business name is required for business accounts' })}
                  className={`form-control ${errors.business_name ? 'is-invalid' : ''}`}
                  placeholder="e.g. Acme Trading Ltd"
                />
                {errors.business_name && <div className="invalid-feedback">{errors.business_name.message}</div>}
              </div>
            )}

            <div className="mb-4">
              <label className="form-label">Bio <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(optional)</span></label>
              <textarea
                {...register('bio')}
                className="form-control"
                rows={3}
                placeholder={sellerType === 'INDIVIDUAL'
                  ? 'Tell buyers a bit about yourself…'
                  : 'Describe your business and what you sell…'}
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

              {/* Required docs hint */}
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Required: </span>
                {selectedConfig?.requiredDocs.join(', ')}
                {selectedConfig?.optionalDocs.length > 0 && (
                  <> &nbsp;·&nbsp; <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Optional: </span>{selectedConfig.optionalDocs.join(', ')}</>
                )}
                <br />
                PDF or image (JPEG, PNG). Max 10MB per file.
              </div>

              {docs.length === 0 && (
                <div style={{ padding: '1.5rem', background: 'var(--surface)', borderRadius: 'var(--radius)', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem', border: '1px dashed var(--border)' }}>
                  No documents added yet. Click &quot;Add Document&quot; to upload.
                </div>
              )}

              <div className="d-flex flex-column gap-2">
                {docs.map(doc => (
                  <DocRow
                    key={doc.id}
                    doc={doc}
                    docOptions={allDocOptions}
                    onTypeChange={updateDocType}
                    onFileChange={handleFileChange}
                    onRemove={removeDoc}
                  />
                ))}
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary w-100"
              disabled={submitting}
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
