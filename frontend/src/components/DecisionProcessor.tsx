/**
 * DecisionProcessor — Invisible background component that handles
 * systematic decisions and system-wide assertions.
 */
import { useLiveMetrics } from '../hooks/useLiveMetrics';
import { useDecisionEngine } from '../hooks/useDecisionEngine';

export default function DecisionProcessor() {
  const { data, effectiveP95, displayLifecycle, strategyProfile } = useLiveMetrics();
  const effectiveData = data
    ? {
        ...data,
        p95_ms: effectiveP95,
        system_lifecycle: displayLifecycle,
        active_path: strategyProfile.activePath,
      }
    : undefined;

  // The hook handles comparison, hysteresis, and log emission
  useDecisionEngine(effectiveData);

  return null; // Invisible component
}
