import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useQueryClient } from '@tanstack/react-query';
import apiClient from '../../api/client';
import { useToast } from '../../components/common/Toast';
import { FiChevronDown, FiChevronUp, FiCreditCard, FiHash, FiUser, FiSave, FiX } from 'react-icons/fi';

const NIGERIAN_BANKS = [
    { name: 'Access Bank', code: '044' },
    { name: 'Guaranty Trust Bank (GTB)', code: '058' },
    { name: 'First Bank of Nigeria', code: '011' },
    { name: 'Zenith Bank', code: '057' },
    { name: 'United Bank for Africa (UBA)', code: '033' },
];

export default function BankDetailsSection({ profile, onUpdate }) {
    const [isEditing, setIsEditing] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const { showToast } = useToast();
    const queryClient = useQueryClient();

    const bankDetails = profile.profile || {};
    const hasBankDetails = bankDetails.account_number && bankDetails.bank_code;

    const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
        defaultValues: {
            bank_code: bankDetails.bank_code || '',
            account_number: bankDetails.account_number || '',
            account_name: bankDetails.account_name || ''
        }
    });

    const onSubmit = async (data) => {
        try {
            await apiClient.patch('/users/me', data);
            showToast('Bank details updated successfully!', 'success');
            setIsEditing(false);
            queryClient.invalidateQueries({ queryKey: ['userProfile'] });
            if (onUpdate) onUpdate();
        } catch (error) {
            const msg = error.response?.data?.detail || 'Failed to update bank details';
            showToast(msg, 'error');
        }
    };

    const getBankName = (code) => {
        const bank = NIGERIAN_BANKS.find(b => b.code === code);
        return bank ? bank.name : code;
    };

    return (
        <div className="card" style={{ borderRadius: 'var(--radius-xl)', overflow: 'hidden' }}>
            <div
                className="card-header d-flex justify-content-between align-items-center"
                style={{ cursor: 'pointer', padding: '1rem 1.25rem' }}
                onClick={() => setIsOpen(!isOpen)}
            >
                <div className="d-flex align-items-center gap-2" style={{ fontWeight: 700, fontSize: '0.9375rem' }}>
                    <FiCreditCard size={16} style={{ color: 'var(--primary)' }} />
                    Withdrawal Bank Details
                </div>
                {isOpen ? <FiChevronUp size={16} style={{ color: 'var(--text-muted)' }} /> : <FiChevronDown size={16} style={{ color: 'var(--text-muted)' }} />}
            </div>
            {isOpen && (
                <div className="card-body" style={{ borderTop: '1px solid var(--border)' }}>
                    {!isEditing ? (
                        <div>
                            {hasBankDetails ? (
                                <div className="row g-3">
                                    {[
                                        { icon: <FiCreditCard size={14} />, label: 'Bank', value: getBankName(bankDetails.bank_code) },
                                        { icon: <FiHash size={14} />, label: 'Account Number', value: bankDetails.account_number },
                                        { icon: <FiUser size={14} />, label: 'Account Name', value: bankDetails.account_name },
                                    ].map((item, i) => (
                                        <div className="col-md-4" key={i}>
                                            <div className="d-flex align-items-center gap-1" style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                                                {item.icon} {item.label}
                                            </div>
                                            <div style={{ fontWeight: 600, fontSize: '0.9375rem' }}>{item.value}</div>
                                        </div>
                                    ))}
                                    <div className="col-12 mt-2">
                                        <button className="btn btn-outline-primary btn-sm" onClick={() => setIsEditing(true)}>
                                            <FiCreditCard size={13} /> Edit Details
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div style={{
                                    padding: '1rem', background: 'var(--warning-light)',
                                    borderRadius: 'var(--radius)', display: 'flex',
                                    alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap',
                                }}>
                                    <div style={{ flex: 1, minWidth: 200 }}>
                                        <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--warning)' }}>No bank details found</div>
                                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>Add bank details to enable withdrawals</div>
                                    </div>
                                    <button className="btn btn-primary btn-sm" onClick={() => setIsEditing(true)}>Add Bank Details</button>
                                </div>
                            )}
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit(onSubmit)}>
                            <div className="row g-3">
                                <div className="col-md-6">
                                    <label className="form-label">Select Bank</label>
                                    <select className={`form-select ${errors.bank_code ? 'is-invalid' : ''}`} {...register('bank_code', { required: 'Bank is required' })}>
                                        <option value="">Choose a bank...</option>
                                        {NIGERIAN_BANKS.map(bank => (
                                            <option key={bank.code} value={bank.code}>{bank.name}</option>
                                        ))}
                                    </select>
                                    {errors.bank_code && <div className="invalid-feedback">{errors.bank_code.message}</div>}
                                </div>
                                <div className="col-md-6">
                                    <label className="form-label">Account Number</label>
                                    <input type="text" className={`form-control ${errors.account_number ? 'is-invalid' : ''}`} placeholder="0123456789" maxLength="10"
                                        {...register('account_number', { required: 'Required', pattern: { value: /^[0-9]{10}$/, message: 'Must be 10 digits' } })} />
                                    {errors.account_number && <div className="invalid-feedback">{errors.account_number.message}</div>}
                                </div>
                                <div className="col-12">
                                    <label className="form-label">Account Name</label>
                                    <input type="text" className={`form-control ${errors.account_name ? 'is-invalid' : ''}`} placeholder="Full account name"
                                        {...register('account_name', { required: 'Required' })} />
                                    {errors.account_name && <div className="invalid-feedback">{errors.account_name.message}</div>}
                                </div>
                                <div className="col-12 pt-2 d-flex gap-2">
                                    <button type="submit" className="btn btn-primary btn-sm" disabled={isSubmitting}>
                                        {isSubmitting ? <><span className="spinner-sm" /> Saving...</> : <><FiSave size={13} /> Save</>}
                                    </button>
                                    <button type="button" className="btn btn-light btn-sm" onClick={() => setIsEditing(false)} disabled={isSubmitting}>
                                        <FiX size={13} /> Cancel
                                    </button>
                                </div>
                            </div>
                        </form>
                    )}
                </div>
            )}
        </div>
    );
}
