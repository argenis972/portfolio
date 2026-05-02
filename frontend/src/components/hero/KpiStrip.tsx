
import { useLanguage } from '../../context/LanguageContext';
import { type SystemStatus } from '../../hooks/useLiveMetrics';
import { type MetricsSummary } from '../../api/types';
import DeltaBadge from '../ui/DeltaBadge';

const STATUS_COLORS: Record<SystemStatus, string> = {
  loading: 'text-app-muted',
  operational: 'text-status-ok',
  warning: 'text-status-warn',
  degraded: 'text-status-error',
  down: 'text-status-error',
};

interface KpiStripProps {
  data: MetricsSummary;
  previous: MetricsSummary | null;
  status: SystemStatus;
  effectiveP95: number;
}

export function KpiStrip({ data, previous, status, effectiveP95 }: KpiStripProps) {
  const { t } = useLanguage();

  const items = [
    {
      label: t('hero.kpi.latency'),
      value: `${effectiveP95}ms`,
      delta: <DeltaBadge current={effectiveP95} previous={previous?.p95_ms ?? null} unit="ms" />,
    },
     {
       label: t('hero.kpi.error_rate'),
       value: data.error_rate_pct,
       className: data.error_rate > 0.045 ? 'text-status-error' : 'text-app-text',
       delta: <DeltaBadge current={data.error_rate * 100} previous={previous ? previous.error_rate * 100 : null} unit="%" decimals={2} />,
       footnote: t('metrics.error_rate_slo_context'),
     },
    {
      label: t('hero.kpi.requests'),
      value: data.requests_24h.toLocaleString('en-US'),
      delta: null,
    },
    {
      label: t('hero.kpi.state'),
      value: t(`metrics.status.${status}`).toUpperCase(),
      className: STATUS_COLORS[status],
      delta: null,
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-8 max-w-xl mx-auto md:mx-0">
      {items.map((item) => (
        <div key={item.label} className="glass rounded-xl px-4 py-3 flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase tracking-widest text-app-muted">{item.label}</span>
           <div className="flex items-baseline flex-wrap">
             <span className={`font-mono text-lg font-bold ${item.className ?? 'text-app-text'}`}>
               {item.value}
             </span>
             {item.delta}
             {item.footnote && (
               <div className="text-[9px] text-status-ok/80 mt-1">
                 {item.footnote}
               </div>
             )}
           </div>
        </div>
      ))}
    </div>
  );
}

export default KpiStrip;
