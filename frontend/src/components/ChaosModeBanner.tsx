import { m, AnimatePresence } from 'framer-motion';
import { useChaosMode } from '../hooks/useChaosMode';
import { useLanguage } from '../context/LanguageContext';

export default function ChaosModeBanner() {
  const { preset } = useChaosMode();
  const { t } = useLanguage();

  return (
    <AnimatePresence>
      {preset !== 'off' && (
        <m.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="bg-[var(--color-status-synthetic)]/90 backdrop-blur-sm border-y border-[var(--color-status-synthetic-border)] overflow-hidden relative"
        >
          <div className="max-w-6xl mx-auto px-4 py-2 flex items-center justify-center gap-3">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
            </span>
            <span className="text-[10px] sm:text-xs font-mono font-bold text-white uppercase tracking-[0.2em]">
              {t('chaos.banner.active')}: <span className="underline decoration-white/40">{t('chaos.banner.mode', { p: preset.toUpperCase() })}</span>
            </span>
            <span className="hidden md:inline-block text-[9px] font-mono text-white/60">
              {t('chaos.banner.hint')}
            </span>
          </div>

          {/* Animated scanline effect */}
          <div className="absolute inset-0 pointer-events-none bg-gradient-to-r from-transparent via-white/5 to-transparent w-1/4 h-full skew-x-[-20deg] animate-[shimmer_2s_infinite]" />
        </m.div>
      )}
    </AnimatePresence>
  );
}
