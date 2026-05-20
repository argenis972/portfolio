/**
 * useLiveMetrics — polling hook for the live evidence dashboard.
 *
 * Polling strategy:
 *   staleTime: 10s   — prevents redundant fetches on navigation
 *   refetchInterval: 15s — live without hammering the API
 *   refetchIntervalInBackground: false — no requests when tab is hidden
 *   refetchOnWindowFocus: false — explicit guard (don't rely on global default)
 *   gcTime: 60s — keeps data in cache during brief unmounts
 *
 * Extras:
 *   history   — rolling last-20 P95 values for the sparkline chart
 *   previous  — snapshot of the prior fetch for delta calculation
 */
import { useMemo, useRef, useState, useEffect } from 'react';
import { useCurrentTime } from './useCurrentTime';
import { useQuery } from '@tanstack/react-query';
import { fetchMetricsSummary, type MetricsSummary } from '../api/portfolioService';
import { useChaosMode } from './useChaosMode';
import { getRecentTraces, subscribeToTraces, type TraceEntry } from '../services/TraceEmitter';
import { type MetricSample } from '../types/metrics';

// Named thresholds — visible numbers = engineering confidence
const LATENCY_WARNING_MS = 60;
const LATENCY_DEGRADED_MS = 100;
const ERROR_RATE_DEGRADED = 0.05;
const MAX_HISTORY = 12;
const SYNTHETIC_WINDOW_MS = 20_000;
const RECOVERING_WINDOW_MS = 45_000;
const DEFAULT_CONFIDENCE_REAL = 98;

const TRACE_PROJECTION: Record<TraceEntry['type'], { factor: number; floor: number; cap: number }> = {
  traffic_spike: { factor: 0.45, floor: 18, cap: 160 },
  forced_failure: { factor: 0.4, floor: 24, cap: 180 },
  cache_stress: { factor: 0.25, floor: 12, cap: 70 },
  queue_drain: { factor: 0.5, floor: -50, cap: -12 },
  manual_retry: { factor: 0.6, floor: 20, cap: 110 },
  latency_injection: { factor: 0.14, floor: 80, cap: 420 },
};

export type SystemStatus = 'loading' | 'operational' | 'warning' | 'degraded' | 'down';

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function parseLatencyDelta(raw?: string): number | null {
  if (!raw) return null;
  const match = raw.trim().match(/^([+-]?)(\d+(?:\.\d+)?)(ms|s)$/i);
  if (!match) return null;

  const [, signToken, amountToken, unit] = match;
  const amount = Number(amountToken);
  const normalized = unit.toLowerCase() === 's' ? amount * 1000 : amount;
  const sign = signToken === '-' ? -1 : 1;
  return Math.round(normalized * sign);
}

function parseImpact(raw?: string): number {
  if (!raw) return 0.2;
  const parsed = Number.parseFloat(raw.replace('%', ''));
  if (!Number.isFinite(parsed)) return 0.2;
  return clamp(parsed / 100, 0.1, 1);
}

function buildSyntheticSample(trace: TraceEntry, baseline: number): MetricSample {
  const projection = TRACE_PROJECTION[trace.type];
  const parsedDelta = parseLatencyDelta(trace.latencyDelta);
  const impact = parseImpact(trace.impactPct);
  const rawDelta = parsedDelta ?? Math.round(trace.totalMs * projection.factor);
  const scaledMagnitude = Math.abs(rawDelta) * Math.max(impact, 0.35);

  let effectiveDelta = Math.round(scaledMagnitude * projection.factor);
  if (projection.floor < 0 || projection.cap < 0) {
    const lowered = -clamp(Math.abs(effectiveDelta || rawDelta), Math.abs(projection.cap), Math.abs(projection.floor));
    effectiveDelta = lowered;
  } else {
    effectiveDelta = clamp(effectiveDelta || projection.floor, projection.floor, projection.cap);
  }

  const nextValue = clamp(baseline + effectiveDelta, 5, 3000);
  const confidencePenalty = trace.origin === 'synthetic' ? 36 : 12;

  return {
    value: nextValue,
    timestamp: trace.timestamp.getTime(),
    source: trace.origin,
    confidence: clamp(Math.round(100 - confidencePenalty - impact * 12), 42, 94),
    traceId: trace.traceId,
  };
}

function appendSample(samples: MetricSample[], sample: MetricSample): MetricSample[] {
  const deduped = samples.filter((entry) => !(entry.timestamp === sample.timestamp && entry.traceId === sample.traceId));
  return [...deduped, sample].sort((a, b) => a.timestamp - b.timestamp).slice(-MAX_HISTORY);
}

export function useLiveMetrics() {
  // Internal source of truth — no re-renders during normal polling
  const lastSuccessRef = useRef<number | null>(null);
  // Reactive value exposed outside (only updates on successful fetch)
  const [lastSuccessSnapshot, setLastSuccessSnapshot] = useState<number | null>(null);

  // Rolling history of P95 samples for sparkline
  const historyRef = useRef<number[]>([]);
  const [history, setHistory] = useState<number[]>([]);
  const sampleHistoryRef = useRef<MetricSample[]>([]);
  const [sampleHistory, setSampleHistory] = useState<MetricSample[]>([]);

  // Previous snapshot for delta calculation
  const previousRef = useRef<MetricsSummary | null>(null);
  const [previous, setPrevious] = useState<MetricsSummary | null>(null);
  const [recentTraces, setRecentTraces] = useState<TraceEntry[]>(() => getRecentTraces());
  const serverDataRef = useRef<MetricsSummary | null>(null);



  useEffect(() => {
    return subscribeToTraces((trace) => {
      setRecentTraces(getRecentTraces());

      const baseline = sampleHistoryRef.current.at(-1)?.value ?? serverDataRef.current?.p95_ms ?? 42;
      const syntheticSample = buildSyntheticSample(trace, baseline);
      sampleHistoryRef.current = appendSample(sampleHistoryRef.current, syntheticSample);
      setSampleHistory([...sampleHistoryRef.current]);
      historyRef.current = sampleHistoryRef.current.map((sample) => sample.value);
      setHistory([...historyRef.current]);
    });
  }, []);

  const { preset } = useChaosMode();

  const query = useQuery({
    queryKey: ['metrics-summary', preset],
    queryFn: async () => fetchMetricsSummary(preset),
    staleTime: 10_000,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    gcTime: 60_000,
    retry: 1,
  });

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (query.data && query.dataUpdatedAt) {
      const data = query.data;
      const now = query.dataUpdatedAt;

      // Only process new fetches once
      if (lastSuccessRef.current === now) return;

      serverDataRef.current = data;
      lastSuccessRef.current = now;
      setLastSuccessSnapshot(now);

      // Update previous before rolling in new data
      if (previousRef.current !== null) {
        setPrevious(previousRef.current);
      }

      // Roll in new P95 value
      historyRef.current = [...historyRef.current, data.p95_ms].slice(-MAX_HISTORY);
      setHistory([...historyRef.current]);

      sampleHistoryRef.current = appendSample(sampleHistoryRef.current, {
        value: data.p95_ms,
        timestamp: now,
        source: 'real',
        confidence: DEFAULT_CONFIDENCE_REAL,
      });
      setSampleHistory([...sampleHistoryRef.current]);

      // Store current as next "previous"
      previousRef.current = data;
    }
  }, [query.data, query.dataUpdatedAt]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Derive combined status: backend signal + local latency threshold
  const latestSample = sampleHistory[sampleHistory.length - 1] ?? null;
  const effectiveP95 = latestSample?.value ?? query.data?.p95_ms ?? 0;
  const confidenceScore = latestSample?.confidence ?? (query.data ? DEFAULT_CONFIDENCE_REAL : 0);
  const confidenceLabel = latestSample?.source === 'synthetic' ? 'estimated' : 'verified';

  const status: SystemStatus = useMemo(() => {
    if (query.isLoading) return 'loading';
    if (!query.data || query.isError) return 'down';

    const { system_status, error_rate } = query.data;
    if (system_status === 'down') return 'down';
    if (effectiveP95 > LATENCY_DEGRADED_MS || error_rate > ERROR_RATE_DEGRADED) return 'degraded';
    if (effectiveP95 > LATENCY_WARNING_MS) return 'warning';
    return 'operational';
  }, [effectiveP95, query.data, query.isLoading, query.isError]);

  const latestTrace = recentTraces[0] ?? null;

   const baselineP95 = useMemo(() => {
     if (sampleHistory.length === 0) return null;
     const avg = sampleHistory.reduce((sum, sample) => sum + sample.value, 0) / sampleHistory.length;
     return Math.round(avg);
   }, [sampleHistory]);

  const currentTime = useCurrentTime(1000);
  const recoveryState = useMemo(() => {
    if (!latestTrace || !['forced_failure', 'latency_injection'].includes(latestTrace.type)) return 'closed' as const;
    const ageMs = currentTime - latestTrace.timestamp.getTime();
    if (ageMs < SYNTHETIC_WINDOW_MS) return 'open' as const;
    if (ageMs < RECOVERING_WINDOW_MS) return 'half_open' as const;
    return 'closed' as const;
  }, [latestTrace, currentTime]);

  const timeoutState = useMemo(() => {
    if (effectiveP95 > LATENCY_DEGRADED_MS) return 'visible' as const;
    if (effectiveP95 > LATENCY_WARNING_MS) return 'risk' as const;
    return 'within_budget' as const;
  }, [effectiveP95]);

  const displayLifecycle = useMemo(() => {
    if (!latestSample || latestSample.source === 'real') {
      return query.data?.system_lifecycle ?? 'NORMAL';
    }

    const ageMs = currentTime - latestSample.timestamp;
    if (ageMs < SYNTHETIC_WINDOW_MS && effectiveP95 > LATENCY_WARNING_MS) return 'DEGRADED';
    if (ageMs < RECOVERING_WINDOW_MS) return 'RECOVERING';
    return query.data?.system_lifecycle ?? 'NORMAL';
  }, [currentTime, effectiveP95, latestSample, query.data?.system_lifecycle]);

  const strategyProfile = useMemo(() => {
    const baseRetry = query.data?.retries_1h ?? 0;

    if (preset === 'failure') {
      return {
        retryBudget: Math.max(baseRetry, 6),
        cacheTtlSeconds: 180,
        activePath: 'fallback' as const,
        source: 'synthetic' as const,
      };
    }

    if (preset === 'stress') {
      return {
        retryBudget: Math.max(baseRetry, 3),
        cacheTtlSeconds: 90,
        activePath: (status === 'degraded' ? 'async' : 'sync') as 'sync' | 'async',
        source: 'synthetic' as const,
      };
    }

    if (preset === 'mild') {
      return {
        retryBudget: Math.max(baseRetry, 1),
        cacheTtlSeconds: 30,
        activePath: (query.data?.active_path ?? 'sync') as 'sync' | 'async' | 'fallback',
        source: 'synthetic' as const,
      };
    }

    return {
      retryBudget: baseRetry,
      cacheTtlSeconds: query.data?.cache_ttl_s ?? 0,
      activePath: (query.data?.active_path ?? 'sync') as 'sync' | 'async' | 'fallback',
      source: 'real' as const,
    };
  }, [preset, query.data?.active_path, query.data?.cache_ttl_s, query.data?.retries_1h, status]);

  return {
    ...query,
    status,
    history,
    sampleHistory,
    previous,
    lastSuccessAt: lastSuccessSnapshot,
    recentTraces,
    latestTrace,
    latestSample,
    effectiveP95,
    confidenceScore,
    confidenceLabel,
    baselineP95,
    recoveryState,
    timeoutState,
    displayLifecycle,
    strategyProfile,
  };
}
