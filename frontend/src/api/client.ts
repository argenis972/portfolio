/**
 * Base HTTP client for the portfolio API.
 *
 * Responsibilities:
 *  - URL construction from VITE_API_URL environment variable
 *  - Centralized trace_id extraction (header → body fallback chain)
 *  - Zod schema validation on every GET response
 *  - Structured error reporting via ApiError
 */
import { z } from 'zod';

/**
 * Ensures the base URL ends with /api/v1.
 * If it already ends with /api/v{number}, leaves it untouched.
 * Otherwise appends /api/v1 and warns in dev mode.
 */
export function ensureApiV1Suffix(url: string): string {
  if (/\/api\/v\d+$/.test(url)) return url;
  const normalized = url.endsWith('/api')
    ? url + '/v1'
    : url.replace(/\/+$/, '') + '/api/v1';
  if (import.meta.env.DEV) {
    console.warn(
      `[API] VITE_API_URL="${url}" no incluye /api/v1. ` +
      `Se normalizó automáticamente a "${normalized}". ` +
      `Fija el valor exacto en Vercel Dashboard para eliminar este warning.`,
    );
  }
  return normalized;
}

const configuredApiBaseUrl = import.meta.env.VITE_API_URL?.trim();
export const API_BASE_URL = (() => {
  const base = configuredApiBaseUrl || (import.meta.env.DEV ? 'http://127.0.0.1:8000/api/v1' : '');
  if (!base) return '';
  return ensureApiV1Suffix(base);
})();

export function buildApiUrl(path: string): string {
  if (!API_BASE_URL) {
    throw new Error('VITE_API_URL is not configured');
  }
  return `${API_BASE_URL}${path}`;
}

// ─── Trace ID Extraction ──────────────────────────────────────────────────────

/**
 * Extracts the trace/request ID from a response using a prioritized fallback chain:
 *   1. `X-Trace-ID` response header (OpenTelemetry standard)
 *   2. `X-Request-ID` response header (middleware-generated UUID)
 *   3. `rawData.error.trace_id` (nested backend error envelope)
 *   4. `rawData.trace_id` (top-level, legacy/success responses)
 */
export function extractTraceId(
  res: Response,
  rawData: unknown,
): string | undefined {
  return (
    res.headers.get('x-trace-id') ??
    res.headers.get('x-request-id') ??
    (rawData as Record<string, Record<string, unknown>> | null)?.error?.trace_id as string | undefined ??
    (rawData as Record<string, unknown> | null)?.trace_id as string | undefined ??
    undefined
  );
}

// ─── Error Class ──────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  traceId?: string;

  constructor(status: number, message: string, traceId?: string) {
    super(message);
    this.status = status;
    this.traceId = traceId;
    this.name = 'ApiError';
  }
}

// ─── Generic GET with Zod validation ─────────────────────────────────────────

export async function apiGet<T>(
  path: string,
  schema: z.ZodSchema<T>,
  chaosPreset?: string,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (chaosPreset) {
    headers['X-Chaos-Preset'] = chaosPreset;
  }

  const res = await fetch(buildApiUrl(path), { headers });

  // Parse body first so we can extract trace_id from error responses
  const rawData = await res.json().catch(() => null);

  const traceId = extractTraceId(res, rawData);

  if (!res.ok) {
    console.error('[API ERROR]', { traceId, status: res.status, endpoint: path });
    throw new ApiError(
      res.status,
      `API request failed: ${res.status} ${res.statusText} (${path})`,
      traceId,
    );
  }

  // Zod contract validation
  const result = schema.safeParse(rawData);
  if (!result.success) {
    console.error(`[Zod Error] Critical contract violation in ${path}:`, result.error.format());
    throw new Error(`Schema validation failed for ${path}`);
  }

  return result.data;
}
