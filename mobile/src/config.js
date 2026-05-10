// Base domain for tenant subdomains.
// Tenants are accessed as: https://{code}.BASE_DOMAIN
// You can also enter a full URL (e.g. http://192.168.1.5:8080) in the app for local testing.
export const BASE_DOMAIN = 'yourdomain.com'; // TODO: set your actual domain

export function buildTenantUrl(input) {
  const trimmed = input.trim();
  if (trimmed.includes('://')) return trimmed.replace(/\/$/, '');
  return `https://${trimmed}.${BASE_DOMAIN}`;
}
