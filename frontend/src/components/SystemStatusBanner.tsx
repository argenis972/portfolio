/**
 * SystemStatusBanner — Global system narrative strip.
 *
 * Epic 1: Multi-service status row (API / Worker / Cache).
 * Round-2: System lifecycle badge (DEGRADED → RECOVERING → STABLE).
 *
 * Appears below the Navbar only when system_status is not 'operational'.
 * Never shown when lifecycle === 'NORMAL'.
 */
import React from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { useMetricsDisplay } from '../hooks/useMetricsDisplay';

const LIFECYCLE_CONFIG: Record<
  string,
  { label: string; dot: string; labelClass: string }
> = {
  DEGRADED:   { label: 'DEGRADED',   dot: 'bg-[var(--color-status-degraded)] animate-pulse', labelClass: 'text-[var(--color-status-degraded-text)]' },
  RECOVERING: { label: 'RECOVERING', dot: 'bg-[var(--color-status-recovering)] animate-pulse', labelClass: 'text-[var(--color-status-recovering-text)]' },
  STABLE:     { label: 'STABLE',     dot: 'bg-[var(--color-status-stable)]',             labelClass: 'text-[var(--color-status-ok-text)]' },
  NORMAL:     { label: 'NORMAL',     dot: 'bg-[var(--color-status-stable)]',             labelClass: 'text-[var(--color-status-ok-text)]' },
};

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
  const { t, metrics, data } = useMetricsDisplay();
  
  if (!data) return null;

  const { status, displayLifecycle, effectiveP95, strategyProfile } = metrics;
  const isVisible = status === 'degraded' || status === 'down';

  const outerColor =
    status === 'down'
      ? 'bg-[var(--color-status-degraded-bg)] border-[var(--color-status-degraded-border)] text-[var(--color-status-degraded-text)]'
      : 'bg-[var(--color-status-recovering-bg)] border-[var(--color-status-recovering-border)] text-[var(--color-status-recovering-text)]';

  const lifecycle     = displayLifecycle ?? data.system_lifecycle ?? 'NORMAL';
  const lifecycleCfg  = LIFECYCLE_CONFIG[lifecycle] ?? LIFECYCLE_CONFIG['NORMAL'];

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
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3 }}
          className={`w-full border-b ${outerColor} backdrop-blur-sm overflow-hidden sticky top-16 z-40`}
        >
          <div className="max-w-6xl mx-auto px-4 py-2.5 font-mono text-xs">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <span className={`w-2 h-2 rounded-full ${lifecycleCfg.dot}`} />
                <span className={`font-bold uppercase tracking-widest ${lifecycleCfg.labelClass}`}>
                  {lifecycle}
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
                    +{effectiveP95}ms latency{strategyProfile.retryBudget > 0 ? ', retries active' : ''}
                  </span>
                </>
              )}
            </div>
          </div>
        </m.div>
      )}
    </AnimatePresence>
  );
});

export default SystemStatusBanner;

