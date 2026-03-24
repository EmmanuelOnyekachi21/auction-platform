import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useNavigate, Link } from 'react-router-dom';
import { useState } from 'react';
import { authActions } from '../../api/auth';

// Define the validation rules (Zod Schema)
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
    const [isSubmitting, setIssubmitting] = useState(false);

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
    const strengthColors = ['bg-danger', 'bg-warning', 'bg-info', 'bg-primary', 'bg-success'];

    const onSubmit = async (data) => {
        setIssubmitting(true);
        setApiError(null);
        try {
            await authActions.register(data);
            navigate('/verify-email-sent');
        } catch (err) {
            setApiError(err.response?.data?.detail || 'Registration failed. Try again.');
        } finally {
            setIssubmitting(false);
        }
    };

    return (
        <div className="container mt-5">
            <div className="row justify-content-center">
                <div className="col-md-6 card shadow p-4">
                    <h2 className="text-center mb-4">Join Auction Platform</h2>

                    {apiError && <div className="alert alert-danger">{apiError}</div>}

                    <form onSubmit={handleSubmit(onSubmit)}>
                        <div className="row">
                            <div className="col-md-6 mb-3">
                                <label className="form-label">First Name</label>
                                <input
                                    {...register('first_name')}
                                    className={`form-control ${errors.first_name ? 'is-invalid' : ''}`}
                                />
                                <div className="invalid-feedback">{errors.first_name?.message}</div>
                            </div>

                            <div className="col-md-6 mb-3">
                                <label className="form-label">Last Name</label>
                                <input
                                    {...register('last_name')}
                                    className={`form-control ${errors.last_name ? 'is-invalid' : ''}`}
                                />
                                <div className="invalid-feedback">{errors.last_name?.message}</div>
                            </div>
                        </div>

                        <div className="mb-3">
                            <label className="form-label">Email</label>
                            <input
                                type="email"
                                {...register('email')}
                                className={`form-control ${errors.email ? 'is-invalid' : ''}`}
                            />
                            <div className="invalid-feedback">{errors.email?.message}</div>
                        </div>

                        <div className="mb-3">
                            <label className="form-label">Phone Number (Nigerian)</label>
                            <input
                                placeholder="e.g. 08012345678"
                                {...register('phone_number')}
                                className={`form-control ${errors.phone_number ? 'is-invalid' : ''}`}
                            />
                            <div className="invalid-feedback">{errors.phone_number?.message}</div>
                        </div>

                        <div className="mb-3">
                            <label className="form-label">Password</label>
                            <input
                                type="password"
                                {...register('password')}
                                className={`form-control ${errors.password ? 'is-invalid' : ''}`}
                            />
                            {password && (
                                <div className="progress mt-2" style={{ height: '5px' }}>
                                    <div
                                        className={`progress-bar ${strengthColors[strength]}`}
                                        style={{ width: `${(strength / 4) * 100}%` }}
                                    />
                                </div>
                            )}
                            <div className="invalid-feedback d-block">{errors.password?.message}</div>
                        </div>

                        <div className="mb-4">
                            <label className="form-label">Confirm Password</label>
                            <input
                                type="password"
                                {...register('confirm_password')}
                                className={`form-control ${errors.confirm_password ? 'is-invalid' : ''}`}
                            />
                            <div className="invalid-feedback">{errors.confirm_password?.message}</div>
                        </div>

                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="btn btn-primary w-100 mb-3"
                        >
                            {isSubmitting ? 'Registering...' : 'Sign Up'}
                        </button>

                        <p className="text-center">
                            Already have an account? <Link to="/login">Login</Link>
                        </p>
                    </form>
                </div>
            </div>
        </div>
    );
}
