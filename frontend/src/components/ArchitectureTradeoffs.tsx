import { m } from 'framer-motion';
import { useLanguage } from '../context/LanguageContext';

export default function ArchitectureTradeoffs() {
  const { t } = useLanguage();

  const tradeOffs = [
    {
      title: t('tradeoffs.latency.title'),
      desc: t('tradeoffs.latency.desc'),
      status: t('tradeoffs.status.active'),
      impact: t('tradeoffs.latency.impact')
    },
    {
      title: t('tradeoffs.sync.title'),
      desc: t('tradeoffs.sync.desc'),
      status: t('tradeoffs.status.optimized'),
      impact: t('tradeoffs.sync.impact')
    },
    {
      title: t('tradeoffs.logging.title'),
      desc: t('tradeoffs.logging.desc'),
      status: t('tradeoffs.status.enforced'),
      impact: t('tradeoffs.logging.impact')
    }
  ];

  return (
    <section id="tradeoffs" className="px-4 max-w-6xl mx-auto py-12">
      <div className="mb-8">
        <h2 className="text-xs font-mono uppercase tracking-[0.2em] text-app-primary mb-1">
          {t('tradeoffs.title')}
        </h2>
        <p className="text-sm text-app-muted">{t('tradeoffs.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {tradeOffs.map((item, i) => (
          <m.div
            key={item.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className="group relative p-6 rounded-2xl border border-app-border/40 bg-app-surface/20 hover:bg-app-primary/5 transition-colors duration-300"
          >
            <div className="absolute top-4 right-4 text-[9px] font-mono text-app-primary/60 border border-app-primary/20 rounded px-1.5 py-0.5">
              {item.status}
            </div>

            <h3 className="text-sm font-bold text-app-text mb-3">{item.title}</h3>
            <p className="text-xs text-app-muted leading-relaxed mb-4">
              {item.desc}
            </p>

            <div className="pt-4 border-t border-app-border/20">
              <div className="text-[9px] font-mono text-app-muted uppercase tracking-wider mb-1">{t('tradeoffs.impact_label')}</div>
              <div className="text-[11px] font-mono text-app-primary font-bold">
                {'>'} {item.impact}
              </div>
            </div>
          </m.div>
        ))}
      </div>

      <div className="mt-8 p-4 bg-app-primary/5 border border-app-primary/10 rounded-xl">
        <p className="text-[11px] font-mono text-app-muted leading-relaxed">
          {t('tradeoffs.protip')}
        </p>
      </div>
    </section>
  );
}
