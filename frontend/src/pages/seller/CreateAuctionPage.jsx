/**
 * CreateAuctionPage.jsx — 4-step multi-step auction creation wizard
 *
 * Step 1: Item Details   (react-hook-form + zod)
 * Step 2: Upload Images
 * Step 3: Auction Settings
 * Step 4: Review & Publish
 *
 * Session persistence: wizard state is saved to sessionStorage on every
 * change so a page refresh restores progress. Cleared on publish or
 * explicit abandon.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQuery } from '@tanstack/react-query';
import {
    FiUpload, FiStar, FiTrash2, FiChevronRight, FiChevronLeft,
    FiAlertCircle, FiCheckCircle, FiInfo, FiRefreshCw,
} from 'react-icons/fi';

import apiClient from '../../api/client';
import { getAuction, getCategories } from '../../api/auctions';
import { useAuthStore } from '../../store/authStore';
import { useToast } from '../../components/common/Toast';
import './CreateAuctionPage.css';

/* ══════════════════════════════════════════════════════════════════════════════
   SESSION PERSISTENCE
══════════════════════════════════════════════════════════════════════════════ */

const SESSION_KEY = 'cap_wizard_state';

const saveSession = (step, state) => {
    try {
        sessionStorage.setItem(SESSION_KEY, JSON.stringify({ step, state }));
    } catch { /* quota exceeded — silently ignore */ }
};

const loadSession = () => {
    try {
        const raw = sessionStorage.getItem(SESSION_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
};

const clearSession = () => {
    try { sessionStorage.removeItem(SESSION_KEY); } catch { /* ignore */ }
};

/* ══════════════════════════════════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════════════════════════════════ */

const formatNaira = (v) =>
    `₦${Number(v || 0).toLocaleString('en-NG', { minimumFractionDigits: 0 })}`;

/** Add hours to a Date and return ISO string for datetime-local input */
const isoLocal = (date) => {
    const pad = (n) => String(n).padStart(2, '0');
    return (
        `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
        `T${pad(date.getHours())}:${pad(date.getMinutes())}`
    );
};

const plusMinutes = (date, m) => new Date(date.getTime() + m * 60_000);

const CONDITIONS = [
    { value: 'NEW',      label: 'New',      desc: 'Brand new, unused, in original packaging' },
    { value: 'LIKE_NEW', label: 'Like New',  desc: 'Used very briefly, no visible wear' },
    { value: 'GOOD',     label: 'Good',      desc: 'Works perfectly, minor cosmetic signs of use' },
    { value: 'FAIR',     label: 'Fair',      desc: 'Fully functional, moderate wear visible' },
    { value: 'POOR',     label: 'Poor',      desc: 'Heavily used; functional but noticeably worn' },
];

const DURATION_PILLS = [
    { label: '5 min',  minutes: 5  },
    { label: '10 min', minutes: 10 },
    { label: '15 min', minutes: 15 },
    { label: '20 min', minutes: 20 },
    { label: '30 min', minutes: 30 },
    { label: '1 hr',   minutes: 60 },
];

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_IMAGES     = 8;
const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

/* ══════════════════════════════════════════════════════════════════════════════
   ZOD SCHEMAS
══════════════════════════════════════════════════════════════════════════════ */

const itemSchema = z.object({
    name:        z.string().min(3, 'Item name must be at least 3 characters'),
    category_id: z.string().min(1, 'Please select a category'),
    condition:   z.string().min(1, 'Please select a condition'),
    description: z.string().min(20, 'Description must be at least 20 characters'),
    weight:      z.string().optional(),
    dimensions:  z.string().optional(),
});

const baseAuctionSchema = z.object({
    start_at:       z.string().min(1, 'Start date is required'),
    end_at:         z.string().min(1, 'End date is required'),
    starting_price: z.coerce.number().min(1, 'Starting price must be at least ₦1'),
    reserve_price:  z.coerce.number().optional(),
});

const auctionSchema = baseAuctionSchema.refine((d) => new Date(d.end_at) > new Date(d.start_at), {
    message: 'End date must be after start date',
    path: ['end_at'],
});

/* ══════════════════════════════════════════════════════════════════════════════
   STEP INDICATOR
══════════════════════════════════════════════════════════════════════════════ */

const STEPS = [
    { n: 1, label: 'Item Details' },
    { n: 2, label: 'Photos' },
    { n: 3, label: 'Auction Settings' },
    { n: 4, label: 'Review' },
];

function StepIndicator({ current }) {
    return (
        <div className="cap__steps">
            {STEPS.map((step, i) => {
                const done    = step.n < current;
                const active  = step.n === current;
                return (
                    <div key={step.n} className="cap__step-item">
                        <div className={`cap__step-circle ${done ? 'cap__step-circle--done' : active ? 'cap__step-circle--active' : ''}`}>
                            {done ? <FiCheckCircle size={15} /> : step.n}
                        </div>
                        <span className={`cap__step-label ${active ? 'cap__step-label--active' : ''}`}>
                            {step.label}
                        </span>
                        {i < STEPS.length - 1 && (
                            <div className={`cap__step-line ${done ? 'cap__step-line--done' : ''}`} />
                        )}
                    </div>
                );
            })}
        </div>
    );
}

/* ══════════════════════════════════════════════════════════════════════════════
   STEP 1 — ITEM DETAILS
══════════════════════════════════════════════════════════════════════════════ */

function Step1ItemDetails({ onNext, prefill, onDraftChange, existingItemId }) {
    const { data: categoriesData } = useQuery({
        queryKey: ['categories'],
        queryFn: getCategories,
        staleTime: 5 * 60 * 1000,
    });
    const categories = Array.isArray(categoriesData) ? categoriesData : (categoriesData?.items ?? []);
    const [submitting, setSubmitting] = useState(false);
    const { showToast } = useToast();

    const {
        register,
        handleSubmit,
        watch,
        formState: { errors },
    } = useForm({
        resolver: zodResolver(itemSchema),
        defaultValues: prefill ? {
            name:        prefill.title ?? '',
            category_id: prefill.category_id ?? '',
            condition:   prefill.condition ?? '',
            description: prefill.description ?? '',
            weight:      prefill.weight_kg ? String(prefill.weight_kg) : '',
            dimensions:  prefill.dimensions ?? '',
        } : {},
    });

    const description = watch('description', '');

    // Continuously save draft values to session so a refresh restores them
    const allValues = watch();
    useEffect(() => {
        onDraftChange?.(allValues);
    }, [JSON.stringify(allValues)]); // eslint-disable-line react-hooks/exhaustive-deps

    const onSubmit = async (data) => {
        setSubmitting(true);
        try {
            // If item was already created (user went back), skip re-creating it
            if (existingItemId) {
                onNext({ itemId: existingItemId, itemData: data });
                return;
            }
            const payload = {
                title:       data.name,
                category_id: data.category_id,
                condition:   data.condition,
                description: data.description,
                ...(data.weight     ? { weight_kg:   parseFloat(data.weight) } : {}),
                ...(data.dimensions ? { dimensions:  data.dimensions }         : {}),
            };
            const res = await apiClient.post('/items', payload);
            onNext({ itemId: res.data?.id ?? res.data?.item_id, itemData: data });
        } catch (err) {
            showToast(err?.response?.data?.detail ?? 'Failed to save item. Please try again.', 'error');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="cap__form" noValidate>

            {/* Item name */}
            <div className="cap__field">
                <label className="form-label" htmlFor="item-name">Item Name *</label>
                <input
                    id="item-name"
                    className={`form-control ${errors.name ? 'is-invalid' : ''}`}
                    placeholder="e.g. Sony WH-1000XM5 Headphones"
                    {...register('name')}
                />
                {errors.name && <div className="invalid-feedback">{errors.name.message}</div>}
            </div>

            {/* Category */}
            <div className="cap__field">
                <label className="form-label" htmlFor="item-category">Category *</label>
                <select
                    id="item-category"
                    className={`form-select ${errors.category_id ? 'is-invalid' : ''}`}
                    {...register('category_id')}
                >
                    <option value="">Select a category…</option>
                    {categories.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                </select>
                {errors.category_id && <div className="invalid-feedback">{errors.category_id.message}</div>}
            </div>

            {/* Condition */}
            <div className="cap__field">
                <label className="form-label">Condition *</label>
                {errors.condition && <div className="cap__field-error">{errors.condition.message}</div>}
                <div className="cap__condition-grid">
                    {CONDITIONS.map((c) => (
                        <label key={c.value} className="cap__condition-card">
                            <input type="radio" value={c.value} {...register('condition')} style={{ display: 'none' }} />
                            <div className="cap__condition-inner">
                                <span className="cap__condition-label">{c.label}</span>
                                <span className="cap__condition-desc">{c.desc}</span>
                            </div>
                        </label>
                    ))}
                </div>
            </div>

            {/* Description */}
            <div className="cap__field">
                <label className="form-label" htmlFor="item-description">
                    Description *
                    <span className="cap__char-count">{description.length} chars</span>
                </label>
                <textarea
                    id="item-description"
                    rows={5}
                    className={`form-control ${errors.description ? 'is-invalid' : ''}`}
                    placeholder="Describe the item in detail — model, features, any defects…"
                    {...register('description')}
                />
                {errors.description && <div className="invalid-feedback">{errors.description.message}</div>}
            </div>

            {/* Weight + Dimensions side-by-side */}
            <div className="row g-3">
                <div className="col-sm-6 cap__field">
                    <label className="form-label" htmlFor="item-weight">Weight (kg) <span className="cap__optional">optional</span></label>
                    <input
                        id="item-weight"
                        type="number"
                        step="0.01"
                        className="form-control"
                        placeholder="e.g. 0.5"
                        {...register('weight')}
                    />
                </div>
                <div className="col-sm-6 cap__field">
                    <label className="form-label" htmlFor="item-dimensions">Dimensions <span className="cap__optional">optional</span></label>
                    <input
                        id="item-dimensions"
                        className="form-control"
                        placeholder="30cm × 20cm × 10cm"
                        {...register('dimensions')}
                    />
                </div>
            </div>

            <div className="cap__nav">
                <span />
                <button type="submit" className="btn btn-primary cap__next-btn" disabled={submitting}>
                    {submitting
                        ? <><span className="spinner-sm" /> Saving…</>
                        : <>Next: Photos <FiChevronRight size={16} /></>
                    }
                </button>
            </div>
        </form>
    );
}

/* ══════════════════════════════════════════════════════════════════════════════
   STEP 2 — UPLOAD IMAGES
══════════════════════════════════════════════════════════════════════════════ */

function Step2Images({ itemId, onNext, onBack, savedImages = [] }) {
    const { showToast } = useToast();
    // Seed with already-uploaded images from a restored session.
    // These have a `url` from the server — no file object needed.
    const [images, setImages] = useState(() =>
        savedImages.map((img) => ({
            file:      null,
            preview:   img.preview ?? img.url ?? img.image_url,
            url:       img.url ?? img.image_url,
            id:        img.id,
            relistUrl: img.relistUrl ?? null,
            progress:  img.uploaded ? 100 : 0,
            error:     null,
            uploaded:  img.uploaded ?? false,
        }))
    );
    const [primaryIdx, setPrimary]  = useState(0);
    const [dragging, setDragging]   = useState(false);
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef(null);

    const addFiles = useCallback((files) => {
        const valid = [];
        for (const f of files) {
            if (!ACCEPTED_TYPES.includes(f.type)) {
                showToast(`${f.name}: only JPG, PNG, WebP allowed`, 'error'); continue;
            }
            if (f.size > MAX_SIZE_BYTES) {
                showToast(`${f.name}: exceeds 5 MB limit`, 'error'); continue;
            }
            valid.push(f);
        }
        const remaining = MAX_IMAGES - images.length;
        if (valid.length > remaining) {
            showToast(`Maximum ${MAX_IMAGES} images allowed. ${remaining} slot(s) remaining.`, 'error');
        }
        const toAdd = valid.slice(0, remaining).map((f) => ({
            file:     f,
            preview:  URL.createObjectURL(f),
            progress: 0,
            error:    null,
        }));
        setImages((prev) => [...prev, ...toAdd]);
    }, [images.length, showToast]);

    const handleDrop = (e) => {
        e.preventDefault();
        setDragging(false);
        addFiles(Array.from(e.dataTransfer.files));
    };

    const removeImage = (idx) => {
        setImages((prev) => {
            const next = prev.filter((_, i) => i !== idx);
            if (primaryIdx >= next.length) setPrimary(Math.max(0, next.length - 1));
            return next;
        });
    };

    const handleNext = async () => {
        if (images.length === 0) {
            if (!window.confirm('No images added. Continue without images?')) return;
            onNext({ uploadedImages: [] });
            return;
        }
        setUploading(true);
        const uploaded = [];
        for (let i = 0; i < images.length; i++) {
            // Already uploaded in a previous session (same item) — keep as-is
            if (images[i].uploaded) {
                uploaded.push({ url: images[i].url, id: images[i].id });
                continue;
            }
            try {
                setImages((prev) => prev.map((img, j) => j === i ? { ...img, progress: 50 } : img));
                const formData = new FormData();

                if (images[i].relistUrl) {
                    // Relist: fetch the original image from Cloudinary and re-upload to new item
                    const blob = await fetch(images[i].relistUrl).then((r) => r.blob());
                    const ext  = images[i].relistUrl.split('.').pop().split('?')[0] || 'jpg';
                    formData.append('file', blob, `image_${i}.${ext}`);
                } else {
                    formData.append('file', images[i].file);
                }

                if (i === primaryIdx) formData.append('is_primary', 'true');
                const res = await apiClient.post(`/items/${itemId}/images`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
                uploaded.push(res.data);
                setImages((prev) => prev.map((img, j) => j === i ? { ...img, progress: 100 } : img));
            } catch {
                setImages((prev) => prev.map((img, j) => j === i ? { ...img, error: 'Upload failed', progress: 0 } : img));
                showToast(`Failed to upload image ${i + 1}`, 'error');
            }
        }
        setUploading(false);
        onNext({ uploadedImages: uploaded });
    };

    return (
        <div className="cap__form">

            {images.length === 0 ? (
                /* Drop zone */
                <div
                    className={`cap__dropzone ${dragging ? 'cap__dropzone--active' : ''}`}
                    onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    role="button"
                    tabIndex={0}
                    aria-label="Upload images"
                >
                    <FiUpload size={36} style={{ color: 'var(--primary)', marginBottom: '0.75rem' }} />
                    <div className="cap__dropzone-title">Drag & drop images here</div>
                    <div className="cap__dropzone-sub">or click to browse · JPG, PNG, WebP · max 5 MB each · up to {MAX_IMAGES}</div>
                </div>
            ) : (
                /* Preview grid */
                <div>
                    <div className="cap__image-grid">
                        {images.map((img, i) => (
                            <div
                                key={img.preview}
                                className={`cap__img-thumb ${i === primaryIdx ? 'cap__img-thumb--primary' : ''}`}
                                onClick={() => setPrimary(i)}
                                title={i === primaryIdx ? 'Primary image' : 'Click to set as primary'}
                            >
                                <img src={img.preview} alt={`Upload ${i + 1}`} />
                                {i === primaryIdx && (
                                    <div className="cap__img-primary-badge">
                                        <FiStar size={11} /> Primary
                                    </div>
                                )}
                                {img.progress > 0 && img.progress < 100 && (
                                    <div className="cap__img-progress">
                                        <div className="cap__img-progress-bar" style={{ width: `${img.progress}%` }} />
                                    </div>
                                )}
                                {img.error && (
                                    <div className="cap__img-error"><FiAlertCircle size={14} /></div>
                                )}
                                <button
                                    className="cap__img-remove"
                                    onClick={(e) => { e.stopPropagation(); removeImage(i); }}
                                    aria-label="Remove image"
                                >
                                    <FiTrash2 size={13} />
                                </button>
                            </div>
                        ))}

                        {/* Add more slot */}
                        {images.length < MAX_IMAGES && (
                            <div
                                className="cap__img-add"
                                onClick={() => fileInputRef.current?.click()}
                                title="Add more images"
                            >
                                <FiUpload size={22} />
                                <span>Add</span>
                            </div>
                        )}
                    </div>

                    <p className="cap__img-hint">
                        <FiInfo size={12} /> Click an image to set it as primary. First image is primary by default.
                    </p>
                </div>
            )}

            <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_TYPES.join(',')}
                multiple
                style={{ display: 'none' }}
                onChange={(e) => addFiles(Array.from(e.target.files))}
            />

            {images.length === 0 && (
                <div className="cap__warn">
                    <FiAlertCircle size={15} /> You can continue without images, but listings with photos get more bids.
                </div>
            )}

            <div className="cap__nav">
                <button type="button" className="btn btn-outline-primary" onClick={onBack}>
                    <FiChevronLeft size={15} /> Back
                </button>
                <button
                    type="button"
                    className="btn btn-primary cap__next-btn"
                    onClick={handleNext}
                    disabled={uploading}
                >
                    {uploading
                        ? <><span className="spinner-sm" /> Uploading…</>
                        : <>Next: Auction Settings <FiChevronRight size={16} /></>
                    }
                </button>
            </div>
        </div>
    );
}

/* ══════════════════════════════════════════════════════════════════════════════
   STEP 3 — AUCTION SETTINGS
══════════════════════════════════════════════════════════════════════════════ */

function Step3Settings({ itemId, onNext, onBack, prefill, existingAuctionId }) {
    const { showToast } = useToast();
    const [submitting, setSubmitting]     = useState(false);
    const [reserveOn, setReserveOn]       = useState(false);
    const [activeDuration, setActiveDur]  = useState(null); // hours

    const now      = new Date();
    const defaultStart = isoLocal(new Date(now.getTime() + 5 * 60_000)); // 5 mins ahead
    const defaultEnd   = isoLocal(new Date(now.getTime() + 10 * 60_000)); // 10 mins from now

    const {
        register,
        handleSubmit,
        watch,
        setValue,
        formState: { errors },
    } = useForm({
        resolver: zodResolver(
            reserveOn
                ? baseAuctionSchema
                      .extend({ reserve_price: z.coerce.number().min(1, 'Reserve price must be ≥ ₦1') })
                      .refine((d) => new Date(d.end_at) > new Date(d.start_at), {
                          message: 'End date must be after start date',
                          path: ['end_at'],
                      })
                : auctionSchema
        ),
        defaultValues: {
            start_at:       defaultStart,
            end_at:         defaultEnd,
            starting_price: prefill?.starting_price ? String(prefill.starting_price) : '',
            reserve_price:  '',
        },
    });

    const startAt = watch('start_at');

    const applyDuration = (minutes) => {
        const start = new Date(startAt || now);
        setValue('end_at', isoLocal(plusMinutes(start, minutes)));
        setActiveDur(minutes);
    };

    const onSubmit = async (data) => {
        setSubmitting(true);
        try {
            // If auction was already created (user went back), skip re-creating it
            if (existingAuctionId) {
                onNext({ auctionId: existingAuctionId, settingsData: data, reserveOn });
                return;
            }
            // 1. Create auction
            const auctionPayload = {
                starts_at: new Date(data.start_at).toISOString(),
                ends_at:   new Date(data.end_at).toISOString(),
                ...(reserveOn && data.reserve_price ? { reserve_price: data.reserve_price } : {}),
            };
            const auctionRes = await apiClient.post('/auctions', auctionPayload);
            const auctionId  = auctionRes.data?.id ?? auctionRes.data?.auction_id;

            // 2. Attach item to auction
            await apiClient.post(`/auctions/${auctionId}/items`, {
                item_id:        itemId,
                starting_price: data.starting_price,
                quantity:       1,
            });

            onNext({ auctionId, settingsData: data, reserveOn });
        } catch (err) {
            showToast(err?.response?.data?.detail ?? 'Failed to create auction. Please try again.', 'error');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="cap__form" noValidate>

            {/* Dates row */}
            <div className="row g-3">
                <div className="col-sm-6 cap__field">
                    <label className="form-label" htmlFor="auction-start">Start Date & Time *</label>
                    <input
                        id="auction-start"
                        type="datetime-local"
                        className={`form-control ${errors.start_at ? 'is-invalid' : ''}`}
                        {...register('start_at')}
                    />
                    {errors.start_at && <div className="invalid-feedback">{errors.start_at.message}</div>}
                </div>
                <div className="col-sm-6 cap__field">
                    <label className="form-label" htmlFor="auction-end">End Date & Time *</label>
                    <input
                        id="auction-end"
                        type="datetime-local"
                        className={`form-control ${errors.end_at ? 'is-invalid' : ''}`}
                        readOnly
                        style={{ backgroundColor: 'var(--bg-secondary)', cursor: 'not-allowed' }}
                        {...register('end_at')}
                    />
                    <p className="cap__hint" style={{ marginTop: '0.25rem' }}>
                        <FiInfo size={12} /> Calculated from start time + duration selected below
                    </p>
                    {errors.end_at && <div className="invalid-feedback">{errors.end_at.message}</div>}
                </div>
            </div>

            {/* Duration quick-picks */}
            <div className="cap__field">
                <label className="form-label">Quick Duration</label>
                <div className="cap__duration-pills">
                    {DURATION_PILLS.map(({ label, minutes }) => (
                        <button
                            key={minutes}
                            type="button"
                            className={`cap__duration-pill ${activeDuration === minutes ? 'cap__duration-pill--active' : ''}`}
                            onClick={() => applyDuration(minutes)}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Prices row */}
            <div className="cap__field">
                <label className="form-label" htmlFor="starting-price">Starting Price (₦) *</label>
                <div className="cap__price-wrapper">
                    <span className="cap__price-prefix">₦</span>
                    <input
                        id="starting-price"
                        type="number"
                        min="1"
                        step="1"
                        className={`form-control cap__price-input ${errors.starting_price ? 'is-invalid' : ''}`}
                        placeholder="e.g. 5000"
                        {...register('starting_price')}
                    />
                </div>
                {errors.starting_price && <div className="cap__field-error">{errors.starting_price.message}</div>}
            </div>

            {/* Reserve price toggle */}
            <div className="cap__field">
                <div className="cap__toggle-row">
                    <div>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>Reserve Price</div>
                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Set a reserve price — your item only sells if bidding reaches this amount</div>
                    </div>
                    <button
                        type="button"
                        id="reserve-toggle"
                        className={`cap__toggle ${reserveOn ? 'cap__toggle--on' : ''}`}
                        onClick={() => setReserveOn((p) => !p)}
                        aria-pressed={reserveOn}
                    >
                        <span className="cap__toggle-knob" />
                    </button>
                </div>

                {!reserveOn && (
                    <p className="cap__hint" style={{ marginTop: '0.5rem' }}>
                        <FiInfo size={12} /> Item sells to highest bidder regardless of final price.
                    </p>
                )}

                {reserveOn && (
                    <div style={{ marginTop: '0.875rem' }}>
                        <div className="cap__price-wrapper">
                            <span className="cap__price-prefix">₦</span>
                            <input
                                id="reserve-price"
                                type="number"
                                min="1"
                                step="1"
                                className={`form-control cap__price-input ${errors.reserve_price ? 'is-invalid' : ''}`}
                                placeholder="e.g. 50000"
                                {...register('reserve_price')}
                            />
                        </div>
                        {errors.reserve_price && <div className="cap__field-error">{errors.reserve_price.message}</div>}
                        <p className="cap__hint">
                            <FiInfo size={12} /> Your item will only sell if bidding reaches this amount. Buyers will see &quot;Reserve Not Met" until this threshold is crossed.
                        </p>
                        <p className="cap__hint" style={{ color: 'var(--warning)', fontWeight: 600 }}>
                            <FiAlertCircle size={12} /> Reserve price must be higher than your starting price.
                        </p>
                    </div>
                )}
            </div>

            <div className="cap__nav">
                <button type="button" className="btn btn-outline-primary" onClick={onBack}>
                    <FiChevronLeft size={15} /> Back
                </button>
                <button type="submit" className="btn btn-primary cap__next-btn" disabled={submitting}>
                    {submitting
                        ? <><span className="spinner-sm" /> Creating…</>
                        : <>Next: Review <FiChevronRight size={16} /></>
                    }
                </button>
            </div>
        </form>
    );
}

/* ══════════════════════════════════════════════════════════════════════════════
   STEP 4 — REVIEW & PUBLISH
══════════════════════════════════════════════════════════════════════════════ */

function Step4Review({ auctionId, itemData, settingsData, uploadedImages, reserveOn, onBack, onPublished }) {
    const navigate = useNavigate();
    const { showToast } = useToast();
    const [publishing, setPublishing] = useState(false);

    const handlePublish = async () => {
        setPublishing(true);
        try {
            const res = await apiClient.patch(`/auctions/${auctionId}/publish`);
            const returnedStatus = res.data?.status ?? res.data?.data?.status ?? 'ACTIVE';
            const msg = returnedStatus === 'SCHEDULED'
                ? 'Auction scheduled! It will go live at the start time you set.'
                : 'Auction is now live!';
            onPublished?.(); // clear sessionStorage
            showToast(msg, 'success');
            navigate(`/auctions/${auctionId}`);
        } catch (err) {
            showToast(err?.response?.data?.detail ?? 'Failed to publish auction.', 'error');
            setPublishing(false);
        }
    };

    const condLabel = CONDITIONS.find((c) => c.value === itemData?.condition)?.label ?? itemData?.condition;

    const duration = (() => {
        if (!settingsData?.start_at || !settingsData?.end_at) return '—';
        const ms    = new Date(settingsData.end_at) - new Date(settingsData.start_at);
        const hours = Math.round(ms / 3_600_000);
        return `${hours} hour${hours !== 1 ? 's' : ''}`;
    })();

    const summaryRows = [
        { label: 'Item Name',       value: itemData?.name },
        { label: 'Condition',       value: condLabel },
        { label: 'Description',     value: <span style={{ fontStyle: 'italic', fontSize: '0.8125rem' }}>{(itemData?.description ?? '').slice(0, 120)}{itemData?.description?.length > 120 ? '…' : ''}</span> },
        { label: 'Starting Price',  value: formatNaira(settingsData?.starting_price) },
        { label: 'Reserve Price',   value: reserveOn ? 'Set (confidential)' : 'None — sells to highest bidder' },
        { label: 'Starts',          value: settingsData?.start_at ? new Date(settingsData.start_at).toLocaleString('en-NG') : '—' },
        { label: 'Ends',            value: settingsData?.end_at   ? new Date(settingsData.end_at).toLocaleString('en-NG')   : '—' },
        { label: 'Duration',        value: duration },
        { label: 'Images',          value: `${uploadedImages?.length ?? 0} uploaded` },
    ];

    return (
        <div className="cap__form">

            {/* Image thumbnails */}
            {uploadedImages?.length > 0 && (
                <div className="cap__review-images">
                    {uploadedImages.slice(0, 5).map((img, i) => (
                        <img
                            key={i}
                            src={img.url ?? img.image_url}
                            alt={`Preview ${i + 1}`}
                            className="cap__review-thumb"
                        />
                    ))}
                    {uploadedImages.length > 5 && (
                        <div className="cap__review-thumb cap__review-thumb--more">
                            +{uploadedImages.length - 5}
                        </div>
                    )}
                </div>
            )}

            {/* Summary table */}
            <div className="cap__review-card">
                {summaryRows.map(({ label, value }, i) => (
                    <div key={label} className={`cap__review-row ${i < summaryRows.length - 1 ? 'cap__review-row--border' : ''}`}>
                        <span className="cap__review-label">{label}</span>
                        <span className="cap__review-value">{value}</span>
                    </div>
                ))}
            </div>

            {/* Commission notice */}
            <div className="cap__commission">
                <FiInfo size={14} />
                <span><strong>Platform fee:</strong> 5% on successful sale. No charge if the item doesn't sell.</span>
            </div>

            <div className="cap__nav">
                <button type="button" className="btn btn-outline-primary" onClick={onBack}>
                    <FiChevronLeft size={15} /> Edit Details
                </button>
                <button
                    id="publish-auction-btn"
                    type="button"
                    className="btn btn-primary cap__next-btn"
                    onClick={handlePublish}
                    disabled={publishing}
                >
                    {publishing
                        ? <><span className="spinner-sm" /> Publishing…</>
                        : <>Publish Auction <FiCheckCircle size={15} /></>
                    }
                </button>
            </div>
        </div>
    );
}

/* ══════════════════════════════════════════════════════════════════════════════
   MAIN PAGE
══════════════════════════════════════════════════════════════════════════════ */

export default function CreateAuctionPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const relistId = searchParams.get('relist');
    const { user, isAuthenticated } = useAuthStore();

    /* Gate: must be authenticated and a verified seller (admins bypass) */
    useEffect(() => {
        if (!isAuthenticated) { navigate('/login', { replace: true }); return; }
        const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPERUSER';
        if (isAdmin) return;
        const profile = user?.seller_profile;
        if (!profile)             { navigate('/become-seller', { replace: true }); return; }
        if (!profile.is_verified) { navigate('/seller/pending', { replace: true }); return; }
    }, [isAuthenticated, user, navigate]);

    /* Fetch original auction data when relisting */
    const { data: relistAuction, isLoading: relistLoading } = useQuery({
        queryKey: ['auction', relistId],
        queryFn: () => getAuction(relistId),
        enabled: !!relistId,
        staleTime: Infinity,
    });

    /* ── Rehydrate from sessionStorage on first mount (skip when relisting) ── */
    const saved = !relistId ? loadSession() : null;

    const [step, setStep] = useState(saved?.step ?? 1);
    const [state, setState] = useState(saved?.state ?? {
        itemId:         null,
        itemData:       null,
        uploadedImages: [],
        auctionId:      null,
        settingsData:   null,
        reserveOn:      false,
    });

    /* Persist to sessionStorage whenever step or state changes */
    useEffect(() => {
        // Don't persist relist flows — they have their own source of truth
        if (relistId) return;
        saveSession(step, state);
    }, [step, state, relistId]);

    const merge = (patch) => setState((prev) => ({ ...prev, ...patch }));

    /* Build prefill objects from the fetched auction (relist) or restored session */
    const relistItem = relistAuction?.items?.[0];

    // Relist: pre-fill item details from the original auction
    const relistItemPrefill = relistItem ? {
        title:       relistAuction.title ?? relistItem.item?.title ?? '',
        category_id: relistItem.item?.category?.id ?? '',
        condition:   relistItem.item?.condition ?? '',
        description: relistItem.item?.description ?? '',
        weight_kg:   relistItem.item?.weight_kg ?? '',
        dimensions:  relistItem.item?.dimensions ?? '',
    } : null;

    // Relist: pre-fill images from the original auction item.
    // Mark as `relistUrl` so Step 2 fetches and re-uploads them to the new item.
    const relistImages = relistItem?.item?.images?.length
        ? relistItem.item.images.map((img) => ({
            url:       img.url,
            id:        img.id,
            preview:   img.url,
            relistUrl: img.url,   // signals Step 2 to re-upload via fetch
            uploaded:  false,
        }))
        : [];

    const relistSettingsPrefill = relistItem ? {
        starting_price: relistItem.starting_price,
    } : null;

    // Resume: pre-fill Step 1 from saved session itemData
    const resumeItemPrefill = (!relistId && saved?.state?.itemData) ? {
        title:       saved.state.itemData.name ?? '',
        category_id: saved.state.itemData.category_id ?? '',
        condition:   saved.state.itemData.condition ?? '',
        description: saved.state.itemData.description ?? '',
        weight_kg:   saved.state.itemData.weight ?? '',
        dimensions:  saved.state.itemData.dimensions ?? '',
    } : null;

    // Final prefill values — relist takes priority over resume
    const itemPrefill      = relistItemPrefill ?? resumeItemPrefill;
    const settingsPrefill  = relistSettingsPrefill;

    const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPERUSER';
    if (!isAuthenticated || (!isAdmin && !user?.seller_profile?.is_verified)) return null;
    if (relistId && relistLoading) {
        return (
            <div className="cap page-container" style={{ maxWidth: 720, textAlign: 'center', paddingTop: '4rem' }}>
                <span className="spinner-sm" style={{ width: 32, height: 32 }} /> Loading auction details…
            </div>
        );
    }

    /* Show a resume banner when we restored a previous session */
    const isResuming = !relistId && !!saved && (saved.step > 1 || saved.state?.itemId || saved.state?.itemData);

    return (
        <div className="cap page-container" style={{ maxWidth: 720 }}>
            <div style={{ marginBottom: '0.5rem' }}>
                <h1 className="cap__page-title">
                    {relistId ? 'Relist Item' : 'Create New Auction'}
                </h1>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', margin: 0 }}>
                    {relistId
                        ? 'Details from your previous auction are pre-filled. Update anything you want before publishing.'
                        : 'Fill in the details below to list your item for auction.'}
                </p>
            </div>

            {relistId && (
                <div className="cap__warn" style={{ background: 'var(--primary-50)', borderColor: 'var(--primary-light)', color: 'var(--primary)', marginBottom: '1rem' }}>
                    <FiRefreshCw size={14} /> Relisting a previous auction — all fields are pre-filled from the original. A new item and auction will be created.
                </div>
            )}

            {isResuming && (
                <div className="cap__warn" style={{ background: 'var(--warning-50, #fffbeb)', borderColor: 'var(--warning, #f59e0b)', color: 'var(--warning-dark, #92400e)', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span><FiInfo size={14} /> Resuming where you left off — your progress was saved.</span>
                    <button
                        className="btn btn-sm"
                        style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', marginLeft: '1rem', whiteSpace: 'nowrap' }}
                        onClick={() => {
                            clearSession();
                            setStep(1);
                            setState({ itemId: null, itemData: null, uploadedImages: [], auctionId: null, settingsData: null, reserveOn: false });
                        }}
                    >
                        Start fresh
                    </button>
                </div>
            )}

            <StepIndicator current={step} />

            <div className="cap__card">
                <div className="cap__card-header">
                    Step {step} — {STEPS[step - 1].label}
                </div>
                <div className="cap__card-body">
                    {step === 1 && (
                        <Step1ItemDetails
                            prefill={itemPrefill}
                            existingItemId={state.itemId}
                            onDraftChange={(draft) => {
                                if (!relistId) {
                                    try {
                                        const current = loadSession() ?? { step: 1, state: {} };
                                        current.state.itemData = draft;
                                        sessionStorage.setItem(SESSION_KEY, JSON.stringify(current));
                                    } catch { /* ignore */ }
                                }
                            }}
                            onNext={(data) => { merge(data); setStep(2); }}
                        />
                    )}
                    {step === 2 && (
                        <Step2Images
                            itemId={state.itemId}
                            savedImages={relistId ? relistImages : state.uploadedImages}
                            onNext={(data) => { merge(data); setStep(3); }}
                            onBack={() => setStep(1)}
                        />
                    )}
                    {step === 3 && (
                        <Step3Settings
                            itemId={state.itemId}
                            existingAuctionId={state.auctionId}
                            prefill={settingsPrefill}
                            onNext={(data) => { merge(data); setStep(4); }}
                            onBack={() => setStep(2)}
                        />
                    )}
                    {step === 4 && (
                        <Step4Review
                            auctionId={state.auctionId}
                            itemData={state.itemData}
                            settingsData={state.settingsData}
                            uploadedImages={state.uploadedImages}
                            reserveOn={state.reserveOn}
                            onBack={() => setStep(1)}
                            onPublished={clearSession}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}
