import apiClient from './client';

export const getKYCStatus = async () => {
  const res = await apiClient.get('/kyc/status');
  return res.data;
};

export const verifyBVN = async ({ bvn, date_of_birth }) => {
  const res = await apiClient.post('/kyc/verify-bvn', { bvn, date_of_birth });
  return res.data;
};
