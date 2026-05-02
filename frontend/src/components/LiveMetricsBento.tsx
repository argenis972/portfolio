import React from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { useLanguage } from '../context/LanguageContext';
import { useMetricsDisplay } from '../hooks/useMetricsDisplay';
import { useChaosMode } from '../hooks/useChaosMode';
import { Tile, TileSkeleton } from './ui/Tile';
import MetricsSparkline from './ui/MetricsSparkline';



export default function LiveMetricsBento() {
  const displayContext = useMetricsDisplay();
  const { preset } = useChaosMode();
  const { isLoading, t } = displayContext;

  if (isLoading || !displayContext.data) {
    return (
      <section id="metrics" className="px-4 max-w-6xl mx-auto py-12">
        <div className="mb-6">
          <div className="h-5 w-48 rounded bg-app-border animate-pulse mb-2" />
          <div className="h-4 w-72 rounded bg-app-border animate-pulse opacity-60" />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {[0, 1, 2, 3, 4, 5].map((i) => <TileSkeleton key={i} index={i} />)}
        </div>
      </section>
    );
  }

  const {
    data,
    errorIsElevated,
    errorRateColor,
    errorNumberColor,
    hasIncident,
    incidentDot,
    incidentText,
    latencyDelta,
    baselineDelta,
    latestEventLabel,
    latestEventAgoSeconds,
    confidenceTone,
    metrics: {
      sampleHistory,
      latestSample,
      effectiveP95,
      confidenceScore,
      confidenceLabel,
      baselineP95,
      latestTrace,
      recentTraces,
      displayLifecycle,
      strategyProfile,
    }
  } = displayContext;

  const activePath = strategyProfile.activePath;

  return (
    <section id="metrics" aria-label="Live system metrics" className="px-4 max-w-6xl mx-auto py-12">
      <div className="mb-6 text-center lg:text-left">
        <h2 className="text-xs font-mono uppercase tracking-[0.2em] text-app-primary mb-1">
          {t('metrics.system_status').toUpperCase()}
        </h2>
        <p className="text-xs font-mono text-app-muted max-w-lg mx-auto lg:mx-0">
          {t('metrics.section_subtitle')}
        </p>
        <div className="mt-3 flex flex-wrap items-center justify-center lg:justify-start gap-2 text-[10px] font-mono">
          <span className="text-app-muted/80">
            Session includes ~{100 - confidenceScore}% synthetic data during active chaos events.
          </span>
          <span className={`ml-1 rounded-full border px-2 py-0.5 ${confidenceTone}`}>
            {t(`metrics.confidence.${confidenceLabel}`)}
          </span>
          <span className="rounded-full border border-app-border/40 bg-app-surface/30 px-2 py-1 text-app-muted ml-auto">
            {t(`metrics.lifecycle.${displayLifecycle}`)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <Tile index={0} label={t('metrics.latency')} alertState={preset !== 'off' ? 'chaos' : 'none'}>
          <div className="mt-1 flex flex-col gap-3">
            <div className="flex items-end justify-between gap-4">
              <div className="flex items-end gap-1">
                <span className="font-mono text-2xl font-bold text-app-text">{effectiveP95}</span>
                <span className="text-sm font-normal text-app-muted mb-1">ms</span>
              </div>
              {baselineP95 !== null && <span className="text-[10px] font-mono text-app-muted">baseline {baselineP95}ms</span>}
            </div>
            {sampleHistory.length >= 2 ? (
              <div className="rounded-xl border border-app-border/40 bg-app-surface/30 px-2 py-2 overflow-hidden">
                <MetricsSparkline samples={sampleHistory} traces={recentTraces} width={248} height={72} compact />
              </div>
            ) : (
              <div className="rounded-xl border border-app-border/40 bg-app-surface/30 px-2 py-2 overflow-hidden">
                <MetricsSparkline samples={[]} traces={recentTraces} width={248} height={72} compact />
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {latencyDelta !== null && (
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-mono ${latencyDelta > 0 ? 'bg-status-error-soft text-status-error' : 'bg-status-ok-soft text-status-ok'}`}>
                  {t('metrics.delta.previous')} {latencyDelta > 0 ? '+' : ''}{latencyDelta}ms
                </span>
              )}
              {baselineDelta !== null && (
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-mono ${baselineDelta > 0 ? 'bg-status-warn-soft text-status-warn' : 'bg-status-ok-soft text-status-ok'}`}>
                  {t('metrics.delta.baseline')} {baselineDelta > 0 ? '+' : ''}{baselineDelta}ms
                </span>
              )}
            </div>
          </div>
          <span className={`text-xs font-mono px-2 py-0.5 rounded-full w-fit ${effectiveP95 <= 60 ? 'bg-status-ok-soft text-status-ok' : 'bg-status-warn-soft text-status-warn'}`}>
            {effectiveP95 <= 60 ? t('metrics.health.healthy') : t('metrics.health.warning')}
          </span>
        </Tile>

        <Tile index={1} label={t('metrics.error_rate')} alertState={preset !== 'off' ? 'chaos' : 'none'}>
           <div className="flex items-center gap-2 mt-1">
             <AnimatePresence>
               {errorIsElevated && (
                 <m.span
                   initial={{ opacity: 0, scale: 0.5 }}
                   animate={{ opacity: 1, scale: 1 }}
                   exit={{ opacity: 0, scale: 0.5 }}
                   className="text-status-error text-xl drop-shadow-[0_0_8px_rgba(239,68,68,0.4)]"
                 >
                   ⚠
                 </m.span>
               )}
             </AnimatePresence>
             <m.span 
               animate={errorIsElevated ? { color: '#f87171' } : { color: 'inherit' }}
               className={`font-mono text-2xl font-bold ${errorNumberColor}`}
             >
               {data.error_rate_pct}
             </m.span>
           </div>
           <div className="text-[9px] text-status-ok/80 mt-1">
             {t('metrics.error_rate_slo_context')}
           </div>
           <m.div
             animate={errorIsElevated ? { scale: [1, 1.05, 1], transition: { repeat: Infinity, duration: 2 } } : {}}
             className={`text-xs font-mono px-2 py-0.5 rounded-full w-fit ${errorRateColor}`}
           >
             {t(`metrics.health.${data.error_rate_status}`)}
           </m.div>
        </Tile>

        <Tile index={2} label={t('metrics.requests_24h')}>
          <span className="font-mono text-2xl font-bold text-app-text mt-1">{data.requests_24h.toLocaleString('en-US')}</span>
          <UpdatedAgo timestamp={data.timestamp} />
        </Tile>

        <Tile index={3} label={t('metrics.retries_1h')}>
          <div className="flex items-center gap-2 mt-1">
            {strategyProfile.retryBudget > 5 && <span className="text-status-error text-lg">⚠</span>}
            <span className={`font-mono text-2xl font-bold ${strategyProfile.retryBudget > 10 ? 'text-status-error' : strategyProfile.retryBudget > 0 ? 'text-status-warn' : 'text-app-text'}`}>
              {strategyProfile.retryBudget}
            </span>
          </div>
          <span className={`text-xs font-mono px-2 py-0.5 rounded-full w-fit ${strategyProfile.retryBudget > 10 ? 'bg-status-error-soft text-status-error' : strategyProfile.retryBudget > 0 ? 'bg-status-warn-soft text-status-warn' : 'bg-status-ok-soft text-status-ok'}`}>
            {strategyProfile.retryBudget > 10 ? t('metrics.health.investigating') : strategyProfile.retryBudget > 0 ? t('metrics.health.warning') : t('metrics.health.stable')}
          </span>
          <span className="text-[10px] font-mono text-app-muted">{t('metrics.strategy.retry')} {strategyProfile.source === 'synthetic' ? t('metrics.strategy.synthetic') : t('metrics.strategy.backend')}</span>
        </Tile>

        <Tile index={4} label={t('metrics.last_incident')}>
          <div className="flex items-center gap-2 mt-1">
            <span className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${incidentDot}`} />
            <span className={`font-mono text-sm font-bold ${incidentText} truncate`}>
              {hasIncident ? t(`metrics.incident.${data.last_incident}`) : t('metrics.incident.none')}
            </span>
          </div>
          {hasIncident && <span className="text-xs text-app-muted font-mono">{data.last_incident_ago}</span>}
        </Tile>
      </div>

      <m.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.25 }}
        className="mt-4 grid gap-3 lg:grid-cols-[1.4fr_1fr]"
      >
        <div className="glass rounded-2xl border border-app-border p-5 overflow-hidden">
          <div className="mb-3 flex items-center justify-between gap-3">
            <span className="text-xs font-mono uppercase tracking-widest text-app-muted">{t('metrics.telemetry.title')}</span>
            <span className="text-[10px] font-mono text-app-muted">{t('metrics.telemetry.p95_label')}</span>
          </div>
          <div className="overflow-x-auto">
            <div className="min-w-[520px]">
              <MetricsSparkline samples={sampleHistory} traces={recentTraces} width={560} height={120} />
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-3 text-[10px] font-mono text-app-muted">
            <span>{t('metrics.legend.healthy')}</span>
            <span>{t('metrics.legend.warning')}</span>
            <span>{t('metrics.legend.degraded')}</span>
            <span>{t('metrics.legend.real')}</span>
            <span>{t('metrics.legend.synthetic')}</span>
          </div>
        </div>

        <div className="glass rounded-2xl border border-app-border p-5">
          <div className="mb-4 text-xs font-mono uppercase tracking-widest text-app-muted">{t('metrics.system_model.title')}</div>
          <div className="grid gap-3">
            {/* Execution paths */}
            <div className="rounded-xl border border-app-border/50 bg-app-surface/30 p-3 space-y-2">
              <div className="text-[10px] font-mono uppercase tracking-widest text-app-muted mb-1">{t('metrics.system_model.paths')}</div>
              {[
                { pathKey: 'sync',     labelKey: 'metrics.system_model.sync',     color: 'text-status-ok' },
                { pathKey: 'async',    labelKey: 'metrics.system_model.async',    color: 'text-status-warn' },
                { pathKey: 'fallback', labelKey: 'metrics.system_model.fallback', color: 'text-status-info' },
              ].map(({ pathKey, labelKey, color }) => {
                const active = activePath === pathKey;
                return (
                  <div key={pathKey} className="flex items-center justify-between">
                    <span className={`text-xs font-mono ${active ? color : 'text-app-muted/50'}`}>{t(labelKey)}</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${active ? `${color} border-current/20 bg-current/5` : 'text-app-muted/30 border-app-border/20'}`}>
                      {active ? 'ACTIVE' : 'standby'}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Lifecycle state */}
            <div className="rounded-xl border border-app-border/50 bg-app-surface/30 p-3">
              <div className="text-[10px] font-mono uppercase tracking-widest text-app-muted">{t('metrics.system_model.lifecycle')}</div>
              <div className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-mono ${
                displayLifecycle === 'DEGRADED'   ? 'bg-status-error-soft text-status-error' :
                displayLifecycle === 'RECOVERING' ? 'bg-status-warn-soft text-status-warn' :
                displayLifecycle === 'STABLE'     ? 'bg-status-ok-soft text-status-ok' :
                'bg-status-ok-soft text-status-ok'
              }`}>
                {displayLifecycle}
              </div>
              <div className="mt-2 text-[10px] font-mono text-app-muted">{t(`metrics.origin.${strategyProfile.source}`)}</div>
            </div>

            <div className="rounded-xl border border-app-border/50 bg-app-surface/30 p-3">
              <div className="text-[10px] font-mono uppercase tracking-widest text-app-muted">{t('metrics.strategy.title')}</div>
              <div className="mt-2 grid gap-2 text-xs font-mono text-app-text">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-app-muted">{t('metrics.strategy.retry')}</span>
                  <span>{strategyProfile.retryBudget}x</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-app-muted">{t('metrics.strategy.cache')}</span>
                  <span>TTL {strategyProfile.cacheTtlSeconds}s</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-app-muted">{t('metrics.strategy.source')}</span>
                  <span>{t(`metrics.origin.${strategyProfile.source}`)}</span>
                </div>
              </div>
            </div>

            {/* Latest event */}
            <div className="rounded-xl border border-app-border/50 bg-app-surface/30 p-3">
              <div className="text-[10px] font-mono uppercase tracking-widest text-app-muted">{t('metrics.failure_model.latest_event')}</div>
              <div className="mt-2 text-sm font-mono text-app-text break-all">{latestEventLabel}</div>
              {latestTrace && (
                <div className="mt-2 text-[10px] font-mono text-app-muted space-y-1">
                  <div>request_id={latestTrace.requestId}</div>
                  <div>trace_id={latestTrace.traceId}</div>
                  {latestEventAgoSeconds !== null && <div>{t('metrics.updated_ago', { s: latestEventAgoSeconds })}</div>}
                </div>
              )}
            </div>
          </div>
        </div>
      </m.div>

      <div className="flex justify-end mt-2 pr-1">
        <a
          href="https://api.argenisbackend.com/api/v1/metrics/summary"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] font-mono text-app-muted hover:text-app-primary transition-colors duration-200 flex items-center gap-1"
          title={t('metrics.source_tooltip')}
        >
          {t('metrics.view_raw')}
          <span className="opacity-60">↗</span>
        </a>
      </div>
    </section>
  );
}
