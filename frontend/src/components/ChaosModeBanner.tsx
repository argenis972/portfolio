/**
 * ChaosModeBanner — Unified collapsible system alert banner.
 *
 * Rendering logic (two independent axes — do NOT conflate them):
 *   - `preset !== 'off'`                          → chaos is active
 *   - `status === 'degraded' || status === 'down'` → system is degraded
 *
 * Cases:
 *   A) chaos active + system degraded → unified collapsible banner (chaos label + system detail)
 *   B) chaos active + system OK       → unified collapsible banner (chaos label only)
 *   C) chaos off   + system degraded  → this component renders null; SystemStatusBanner handles it
 *   D) chaos off   + system OK        → nothing renders
 */
import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { useChaosMode } from '../hooks/useChaosMode';
import { useMetricsDisplay } from '../hooks/useMetricsDisplay';
import { useLanguage } from '../context/LanguageContext';

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

export default function ChaosModeBanner() {
  const { preset } = useChaosMode();
  const { t, metrics, data } = useMetricsDisplay();
  const { t: tLang } = useLanguage();
  const [expanded, setExpanded] = useState(false);

  // Case D — nothing to show
  if (preset === 'off') return null;

  // Chaos is active (Cases A & B)
  const { status, displayLifecycle, effectiveP95, strategyProfile } = metrics;
  const isSystemDegraded = status === 'degraded' || status === 'down';
  const lifecycle = displayLifecycle ?? data?.system_lifecycle ?? 'NORMAL';
  const showDetail = lifecycle !== 'STABLE' && lifecycle !== 'NORMAL';

  const cause = data?.last_incident && data.last_incident !== 'none'
    ? t(causeKey(data.last_incident))
    : t('banner.cause.backend');

  const degradedColor = status === 'down'
    ? 'bg-[var(--color-status-degraded-bg)] border-[var(--color-status-degraded-border)] text-[var(--color-status-degraded-text)]'
    : 'bg-[var(--color-status-recovering-bg)] border-[var(--color-status-recovering-border)] text-[var(--color-status-recovering-text)]';

  return (
    <AnimatePresence>
      <m.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: 'auto', opacity: 1 }}
        exit={{ height: 0, opacity: 0 }}
        className="w-full overflow-hidden sticky top-16 z-40"
      >
        {/* Collapsed pill — always visible when chaos is active */}
        <div className="bg-[var(--color-status-synthetic)]/90 backdrop-blur-sm border-y border-[var(--color-status-synthetic-border)] relative">
          <div className="max-w-6xl mx-auto px-4 py-2 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              {/* Pulsing dot */}
              <span className="relative flex h-2 w-2 flex-shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
              </span>
              <span className="text-[10px] sm:text-xs font-mono font-bold text-white uppercase tracking-[0.2em]">
                {tLang('chaos.banner.active')}
                {' · '}
                <span className="underline decoration-white/40">
                  {tLang('chaos.banner.mode', { p: preset.toUpperCase() })}
                </span>
              </span>
              {/* System status inline — only when degraded */}
              {isSystemDegraded && !expanded && (
                <span className="hidden sm:inline-flex items-center gap-1 ml-1 text-[9px] font-mono text-white/70 border border-white/20 rounded-full px-2 py-0.5">
                  <span className="text-status-error">⚠</span>
                  {t(`metrics.status.${status}`)}
                </span>
              )}
            </div>

            {/* Expand/collapse toggle */}
            <button
              onClick={() => setExpanded(v => !v)}
              aria-expanded={expanded}
              aria-label={expanded ? 'Collapse system detail' : 'Expand system detail'}
              className="flex items-center gap-1.5 text-xs font-mono font-bold text-white transition-colors py-1 px-3 rounded bg-white/10 hover:bg-white/20 focus-visible:outline-none border border-white/10"
            >
              <span>{expanded ? tLang('chaos.banner.collapse') || 'COLLAPSE' : tLang('chaos.banner.expand') || 'DETAILS'}</span>
              <m.span
                animate={{ rotate: expanded ? 180 : 0 }}
                transition={{ duration: 0.2 }}
                className="flex-shrink-0"
              >
                <ChevronDown className="w-4 h-4" />
              </m.span>
            </button>
          </div>

          {/* Scanline shimmer */}
          <div className="absolute inset-0 pointer-events-none bg-gradient-to-r from-transparent via-white/5 to-transparent w-1/4 h-full skew-x-[-20deg] animate-[shimmer_2s_infinite]" />
        </div>

        {/* Expanded detail — system status info */}
        <AnimatePresence>
          {expanded && isSystemDegraded && (
            <m.div
              key="detail"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className={`w-full border-b ${degradedColor} backdrop-blur-sm overflow-hidden`}
            >
              <div className="max-w-6xl mx-auto px-4 py-2.5 font-mono text-xs">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="text-sm">⚠️</span>
                    <span className={`font-bold uppercase tracking-widest ${status === 'down' ? 'text-status-error' : 'text-status-warn'}`}>
                      {t(`metrics.status.${status}`)}
                    </span>
                  </div>

                  {showDetail && (
                    <>
                      <span className="text-current/45">·</span>
                      <span className="text-current/80">
                        <span className="text-current/55">{t('banner.cause')}: </span>
                        {cause}
                      </span>
                    </>
                  )}

                  {showDetail && (
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
          {expanded && !isSystemDegraded && (
            <m.div
              key="detail-ok"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="w-full border-b border-[var(--color-status-synthetic-border)]/40 bg-[var(--color-status-synthetic)]/30 backdrop-blur-sm overflow-hidden"
            >
              <div className="max-w-6xl mx-auto px-4 py-2 font-mono text-[10px] text-white/60">
                {tLang('chaos.banner.hint')} · {t('metrics.status.operational').toLowerCase()}
              </div>
            </m.div>
          )}
        </AnimatePresence>
      </m.div>
    </AnimatePresence>
  );
}
