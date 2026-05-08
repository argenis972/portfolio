/**
 * useDecisionEngine — The reactive "brain" of the observability stack.
 *
 * It monitors live metrics and issues DECISION logs when thresholds are crossed.
 * Features:
 *   - Hysteresis (anti-flapping): ON and OFF thresholds.
 *   - Priority: ERROR spikes suppress LATENCY decisions.
 *   - Edge-triggered: Only emits logs on transitions.
 */
import { useEffect, useRef } from 'react';
import { useLog } from './useLog';
import { type MetricsSummary } from '../api/types';

// Engineering thresholds with Hysteresis
const ERROR_SPIKE_ON  = 0.045;
const ERROR_SPIKE_OFF = 0.035;

const LATENCY_ON_MS   = 100;
const LATENCY_OFF_MS  = 70;

const SUPPRESS_LATENCY_AFTER_ERROR_MS = 30_000;

export function useDecisionEngine(data: MetricsSummary | undefined) {
  const { addEntry } = useLog();

  // Track state of each trigger to enable edge-triggering and hysteresis
  const errorActive = useRef(false);
  const latencyActive = useRef(false);

  // Lifecycle state tracking for logs
  const lastLifecycle = useRef<string | null>(null);

  // Decision suppression timers
  const latencySuppressedUntil = useRef(0);

  useEffect(() => {
    if (!data) return;

    const { error_rate, p95_ms, system_lifecycle, active_path } = data;
    const now = Date.now();

    // 1. Lifecycle State Machine Transitions
    if (lastLifecycle.current !== null && lastLifecycle.current !== system_lifecycle) {
      addEntry(
        'DECISION',
        `state_transition previous=${lastLifecycle.current} current=${system_lifecycle} active_path=${active_path}`
      );
    }
    lastLifecycle.current = system_lifecycle;

    // 2. Error Rate Trigger (Priority 1)
    if (!errorActive.current && error_rate >= ERROR_SPIKE_ON) {
      errorActive.current = true;
      addEntry(
        'DECISION',
        `error_spike_detected value=${(error_rate * 100).toFixed(2)}% threshold=${(ERROR_SPIKE_ON * 100).toFixed(2)}% status=ENGAGED action=suppressing_latency_decisions`
      );
      // Suppress latency decisions when a major error spike is happening
      latencySuppressedUntil.current = now + SUPPRESS_LATENCY_AFTER_ERROR_MS;
    } else if (errorActive.current && error_rate <= ERROR_SPIKE_OFF) {
      errorActive.current = false;
      addEntry(
        'DECISION',
        `error_spike_resolved value=${(error_rate * 100).toFixed(2)}% threshold=${(ERROR_SPIKE_OFF * 100).toFixed(2)}% status=IDLE`
      );
    }

    // 3. Latency Trigger (Priority 2)
    const isLatencySuppressed = now < latencySuppressedUntil.current;

    if (!latencyActive.current && p95_ms >= LATENCY_ON_MS) {
      latencyActive.current = true;
      if (!isLatencySuppressed) {
        addEntry(
          'DECISION',
          `latency_threshold_breached value=${p95_ms}ms threshold=${LATENCY_ON_MS}ms status=ENGAGED action=monitoring_p99`
        );
      } else {
        // Log that we saw it but suppressed it due to hierarchy
        addEntry(
          'INFO',
          `latency_high_detected value=${p95_ms}ms status=SUPPRESSED reason=error_spike_priority`
        );
      }
    } else if (latencyActive.current && p95_ms <= LATENCY_OFF_MS) {
      latencyActive.current = false;
      if (!isLatencySuppressed) {
        addEntry(
          'DECISION',
          `latency_stabilized value=${p95_ms}ms threshold=${LATENCY_OFF_MS}ms status=IDLE`
        );
      }
    }

  }, [data, addEntry]);
}
