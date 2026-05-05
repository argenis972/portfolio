import { m } from 'framer-motion';
import { useLanguage } from '../context/LanguageContext';

const INCIDENT_IDS = ['001', '002', '005'];

export default function FeaturedIncident() {
  const { t } = useLanguage();

  return (
    <section id="incident-history" className="px-4 max-w-6xl mx-auto py-12">
      <div className="mb-10">
        <h2 className="text-xs font-mono uppercase tracking-[0.2em] text-app-primary mb-1">
          {t('chaos.incidents.history')}
        </h2>
        <p className="text-sm text-app-muted max-w-lg">
          {t('chaos.incidents.history_subtitle')}
        </p>
      </div>

      <div className="space-y-8">
        {INCIDENT_IDS.map((id, index) => (
          <m.div
            key={id}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="rounded-3xl border border-app-border/60 shadow-xl overflow-hidden bg-gradient-to-br from-app-surface/90 to-app-surface hover:border-app-primary/50 transition-colors duration-500"
          >
            <div className={`p-1 bg-gradient-to-r ${id === '001' ? 'from-red-500/20 to-orange-500/20' :
                id === '002' ? 'from-amber-500/20 to-yellow-500/20' :
                  'from-violet-500/20 to-fuchsia-500/20'
              }`} />

            <div className="p-6 md:p-10">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="bg-app-primary/10 text-app-primary text-[10px] font-mono px-2 py-0.5 rounded border border-app-primary/20 font-bold uppercase tracking-widest">
                      {t(`incident.${id}.badge`)}
                    </span>
                    <span className="text-app-muted font-mono text-[10px]">{t(`incident.${id}.id`)}</span>
                  </div>
                  <h3 className="text-2xl font-bold text-app-text">
                    {t(`incident.${id}.title`)}
                  </h3>
                </div>

                 <div className="flex gap-4 border-l border-app-border/40 pl-4">
                   <div className="text-center">
                     <div className="text-xs font-mono text-app-muted uppercase">{t(`incident.${id}.mttr`)}</div>
                     <div className="text-lg font-bold text-app-primary">
                       {id === '001' ? 'Fixed' : id === '002' ? '50ms' : 'Synced'}
                     </div>
                   </div>
                   <div className="text-center">
                     <div className="text-xs font-mono text-app-muted uppercase">{t(`incident.${id}.impact_label`)}</div>
                     <div className="text-lg font-bold text-status-error">
                       {id === '001' ? '100%' : id === '002' ? '>300ms' : '100%'}
                     </div>
                   </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Timeline sidebar */}
                <div className="md:col-span-1 space-y-6">
                  <div className="space-y-4">
                    <h4 className="text-xs font-mono font-bold text-app-primary uppercase tracking-widest">
                      {t(`incident.${id}.timeline_title`)}
                    </h4>
                    <div className="relative border-l border-app-border/40 pl-4 space-y-6">
                      <div className="relative">
                        <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-status-error shadow-[0_0_8px_rgba(248,113,113,0.4)]" />
                        <div className="text-xs font-bold text-app-text mt-1">{t(`incident.${id}.t1_desc`)}</div>
                      </div>
                      <div className="relative">
                        <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-status-warn" />
                        <div className="text-xs font-bold text-app-text mt-1">{t(`incident.${id}.t2_desc`)}</div>
                      </div>
                      <div className="relative">
                        <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-status-ok" />
                        <div className="text-xs font-bold text-app-text mt-1">{t(`incident.${id}.t3_desc`)}</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Analysis content */}
                <div className="md:col-span-2 space-y-6">
                  <div>
                    <h4 className="text-xs font-mono font-bold text-app-primary uppercase tracking-widest mb-3">
                      {t(`incident.${id}.postmortem_title`)}
                    </h4>
                    <p className="text-sm text-app-muted leading-relaxed">
                      {t(`incident.${id}.postmortem_desc`)}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="bg-app-surface/40 rounded-xl border border-app-border/40 p-4">
                      <div className="text-[10px] font-mono text-app-primary mb-2 uppercase">
                        {t(`incident.${id}.lesson_title`)}
                      </div>
                      <p className="text-[11px] text-app-muted italic font-serif">
                        {t(`incident.${id}.lesson_desc`)}
                      </p>
                    </div>
                    <div className="bg-app-surface/40 rounded-xl border border-app-border/40 p-4">
                      <div className="text-[10px] font-mono text-app-primary mb-2 uppercase">
                        {t(`incident.${id}.debt_title`)}
                      </div>
                      <ul className="text-[11px] text-app-muted space-y-1 list-disc pl-3">
                        <li>{t(`incident.${id}.debt_item1`)}</li>
                        <li>{t(`incident.${id}.debt_item2`)}</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </m.div>
        ))}
      </div>
    </section>
  );
}