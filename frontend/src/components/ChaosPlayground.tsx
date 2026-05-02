/**
 * ChaosPlayground — Redesigned as an operational control panel.
 *
 * Three action cards (Spike / Failure / Cache Stress).
 * Active Incidents panel with TTL tracking.
 * Terminal-style log with request_id and structured format.
 * Writes events to shared LogContext.
 */
import { useState, useCallback, useRef } from 'react';
import { m } from 'framer-motion';
import { useLanguage } from '../context/LanguageContext';
import { useLog } from '../hooks/useLog';
import { useChaosMode, type ChaosPreset } from '../hooks/useChaosMode';
import { useChaosActions, type TerminalEntry } from '../hooks/useChaosActions';
import { useCurrentTime } from '../hooks/useCurrentTime';
import ChaosActionCard from './chaos/ChaosActionCard';
import ChaosTerminal from './chaos/ChaosTerminal';

// Shared trace store moved to src/services/TraceEmitter.ts

// ─── ActionCard extracted → src/components/chaos/ChaosActionCard.tsx ──────────

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function ChaosPlayground() {
  const { t } = useLanguage();
  const { addEntry, incidents, addIncident } = useLog();
  const { preset, setPreset } = useChaosMode();

  // Terminal log (local, lightweight)
  const [terminal, setTerminal] = useState<TerminalEntry[]>([]);
  const termIdRef = useRef(0);

  const addTerminalEntry = useCallback((level: TerminalEntry['level'], message: string, requestId: string) => {
    const entry: TerminalEntry = {
      id: ++termIdRef.current,
      level,
      message,
      requestId,
      timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false }),
    };
    setTerminal((prev) => [entry, ...prev].slice(0, 12));
  }, []);

  const {
    handleDrain, handleRetry, handleLatency,
    drainLoading, retryLoading, latencyLoading,
    drainCooldown, retryCooldown, latencyCooldown,
  } = useChaosActions({
    addTerminalEntry,
    addEntry,
    addIncident,
  });

  const now = useCurrentTime(1000);

  const activeIncidents = incidents.filter((i) => now - i.startedAt < i.ttl);
  const resolvedIncidents = incidents.filter((i) => now - i.startedAt >= i.ttl);

  return (
    <section id="chaos" aria-label="Chaos Playground" className="px-4 max-w-6xl mx-auto py-12">
      <m.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.15 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div className="mb-2">
          <h2 className="text-xs font-mono uppercase tracking-[0.2em] text-app-primary mb-1">
            {t('chaos.title')}
          </h2>
          <p className="text-sm text-app-muted max-w-lg">{t('chaos.subtitle')}</p>
          <p className="text-xs font-mono text-app-primary/70 mt-1">{t('chaos.note')}</p>
        </div>

        {/* Chaos Preset Selector */}
        <div className="glass rounded-xl p-4 border border-app-border mt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <h3 className="text-xs font-mono font-bold text-app-text uppercase tracking-widest flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${preset !== 'off' ? 'bg-violet-400' : 'bg-status-ok'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${preset !== 'off' ? 'bg-violet-500' : 'bg-status-ok'}`}></span>
                </span>
                {t('chaos.presets.title')}
              </h3>
              <p className="text-[10px] font-mono text-app-muted">
                {preset === 'off' ? t('chaos.presets.desc_off') : t('chaos.presets.desc_active', { p: preset.toUpperCase() })}
              </p>
            </div>

            <div className="flex items-center gap-1 bg-app-surface p-1 rounded-lg border border-app-border">
              {(['off', 'mild', 'stress', 'failure'] as ChaosPreset[]).map((p) => (
                <button
                  key={p}
                  onClick={() => {
                    setPreset(p);
                    addEntry('DECISION', `manual_override chaos_preset=${p.toUpperCase()} status=APPLIED`);
                  }}
                  className={`px-3 py-1.5 rounded-md text-[10px] font-mono font-bold transition-all duration-200 ${
                    preset === p
                      ? 'bg-violet-500 text-white shadow-lg shadow-violet-500/20'
                      : 'text-app-muted hover:text-app-text hover:bg-app-surface-hover'
                  }`}
                >
                  {p.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          
          {preset !== 'off' && (
            <m.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-3 pt-3 border-t border-app-border/40 text-[10px] font-mono text-[var(--color-status-synthetic)] italic"
            >
              {preset === 'mild' && t('chaos.presets.mild_effect')}
              {preset === 'stress' && t('chaos.presets.stress_effect')}
              {preset === 'failure' && t('chaos.presets.failure_effect')}
            </m.div>
          )}
        </div>

        {/* Action cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
          <ChaosActionCard
            icon="🌬️"
            titleKey="chaos.action.drain.title"
            descKey="chaos.action.drain.desc"
            accentClass="text-status-ok font-black"
            borderClass="border-status-ok/50"
            hoverClass="bg-status-ok text-white shadow-lg shadow-status-ok/20 hover:brightness-110"
            loading={drainLoading}
            cooldown={drainCooldown}
            loadingKey="chaos.action.drain.running"
            actionKey="chaos.action.drain.action"
            disabled={drainLoading || drainCooldown > 0}
            onClick={handleDrain}
          />
          <ChaosActionCard
            icon="⏳"
            titleKey="chaos.action.latency.title"
            descKey="chaos.action.latency.desc"
            accentClass="text-status-warn font-black"
            borderClass="border-status-warn/50"
            hoverClass="bg-status-warn text-white shadow-lg shadow-status-warn/20 hover:brightness-110"
            loading={latencyLoading}
            cooldown={latencyCooldown}
            loadingKey="chaos.action.latency.running"
            actionKey="chaos.action.latency.action"
            disabled={latencyLoading || latencyCooldown > 0}
            onClick={handleLatency}
          />
          <ChaosActionCard
            icon="🔄"
            titleKey="chaos.action.retry.title"
            descKey="chaos.action.retry.desc"
            accentClass="text-status-info font-black"
            borderClass="border-status-info/50"
            hoverClass="bg-status-info text-white shadow-lg shadow-status-info/20 hover:brightness-110"
            loading={retryLoading}
            cooldown={retryCooldown}
            loadingKey="chaos.action.retry.running"
            actionKey="chaos.action.retry.action"
            disabled={retryLoading || retryCooldown > 0}
            onClick={handleRetry}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
          {/* Active Incidents panel */}
          <div className="glass rounded-xl p-4 border border-app-border">
            <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-mono uppercase tracking-widest text-app-muted">{t('chaos.incidents.history')}</span>
              {activeIncidents.length > 0 && (
                <span className="w-2 h-2 rounded-full bg-status-warn animate-pulse" />
              )}
            </div>
            
            {incidents.length === 0 ? (
              <p className="text-xs font-mono text-app-muted/50">{t('chaos.incidents.empty')}</p>
            ) : (
              <div className="space-y-4">
                {/* Active/Mitigating */}
                {activeIncidents.length > 0 && (
                  <div className="space-y-2">
                    {activeIncidents.map((inc) => {
                      const elapsed = now - inc.startedAt;
                      const remaining = Math.max(0, Math.ceil((inc.ttl - elapsed) / 1000));
                      const isInvestigating = elapsed < 5000;
                      
                      return (
                        <div key={inc.id} className="flex flex-col gap-1 border-l-2 border-status-warn/30 pl-3">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-mono text-status-warn font-bold uppercase tracking-wider">
                              {t(inc.labelKey)}
                            </span>
                            <span className="text-[10px] font-mono text-app-muted opacity-60">
                              {remaining}s
                            </span>
                          </div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${
                              isInvestigating 
                                ? 'bg-status-warn-soft border-status-warn/20 text-status-warn' 
                                : 'bg-status-ok-soft border-status-ok/20 text-status-ok'
                            }`}>
                              {isInvestigating ? 'INVESTIGATING' : 'MITIGATING'}
                            </span>
                            {inc.origin && (
                              <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${inc.origin === 'synthetic' ? 'bg-[var(--color-status-synthetic-bg)] border-[var(--color-status-synthetic-border)] text-[var(--color-status-synthetic)]' : 'bg-status-ok-soft border-status-ok/20 text-status-ok'}`}>
                                {inc.origin}
                              </span>
                            )}
                            {inc.impactPct && (
                              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-status-error/20 bg-status-error-soft text-status-error">
                                impact {inc.impactPct}
                              </span>
                            )}
                            {inc.durationMs !== undefined && (
                              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-app-border/30 bg-app-surface/40 text-app-muted">
                                duration {inc.durationMs}ms
                              </span>
                            )}
                            <div className="flex-grow h-[2px] bg-app-border/30 rounded-full overflow-hidden">
                              <m.div 
                                initial={{ width: '100%' }}
                                animate={{ width: `${(remaining / (inc.ttl/1000)) * 100}%` }}
                                className="h-full bg-status-warn/40"
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Resolved */}
                {resolvedIncidents.length > 0 && (
                  <div className="space-y-1 pt-2 border-t border-app-border/20">
                    <span className="text-[10px] font-mono uppercase tracking-widest text-app-muted/60 block mb-2">{t('chaos.incidents.resolved_section')}</span>
                    {resolvedIncidents.slice(0, 3).map((inc) => (
                      <div key={inc.id} className="flex items-center justify-between opacity-50">
                        <span className="text-[10px] font-mono text-app-text">{t(inc.labelKey)}</span>
                        <span className="text-[9px] font-mono text-status-ok/70">RESOLVED</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Terminal log */}
          <ChaosTerminal entries={terminal} />
        </div>
      </m.div>
    </section>
  );
}
