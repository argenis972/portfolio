import React from 'react';
import { m } from 'framer-motion';
import { useLanguage } from '../../context/LanguageContext';
import { scrollToSection } from '../../utils/scrollToSection';
import { useLiveMetrics } from '../../hooks/useLiveMetrics';

// Sub-components
import LiveStatusBadge from './LiveStatusBadge';
import SystemStateLine from './SystemStateLine';
import KpiStrip from './KpiStrip';
import SystemSidecar from './SystemSidecar';

export const Hero = React.memo(() => {
  const { t } = useLanguage();
  const {
    status, data, previous, sampleHistory, recentTraces, latestTrace,
    latestSample, effectiveP95, confidenceScore, confidenceLabel, recoveryState,
  } = useLiveMetrics();

  return (
    <section id="hero" className="pt-12 pb-12 md:pt-16 md:pb-20 px-4 max-w-6xl mx-auto relative min-h-[85vh] flex items-center">
      {/* Background glow */}
      <div className="hidden md:block absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-app-primary/5 rounded-full blur-[120px] -z-10" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center w-full">
        {/* Left Column: Hero Content */}
        <m.div
          initial={window.innerWidth > 768 ? { x: -20, opacity: 0 } : false}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="max-w-xl text-center md:text-left mx-auto md:mx-0"
        >
          {/* Status badge */}
          {status !== 'degraded' && status !== 'down' && (
            <m.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
              className="mb-4 flex justify-center md:justify-start"
            >
              <LiveStatusBadge status={status} latencyMs={effectiveP95} source={latestSample?.source} />
            </m.div>
          )}

          {/* H1 */}
          <m.h1
            initial={window.innerWidth > 768 ? { opacity: 0, x: -10 } : { opacity: 1, x: 0 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-4xl md:text-6xl font-extrabold tracking-tight mb-4 text-app-text"
          >
            {t('hero.title')}
          </m.h1>

          {/* Subtitle */}
          <m.p
            initial={window.innerWidth > 768 ? { opacity: 0, x: -10 } : { opacity: 1, x: 0 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg md:text-xl text-app-muted max-w-2xl mx-auto md:mx-0"
          >
            {t('hero.subtitle')}
          </m.p>

          {/* Dynamic system state line */}
          {status !== 'degraded' && status !== 'down' && (
            <m.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <SystemStateLine
                status={status}
                effectiveP95={effectiveP95}
                recoveryState={recoveryState}
                lastIncident={data?.last_incident}
              />
            </m.div>
          )}

          {/* KPI strip */}
          {data && (
            <m.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.35 }}
            >
              <KpiStrip
                data={data}
                previous={previous}
                effectiveP95={effectiveP95}
              />
            </m.div>
          )}

          {/* CTAs */}
          <m.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.45 }}
            className="flex flex-col sm:flex-row gap-3 mt-8 justify-center md:justify-start"
          >
            <button
              onClick={() => scrollToSection('metrics')}
              className="bg-app-primary hover:bg-app-primary-hover text-app-primary-text font-bold py-3 px-8 rounded-full transition-smooth premium-shadow font-mono text-sm"
            >
              → {t('hero.cta_metrics')}
            </button>
            <button
              onClick={() => scrollToSection('chaos')}
              className="bg-transparent hover:bg-app-surface-hover text-app-text font-semibold py-3 px-8 rounded-full transition-smooth border border-app-border font-mono text-sm"
            >
              → {t('hero.cta_chaos')}
            </button>
          </m.div>

          {/* Secondary links */}
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="flex gap-4 mt-4 justify-center md:justify-start"
          >
            <a
              href="https://github.com/Argenis1412/portfolio/blob/main/ARCHITECTURE.md"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-mono text-app-muted hover:text-app-primary transition-colors"
            >
              {t('hero.cta_secondary')} ↗
            </a>
          </m.div>
        </m.div>

        {/* Right Column: System State Sidecar */}
        <m.div
          initial={window.innerWidth > 768 ? { x: 20, opacity: 0 } : false}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="hidden md:block"
        >
          <SystemSidecar
            status={status}
            data={data}
            sampleHistory={sampleHistory}
            recentTraces={recentTraces}
            latestTrace={latestTrace}
            latestSample={latestSample}
            effectiveP95={effectiveP95}
            confidenceScore={confidenceScore}
            confidenceLabel={confidenceLabel}
            recoveryState={recoveryState}
          />
        </m.div>
      </div>
    </section>
  );
});

export default Hero;
