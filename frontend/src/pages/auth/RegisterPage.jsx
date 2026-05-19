import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useNavigate, Link } from 'react-router-dom';
import { useState } from 'react';
import { authActions } from '../../api/auth';
import { FiUser, FiMail, FiPhone, FiLock, FiArrowRight } from 'react-icons/fi';

const registerSchema = z
    .object({
        first_name: z.string().min(2, 'First name is too short'),
        last_name: z.string().min(2, 'Last name is too short'),
        email: z.email('Invalid email address'),
        phone_number: z.string().regex(/^(?:\+234|0)[789]\d{9}$/, 'Invalid Nigerian phone number'),
        password: z.string().min(8, 'Password must be at least 8 characters'),
        confirm_password: z.string()
    })
    .refine((data) => data.password === data.confirm_password, {
        error: "Passwords don't match",
        path: ['confirm_password']
    });

export default function RegisterPage() {
    const navigate = useNavigate();
    const [apiError, setApiError] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const { register, handleSubmit, watch, formState: { errors } } = useForm({
        resolver: zodResolver(registerSchema)
    });

    const password = watch('password', '');
    const getPasswordStrength = (pass) => {
        let strength = 0;
        if (pass.length > 7) strength++;
        if (/[A-Z]/.test(pass)) strength++;
        if (/[0-9]/.test(pass)) strength++;
        if (/[^A-Za-z0-9]/.test(pass)) strength++;
        return strength;
    };
    const strength = getPasswordStrength(password);
    const strengthLabels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
    const strengthColors = ['', 'var(--danger)', 'var(--warning)', 'var(--info)', 'var(--success)'];

    const onSubmit = async (data) => {
        setIsSubmitting(true);
        setApiError(null);
        try {
            await authActions.register(data);
            navigate('/verify-email-sent');
        } catch (err) {
            let errorMessage = 'Registration failed. Try again.';
            if (err.response?.data) {
                const errorData = err.response.data;
                if (Array.isArray(errorData.details) && errorData.details.length > 0) {
                    errorMessage = errorData.details.map(e => e.message.replace(/^Value error,\s*/i, '')).join(', ');
                } else if (errorData.message) {
                    errorMessage = errorData.message;
                } else if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                } else if (errorData.detail?.message) {
                    errorMessage = errorData.detail.message;
                } else if (Array.isArray(errorData.detail)) {
                    errorMessage = errorData.detail.map(e => e.msg).join(', ');
                }
            }
            setApiError(errorMessage);
        } finally {
            setIsSubmitting(false);
        }
    };

    const inputIcon = (Icon) => (
        <Icon size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
    );

    return (
        <div className="card" style={{ borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-md)' }}>
            <div className="card-body p-4 p-md-5">
                <h2 style={{ fontWeight: 800, fontSize: '1.5rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                    Create your account
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.75rem' }}>
                    Join thousands of Nigerians trading on KaraKaja
                </p>

                {apiError && (
                    <div style={{
                        padding: '0.75rem 1rem', background: 'var(--danger-light)', border: '1px solid #FECACA',
                        borderRadius: 'var(--radius)', color: 'var(--danger)', fontSize: '0.8125rem', fontWeight: 500, marginBottom: '1.25rem',
                    }}>
                        {apiError}
                    </div>
                )}

                <form onSubmit={handleSubmit(onSubmit)}>
                    <div className="row g-3">
                        <div className="col-6">
                            <label className="form-label">First Name</label>
                            <div style={{ position: 'relative' }}>
                                {inputIcon(FiUser)}
                                <input {...register('first_name')} className={`form-control ${errors.first_name ? 'is-invalid' : ''}`} style={{ paddingLeft: '2.5rem' }} />
                            </div>
                            {errors.first_name && <div className="text-danger" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{errors.first_name.message}</div>}
                        </div>
                        <div className="col-6">
                            <label className="form-label">Last Name</label>
                            <div style={{ position: 'relative' }}>
                                {inputIcon(FiUser)}
                                <input {...register('last_name')} className={`form-control ${errors.last_name ? 'is-invalid' : ''}`} style={{ paddingLeft: '2.5rem' }} />
                            </div>
                            {errors.last_name && <div className="text-danger" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{errors.last_name.message}</div>}
                        </div>
                    </div>

                    <div className="mt-3">
                        <label className="form-label">Email</label>
                        <div style={{ position: 'relative' }}>
                            {inputIcon(FiMail)}
                            <input type="email" {...register('email')} className={`form-control ${errors.email ? 'is-invalid' : ''}`} placeholder="name@example.com" style={{ paddingLeft: '2.5rem' }} />
                        </div>
                        {errors.email && <div className="text-danger" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{errors.email.message}</div>}
                    </div>

                    <div className="mt-3">
                        <label className="form-label">Phone Number</label>
                        <div style={{ position: 'relative' }}>
                            {inputIcon(FiPhone)}
                            <input placeholder="08012345678" {...register('phone_number')} className={`form-control ${errors.phone_number ? 'is-invalid' : ''}`} style={{ paddingLeft: '2.5rem' }} />
                        </div>
                        {errors.phone_number && <div className="text-danger" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{errors.phone_number.message}</div>}
                    </div>

                    <div className="mt-3">
                        <label className="form-label">Password</label>
                        <div style={{ position: 'relative' }}>
                            {inputIcon(FiLock)}
                            <input type="password" {...register('password')} className={`form-control ${errors.password ? 'is-invalid' : ''}`} style={{ paddingLeft: '2.5rem' }} />
                        </div>
                        {password && (
                            <>
                                <div className="mt-2 d-flex align-items-center gap-2">
                                    <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'var(--border)' }}>
                                        <div style={{ width: `${(strength / 4) * 100}%`, height: '100%', borderRadius: 2, background: strengthColors[strength], transition: 'width 0.3s, background 0.3s' }} />
                                    </div>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: strengthColors[strength] }}>{strengthLabels[strength]}</span>
                                </div>
                                <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0 0', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                    {[
                                        { label: 'At least 8 characters', met: password.length >= 8 },
                                        { label: 'One uppercase letter', met: /[A-Z]/.test(password) },
                                        { label: 'One number', met: /[0-9]/.test(password) },
                                        { label: 'One special character (!@#$%…)', met: /[^A-Za-z0-9]/.test(password) },
                                    ].map(({ label, met }) => (
                                        <li key={label} style={{ fontSize: '0.75rem', color: met ? 'var(--success)' : 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                            <span style={{ fontSize: '0.65rem' }}>{met ? '✓' : '○'}</span>
                                            {label}
                                        </li>
                                    ))}
                                </ul>
                            </>
                        )}
                        {errors.password && <div className="text-danger" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{errors.password.message}</div>}
                    </div>

                    <div className="mt-3 mb-4">
                        <label className="form-label">Confirm Password</label>
                        <div style={{ position: 'relative' }}>
                            {inputIcon(FiLock)}
                            <input type="password" {...register('confirm_password')} className={`form-control ${errors.confirm_password ? 'is-invalid' : ''}`} style={{ paddingLeft: '2.5rem' }} />
                        </div>
                        {errors.confirm_password && <div className="text-danger" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>{errors.confirm_password.message}</div>}
                    </div>

                    <button type="submit" disabled={isSubmitting} className="btn btn-primary w-100 mb-3" style={{ padding: '0.625rem', fontWeight: 600 }}>
                        {isSubmitting ? <><span className="spinner-sm" /> Creating account...</> : <>Create Account <FiArrowRight size={16} /></>}
                    </button>

                    <p className="text-center mb-0" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                        Already have an account? <Link to="/login" style={{ fontWeight: 600 }}>Sign in</Link>
                    </p>
                </form>
            </div>
        </div>
    );
}
