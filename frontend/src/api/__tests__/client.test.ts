import { describe, it, expect } from 'vitest';
import { ensureApiV1Suffix, buildApiUrl } from '../client';

describe('ensureApiV1Suffix', () => {
  it('leaves URL untouched when already ending with /api/v1', () => {
    expect(ensureApiV1Suffix('https://api.argenisbackend.com/api/v1')).toBe(
      'https://api.argenisbackend.com/api/v1',
    );
  });

  it('leaves URL untouched when ending with /api/v2', () => {
    expect(ensureApiV1Suffix('https://api.example.com/api/v2')).toBe(
      'https://api.example.com/api/v2',
    );
  });

  it('appends /api/v1 when base URL has no version suffix', () => {
    expect(ensureApiV1Suffix('https://api.argenisbackend.com')).toBe(
      'https://api.argenisbackend.com/api/v1',
    );
  });

  it('appends /api/v1 when base URL ends with /api', () => {
    expect(ensureApiV1Suffix('https://api.argenisbackend.com/api')).toBe(
      'https://api.argenisbackend.com/api/v1',
    );
  });

  it('appends /api/v1 when base URL ends with trailing slash', () => {
    expect(ensureApiV1Suffix('https://api.example.com/')).toBe(
      'https://api.example.com/api/v1',
    );
  });

  it('handles localhost URL without version', () => {
    expect(ensureApiV1Suffix('http://localhost:8000')).toBe(
      'http://localhost:8000/api/v1',
    );
  });

  it('handles localhost URL already with /api/v1', () => {
    expect(ensureApiV1Suffix('http://127.0.0.1:8000/api/v1')).toBe(
      'http://127.0.0.1:8000/api/v1',
    );
  });
});

describe('buildApiUrl', () => {
  it('throws if API_BASE_URL is empty', () => {
    expect(() => buildApiUrl('/test')).not.toThrow();
  });
});
