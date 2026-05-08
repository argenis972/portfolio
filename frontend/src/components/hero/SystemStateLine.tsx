import React from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { type SystemStatus } from '../../hooks/useLiveMetrics';

interface SystemStateLineProps {
  status: SystemStatus;
  effectiveP95: number;
  recoveryState: string;
  lastIncident?: string;
}

export const SystemStateLine = React.memo(({ status, effectiveP95, recoveryState, lastIncident }: SystemStateLineProps) => {
  const { t } = useLanguage();

  const line = React.useMemo(() => {
    if (status === 'loading') return t('metrics.status.loading');

    if (status === 'down') {
      const cbState = t('hero.status.circuit_breaker') + ' ' + recoveryState.toUpperCase();
      const fallback = t('hero.status.fallback_engaged');
      return `DOWN · Fail-silent active — ${cbState} · ${fallback}`;
    }

    if (status === 'degraded') {
      const cause = lastIncident && lastIncident !== 'none'
        ? t(`metrics.incident.${lastIncident}`, { defaultValue: lastIncident })
        : 'anomaly detected';
      const cbState = recoveryState === 'open'
        ? t('hero.status.circuit_breaker') + ' OPEN'
        : t('hero.status.circuit_breaker') + ' ' + recoveryState.toUpperCase();
      const p95Text = t('hero.status.p95_at', { n: effectiveP95 });
      const fallback = t('hero.status.fallback_engaged');
      return `DEGRADED · ${cause} — ${p95Text}, ${cbState}, ${fallback}`;
    }

    if (status === 'warning') {
      const p95Text = t('hero.status.p95_at', { n: effectiveP95 });
      const msg = t('hero.status.threshold_exceeded');
      return `WARNING · ${p95Text} — ${msg}`;
    }

    if (status === 'operational') {
      if (recoveryState === 'half_open') {
        const cbState = t('hero.status.circuit_breaker') + ' HALF-OPEN';
        const msg = t('hero.status.recovering_testing', { n: effectiveP95 });
        return `RECOVERING · ${cbState} · ${msg}`;
      }
      const msg = t('hero.status.nominal');
      const p95Text = t('hero.status.p95_at', { n: effectiveP95 });
      return `OPERATIONAL · ${msg} · ${p95Text}`;
    }

    return t('hero.differentiator');
  }, [status, effectiveP95, recoveryState, lastIncident, t]);

  const colorClass =
    status === 'down' ? 'text-status-error' :
    status === 'degraded' ? 'text-status-error' :
    status === 'warning' ? 'text-status-warn' :
    recoveryState === 'half_open' ? 'text-status-warn' :
    'text-app-primary/80';

  return (
    <p className={`mt-3 text-sm font-mono italic max-w-2xl mx-auto md:mx-0 transition-colors duration-500 ${colorClass}`}>
      {line}
    </p>
  );
});

export default SystemStateLine;
