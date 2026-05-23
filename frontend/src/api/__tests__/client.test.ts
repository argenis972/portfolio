import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ensureApiV1Suffix } from '../client';

describe('API URL normalizer (ensureApiV1Suffix)', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it('preserves url if it already has /api/v1', () => {
    expect(ensureApiV1Suffix('https://api.test.com/api/v1')).toBe('https://api.test.com/api/v1');
  });

  it('preserves url if it already has another version like /api/v2', () => {
    expect(ensureApiV1Suffix('https://api.test.com/api/v2')).toBe('https://api.test.com/api/v2');
  });

  it('normalizes missing suffix and warns in DEV environment', () => {
    const originalDev = import.meta.env.DEV;
    const originalProd = import.meta.env.PROD;
    
    import.meta.env.DEV = true;
    import.meta.env.PROD = false;

    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    
    expect(ensureApiV1Suffix('https://api.test.com')).toBe('https://api.test.com/api/v1');
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();

    import.meta.env.DEV = originalDev;
    import.meta.env.PROD = originalProd;
  });

  it('throws an error in PROD environment if suffix is missing (Fail-fast)', () => {
    const originalDev = import.meta.env.DEV;
    const originalProd = import.meta.env.PROD;
    
    import.meta.env.DEV = false;
    import.meta.env.PROD = true;
    
    expect(() => ensureApiV1Suffix('https://api.test.com')).toThrowError(/It must end with \/api\/v1 in production/);
    
    import.meta.env.DEV = originalDev;
    import.meta.env.PROD = originalProd;
  });
});
