import { m, AnimatePresence } from 'framer-motion';
import { useLanguage } from '../../context/LanguageContext';
import type { TerminalEntry } from '../../hooks/useChaosActions';

// Re-export for compatibility with other components
export type { TerminalEntry };

interface ChaosTerminalProps {
  entries: TerminalEntry[];
}

export default function ChaosTerminal({ entries }: ChaosTerminalProps) {
  const { t } = useLanguage();

  return (
    <AnimatePresence mode="popLayout">
      <div className="rounded-xl bg-[#0a0a0a] border border-app-border p-4 font-mono text-xs overflow-y-auto max-h-[220px]">
         <div className="flex items-center gap-2 mb-3">
           <span className="w-2.5 h-2.5 rounded-full bg-status-error/60" />
           <span className="w-2.5 h-2.5 rounded-full bg-status-warn/60" />
           <span className="w-2.5 h-2.5 rounded-full bg-status-ok/60" />
           <span className="text-[10px] text-app-muted/50 ml-2 uppercase tracking-widest">chaos-log</span>
         </div>
        {entries.length === 0 ? (
          <p className="text-white/40">{'>'} {t('logs.waiting')}</p>
        ) : (
          entries.map((entry) => {
            const parts = entry.message.split(/(TIMEOUT|CIRCUIT_BREAKER=OPEN|RETRY|DEGRADED|FALLBACK|RECOVERED|status=APPLIED)/g);
            const formattedMessage = parts.map((part, i) => {
              if (part === 'TIMEOUT' || part === 'CIRCUIT_BREAKER=OPEN') return <span key={i} className="text-status-error font-bold bg-status-error-soft px-1 rounded">{part}</span>;
              if (part === 'DEGRADED') return <span key={i} className="text-status-error font-bold">{part}</span>;
              if (part === 'RETRY' || part === 'FALLBACK') return <span key={i} className="text-status-warn font-bold bg-status-warn-soft px-1 rounded">{part}</span>;
              if (part === 'RECOVERED' || part === 'status=APPLIED') return <span key={i} className="text-status-ok font-bold">{part}</span>;
              return part;
            });

            return (
              <m.div
                key={entry.id}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex gap-2 mb-1"
              >
                <span className="text-white/60 flex-shrink-0">[{entry.timestamp}]</span>
                 <span className={
                   entry.level === 'ERROR' ? 'text-status-error flex-shrink-0' :
                   entry.level === 'WARN' ? 'text-status-warn flex-shrink-0' :
                   'text-status-ok/70 flex-shrink-0'
                 }>{entry.level.padEnd(5)}</span>
                <span className="text-white/90 break-all">{formattedMessage}</span>
              </m.div>
            );
          })
        )}
      </div>
    </AnimatePresence>
  );
}
