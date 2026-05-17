/**
 * SystemStatusBanner — Global system narrative strip.
 *
 * This banner follows a structured SRE-first format:
 * ⚠️ [STATUS] · Cause: [Trigger] · Impact: [Delta] · Status: [Lifecycle]
 *
 * Appears below the Navbar only when system_status is not 'operational'.
 * Never shown when lifecycle === 'NORMAL'.
 */
import React from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { useMetricsDisplay } from '../hooks/useMetricsDisplay';
import { useChaosMode } from '../hooks/useChaosMode';


function causeKey(lastIncident: string): string {
  const map: Record<string, string> = {
    traffic_spike:     'banner.cause.traffic_spike',
    forced_failure:    'banner.cause.forced_failure',
    cache_stress:      'banner.cause.cache_stress',
    queue_drain:       'banner.cause.queue_drain',
    manual_retry:      'banner.cause.manual_retry',
    latency_injection: 'banner.cause.latency_injection',
  };
  return map[lastIncident] ?? 'banner.cause.backend';
}

const SystemStatusBanner = React.memo(() => {
  const { preset } = useChaosMode();
  const { t, metrics, data } = useMetricsDisplay();

  if (!data || preset !== 'off') return null;

  const { status, displayLifecycle, effectiveP95, strategyProfile } = metrics;
  const isVisible = status === 'degraded' || status === 'down';

  const outerColor =
    status === 'down'
      ? 'bg-[var(--color-status-degraded-bg)] border-[var(--color-status-degraded-border)] text-[var(--color-status-degraded-text)]'
      : 'bg-[var(--color-status-recovering-bg)] border-[var(--color-status-recovering-border)] text-[var(--color-status-recovering-text)]';

  const lifecycle     = displayLifecycle ?? data.system_lifecycle ?? 'NORMAL';

  const cause = data.last_incident && data.last_incident !== 'none'
    ? t(causeKey(data.last_incident))
    : t('banner.cause.backend');

  const showCause   = lifecycle !== 'STABLE' && lifecycle !== 'NORMAL';
  const showImpact  = lifecycle !== 'STABLE' && lifecycle !== 'NORMAL';

  return (
    <AnimatePresence>
      {isVisible && (
        <m.div
          key="status-banner"
          initial={{ opacity: 0, height: 0, y: -10 }}
          animate={{ opacity: 1, height: 'auto', y: 0 }}
          exit={{ opacity: 0, height: 0, y: -10 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          style={{ overflow: 'hidden' }}
          className={`w-full border-b ${outerColor} backdrop-blur-sm overflow-hidden sticky top-16 z-40`}
        >
          <div className="max-w-6xl mx-auto px-4 py-2.5 font-mono text-xs">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <span className="text-sm">⚠️</span>
                <span className={`font-bold uppercase tracking-widest ${status === 'down' ? 'text-status-error' : 'text-status-warn'}`}>
                  {t(`metrics.status.${status}`)}
                </span>
              </div>

              {showCause && (
                <>
                  <span className="text-current/45">·</span>
                  <span className="text-current/80">
                    <span className="text-current/55">{t('banner.cause')}: </span>
                    {cause}
                  </span>
                </>
              )}

              {showImpact && (
                <>
                  <span className="text-current/45">·</span>
                  <span className="text-current/80">
                    <span className="text-current/55">{t('banner.impact')}: </span>
                    +{effectiveP95}ms{strategyProfile.retryBudget > 0 ? `, ${t('banner.impact.retries_active')}` : ''}
                  </span>
                </>
              )}

              <span className="text-current/45">·</span>
              <span className="text-current/80">
                <span className="text-current/55">{t('banner.status')}: </span>
                <span className="capitalize">{t(`metrics.lifecycle.${lifecycle}`).toLowerCase()}</span>
              </span>
            </div>
          </div>
        </m.div>
      )}
    </AnimatePresence>
  );
});

export default SystemStatusBanner;
