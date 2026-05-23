/**
 * ChaosActionCard — individual action button for the Chaos Playground.
 * Displays icon, title, description and a cooldown-aware trigger button.
 */
import { m } from 'framer-motion';
import { useLanguage } from '../../context/LanguageContext';

export interface ChaosActionCardProps {
  icon: string;
  titleKey: string;
  descKey: string;
  accentClass: string;
  borderClass: string;
  hoverClass: string;
  loading: boolean;
  cooldown: number;
  loadingKey: string;
  actionKey: string;
  disabled: boolean;
  onClick: () => void;
  disclaimer?: string;
  // Test ID for E2E testing, follows convention: chaos-btn-{action}
  testId?: `chaos-btn-${string}`;
}

export default function ChaosActionCard({
  icon, titleKey, descKey, accentClass, borderClass, hoverClass,
  loading, cooldown, loadingKey, actionKey, disabled, onClick, disclaimer, testId,
}: ChaosActionCardProps) {
  const { t } = useLanguage();
  return (
    <div className={`glass rounded-xl p-4 flex flex-col gap-3 border ${borderClass} transition-all duration-200`}>
      <div className="flex items-center gap-2">
        <span className="text-lg">{icon}</span>
        <span className={`font-mono text-sm font-bold ${accentClass}`}>{t(titleKey)}</span>
      </div>
      <p className="text-xs text-app-muted leading-relaxed">{t(descKey)}</p>
      {disclaimer && (
        <p className="text-[10px] font-mono text-app-muted/60 italic">{disclaimer}</p>
      )}
       <m.button
         data-testid={testId}
         onClick={onClick}
         disabled={disabled}
         whileTap={!disabled ? { scale: 0.97 } : {}}
         className={`flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-mono text-xs font-semibold transition-all duration-200 mt-auto ${
           disabled
             ? 'bg-app-surface-hover text-app-muted cursor-not-allowed opacity-60'
             : `${hoverClass} border ${borderClass}`
         }`}
       >
        {loading ? (
          <>
            <span className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
            {t(loadingKey)}
          </>
        ) : cooldown > 0 ? (
          t('chaos.cooldown', { s: cooldown })
        ) : (
          t(actionKey)
        )}
      </m.button>
    </div>
  );
}
