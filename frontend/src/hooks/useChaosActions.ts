/**
 * useChaosActions — encapsulates all chaos operation handlers.
 *
 * Manages per-action loading/cooldown state and delegates to the
 * chaos API service. Returns stable handler callbacks and reactive state
 * for the ChaosPlayground UI.
 */
import { useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { buildApiUrl, ApiError, API_BASE_URL } from '../api/client';
import { postChaosDrain, postChaosRetry, postChaosLatency, type ChaosResponse } from '../api/chaosService';
import { emitTrace } from '../services/TraceEmitter';
import * as Sentry from '@sentry/react';
import type { LogLevel } from '../types/logs';
import type { Incident } from '../types/incidents';

// Shared cooldown duration in seconds
const COOLDOWN_SECONDS = 30;

function genReqId(): string {
  return Math.random().toString(36).slice(2, 10).toUpperCase();
}

export interface TerminalEntry {
  id: number;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
  requestId: string;
  timestamp: string;
}

interface UseChaosActionsOptions {
  addTerminalEntry: (level: TerminalEntry['level'], message: string, requestId: string) => void;
  addEntry: (level: LogLevel, message: string, requestId?: string) => void;
  addIncident: (type: string, labelKey: string, meta?: Pick<Incident, 'impactPct' | 'durationMs' | 'origin'>) => void;
}

export function useChaosActions({ addTerminalEntry, addEntry, addIncident }: UseChaosActionsOptions) {
  const queryClient = useQueryClient();

  // Per-action loading state
  const [drainLoading, setDrainLoading] = useState(false);
  const [retryLoading, setRetryLoading] = useState(false);
  const [latencyLoading, setLatencyLoading] = useState(false);

  // Per-action cooldown state (seconds remaining)
  const [drainCooldown, setDrainCooldown] = useState(0);
  const [retryCooldown, setRetryCooldown] = useState(0);
  const [latencyCooldown, setLatencyCooldown] = useState(0);

  const invalidateMetrics = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['metrics-summary'] });
  }, [queryClient]);

  const startCooldown = useCallback((setter: React.Dispatch<React.SetStateAction<number>>) => {
    setter(COOLDOWN_SECONDS);
    const iv = setInterval(() => {
      setter((prev) => {
        if (prev <= 1) { clearInterval(iv); return 0; }
        return prev - 1;
      });
    }, 1000);
  }, []);

  // ─── Handlers ─────────────────────────────────────────────────────────────

  const handleDrain = useCallback(async () => {
    if (drainLoading || drainCooldown > 0) return;
    setDrainLoading(true);
    const rid = genReqId();
    const traceId = `trace-${rid}`;
    addTerminalEntry('INFO', `chaos.drain triggered request_id=${rid} trace_id=${traceId}`, rid);
    addEntry('INFO', `chaos.drain status=TRIGGERED type=QUEUE_DRAIN trace_id=${traceId}`, rid);
    try {
      const res: ChaosResponse = await postChaosDrain();
      const purged = res.tasks_purged ?? 0;
      addTerminalEntry('WARN', `queue.drain completed tasks_purged=${purged} request_id=${rid} trace_id=${traceId}`, rid);
      addEntry('WARN', `queue.drain status=COMPLETED tasks_purged=${purged} trace_id=${traceId}`, rid);
      addIncident('queue_drain', 'chaos.action.drain.title', { impactPct: '0%', durationMs: res.elapsed_ms ?? 50, origin: 'synthetic' });
      emitTrace({ id: `trace-${rid}`, traceId, requestId: rid, type: 'queue_drain', origin: 'synthetic', endpoint: '/chaos/drain', status: 'ok', totalMs: 50, apiMs: 10, dbMs: 40, cacheMs: 0, timestamp: new Date(), impactPct: '0%', latencyDelta: '-40ms', durationMs: res.elapsed_ms ?? 50 });
      invalidateMetrics();
      startCooldown(setDrainCooldown);
    } catch (err: unknown) {
      const isNetworkError = err instanceof TypeError || (err instanceof Error && err.name === 'TypeError');
      const isApiError = err instanceof ApiError;
      const msg = err instanceof Error ? err.message : 'Unknown error';
      const url = buildApiUrl('/chaos/drain');
      const errorTag = isNetworkError ? 'NETWORK' : isApiError ? `HTTP_${(err as ApiError).status}` : 'UNKNOWN';
      
      Sentry.withScope((scope) => {
        scope.setTag('api_base_url', API_BASE_URL);
        scope.setTag('endpoint', '/chaos/drain');
        scope.setTag('error_type', errorTag);
        scope.setExtra('url', url);
        scope.setExtra('request_id', rid);
        Sentry.captureException(err);
      });

      addTerminalEntry('ERROR', `chaos.drain failed error="${msg}" error_type=${errorTag} url=${url} request_id=${rid} trace_id=${traceId}`, rid);
      addEntry('ERROR', `chaos.drain status=FAILED error_type=${errorTag} error="${msg}" trace_id=${traceId}`, rid);
    } finally { setDrainLoading(false); }
  }, [drainLoading, drainCooldown, addTerminalEntry, addEntry, addIncident, invalidateMetrics, startCooldown]);

  const handleRetry = useCallback(async () => {
    if (retryLoading || retryCooldown > 0) return;
    setRetryLoading(true);
    const rid = genReqId();
    const traceId = `trace-${rid}`;
    addTerminalEntry('INFO', `chaos.retry triggered request_id=${rid} trace_id=${traceId}`, rid);
    addEntry('INFO', `chaos.retry status=TRIGGERED type=MANUAL_RETRY trace_id=${traceId}`, rid);
    try {
      await postChaosRetry();
      addTerminalEntry('INFO', `manual.retry dispatched request_id=${rid} trace_id=${traceId}`, rid);
      addEntry('INFO', `manual.retry status=COMPLETED trace_id=${traceId}`, rid);
      addIncident('manual_retry', 'chaos.action.retry.title', { impactPct: '5%', durationMs: 120, origin: 'synthetic' });
      emitTrace({ id: `trace-${rid}`, traceId, requestId: rid, type: 'manual_retry', origin: 'synthetic', endpoint: '/chaos/retry', status: 'ok', totalMs: 120, apiMs: 20, dbMs: 100, cacheMs: 0, timestamp: new Date(), impactPct: '5%', latencyDelta: '+80ms', durationMs: 120 });
      invalidateMetrics();
      startCooldown(setRetryCooldown);
    } catch (err: unknown) {
      const isNetworkError = err instanceof TypeError || (err instanceof Error && err.name === 'TypeError');
      const isApiError = err instanceof ApiError;
      const msg = err instanceof Error ? err.message : 'Unknown error';
      const url = buildApiUrl('/chaos/retry');
      const errorTag = isNetworkError ? 'NETWORK' : isApiError ? `HTTP_${(err as ApiError).status}` : 'UNKNOWN';
      
      Sentry.withScope((scope) => {
        scope.setTag('api_base_url', API_BASE_URL);
        scope.setTag('endpoint', '/chaos/retry');
        scope.setTag('error_type', errorTag);
        scope.setExtra('url', url);
        scope.setExtra('request_id', rid);
        Sentry.captureException(err);
      });

      addTerminalEntry('ERROR', `chaos.retry failed error="${msg}" error_type=${errorTag} url=${url} request_id=${rid} trace_id=${traceId}`, rid);
      addEntry('ERROR', `chaos.retry status=FAILED error_type=${errorTag} error="${msg}" trace_id=${traceId}`, rid);
    } finally { setRetryLoading(false); }
  }, [retryLoading, retryCooldown, addTerminalEntry, addEntry, addIncident, invalidateMetrics, startCooldown]);

  const handleLatency = useCallback(async () => {
    if (latencyLoading || latencyCooldown > 0) return;
    setLatencyLoading(true);
    const rid = genReqId();
    const traceId = `trace-${rid}`;
    addTerminalEntry('INFO', `chaos.latency triggered request_id=${rid} trace_id=${traceId}`, rid);
    addEntry('INFO', `chaos.latency status=TRIGGERED type=LATENCY_INJECTION trace_id=${traceId}`, rid);
    try {
      const res: ChaosResponse = await postChaosLatency();
      addTerminalEntry('WARN', `latency.injection status=TIMEOUT latency_ms=${res.latency_ms} circuit_breaker=OPEN request_id=${rid} trace_id=${traceId}`, rid);
      addEntry('WARN', `latency.injection status=TIMEOUT latency_ms=${res.latency_ms} circuit_breaker=OPEN trace_id=${traceId}`, rid);
      addIncident('latency_injection', 'chaos.action.latency.title', { impactPct: '100%', durationMs: res.latency_ms ?? 3000, origin: 'synthetic' });
      emitTrace({ id: `trace-${rid}`, traceId, requestId: rid, type: 'latency_injection', origin: 'synthetic', endpoint: '/chaos/latency', status: 'error', totalMs: res.latency_ms || 3000, apiMs: 50, dbMs: (res.latency_ms || 3000) - 50, cacheMs: 0, timestamp: new Date(), impactPct: '100%', latencyDelta: `+${((res.latency_ms || 3000) / 1000).toFixed(1)}s`, durationMs: res.latency_ms ?? 3000 });
      invalidateMetrics();
      startCooldown(setLatencyCooldown);
    } catch (err: unknown) {
      const isNetworkError = err instanceof TypeError || (err instanceof Error && err.name === 'TypeError');
      const isApiError = err instanceof ApiError;
      const msg = err instanceof Error ? err.message : 'Unknown error';
      const url = buildApiUrl('/chaos/latency');
      const errorTag = isNetworkError ? 'NETWORK' : isApiError ? `HTTP_${(err as ApiError).status}` : 'UNKNOWN';
      
      Sentry.withScope((scope) => {
        scope.setTag('api_base_url', API_BASE_URL);
        scope.setTag('endpoint', '/chaos/latency');
        scope.setTag('error_type', errorTag);
        scope.setExtra('url', url);
        scope.setExtra('request_id', rid);
        Sentry.captureException(err);
      });

      addTerminalEntry('ERROR', `chaos.latency failed error="${msg}" error_type=${errorTag} url=${url} request_id=${rid} trace_id=${traceId}`, rid);
      addEntry('ERROR', `chaos.latency status=FAILED error_type=${errorTag} error="${msg}" trace_id=${traceId}`, rid);
    } finally { setLatencyLoading(false); }
  }, [latencyLoading, latencyCooldown, addTerminalEntry, addEntry, addIncident, invalidateMetrics, startCooldown]);

  return {
    handleDrain, handleRetry, handleLatency,
    drainLoading, retryLoading, latencyLoading,
    drainCooldown, retryCooldown, latencyCooldown,
  };
}
