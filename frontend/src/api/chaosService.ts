/**
 * Chaos Engineering and Contact mutation functions.
 * These are write operations (POST) that trigger side effects on the backend.
 */
import { buildApiUrl, ApiError, extractTraceId } from './client';
import type { ChaosResponse, ContactResponse } from './types';

// Re-export types so consumers can import from a single service file
export type { ChaosResponse, ContactResponse };

// ─── Contact Form ─────────────────────────────────────────────────────────────

export async function postContact(
  data: {
    name: string;
    email: string;
    subject: string;
    message: string;
    website: string; // Honeypot field
    fax: string;     // Honeypot field
  },
  idempotencyKey: string,
): Promise<ContactResponse> {
  const apiUrl = buildApiUrl('/contact');

  const start = performance.now();
  const res = await fetch(apiUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify(data),
  });
  const durationMs = Math.round(performance.now() - start);

  const rawData = await res.json().catch(() => null);
  const traceId = extractTraceId(res, rawData);

  if (!res.ok) {
    throw new ApiError(res.status, `Failed to submit contact form: ${res.status}`, traceId);
  }

  return {
    traceId,
    durationMs,
    queueStatus: (rawData as Record<string, unknown>)?.queue_status as string | undefined,
    deliveryMode: (rawData as Record<string, unknown>)?.delivery_mode as string | undefined,
    downstream: (rawData as Record<string, unknown>)?.downstream as string | undefined,
    message: (rawData as Record<string, unknown>)?.message as string | undefined,
  };
}

// ─── Chaos Actions ────────────────────────────────────────────────────────────

export async function postChaosSpike(): Promise<ChaosResponse> {
  const res = await fetch(buildApiUrl('/chaos/spike'), { method: 'POST' });
  if (!res.ok) throw new ApiError(res.status, `Chaos spike failed: ${res.status}`);
  return res.json();
}

export async function postChaosDrain(): Promise<ChaosResponse> {
  const res = await fetch(buildApiUrl('/chaos/drain'), { method: 'POST' });
  if (!res.ok) throw new ApiError(res.status, `Chaos drain failed: ${res.status}`);
  return res.json();
}

export async function postChaosRetry(): Promise<ChaosResponse> {
  const res = await fetch(buildApiUrl('/chaos/retry'), { method: 'POST' });
  if (!res.ok) throw new ApiError(res.status, `Chaos retry failed: ${res.status}`);
  return res.json();
}

export async function postChaosLatency(): Promise<ChaosResponse> {
  const res = await fetch(buildApiUrl('/chaos/latency'), { method: 'POST' });
  if (!res.ok) throw new ApiError(res.status, `Chaos latency failed: ${res.status}`);
  return res.json();
}

// ─── Cache Stress (client-side simulation) ───────────────────────────────────
// Fires 10 concurrent GETs against existing read endpoints.
// NOTE: This is a client-side simulation — it generates real backend load
// but does not appear as a tracked chaos incident in /metrics/summary.
export async function postChaosCache(): Promise<{
  requests_sent: number;
  elapsed_ms: number;
  timestamp: string;
}> {
  const endpoints = [
    '/about', '/stack', '/projects', '/experiences', '/formation',
    '/about', '/stack', '/projects', '/experiences', '/formation',
  ];
  const start = performance.now();
  await Promise.allSettled(endpoints.map((path) => fetch(buildApiUrl(path))));
  const elapsed_ms = Math.round(performance.now() - start);
  return {
    requests_sent: endpoints.length,
    elapsed_ms,
    timestamp: new Date().toISOString(),
  };
}
