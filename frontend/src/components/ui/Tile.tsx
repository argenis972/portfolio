import React from 'react';
import { m, type Variants } from 'framer-motion';

const tileVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, delay: i * 0.08, ease: 'easeOut' as const },
  }),
  alert: {
    scale: [1, 1.02, 1],
    borderColor: 'rgba(239, 68, 68, 0.4)',
    transition: { repeat: Infinity, duration: 1.5 },
  },
  critical: {
    x: [0, -1, 1, -1, 1, 0],
    borderColor: 'rgba(220, 38, 38, 0.6)',
    transition: { repeat: Infinity, duration: 0.2 },
  },
  chaos: {
    scale: [1, 1.02, 1],
    borderColor: 'var(--color-status-synthetic)',
    boxShadow: ['0 0 0px rgba(0,0,0,0)', '0 0 20px var(--color-status-synthetic-border)', '0 0 0px rgba(0,0,0,0)'],
    transition: { duration: 0.6 },
  }
};

export function Tile({ index, label, children, alertState }: { index: number; label: string; children: React.ReactNode; alertState?: 'none' | 'alert' | 'critical' | 'chaos' }) {
  return (
    <m.div
      custom={index}
      variants={tileVariants}
      initial="hidden"
      animate={alertState === 'critical' ? 'critical' : alertState === 'alert' ? 'alert' : alertState === 'chaos' ? 'chaos' : 'visible'}
      className={`glass min-h-[120px] rounded-2xl p-5 flex flex-col gap-3 transition-colors duration-300 ${
        alertState === 'critical' ? 'bg-status-error-soft border-status-error/30' : 
        alertState === 'alert' ? 'bg-status-warn-soft border-status-warn/20' : 
        alertState === 'chaos' ? 'bg-[var(--color-status-synthetic-bg)] border-[var(--color-status-synthetic-border)]' :
        ''
      }`}
    >
      <span className="text-xs font-mono uppercase tracking-widest text-app-muted">{label}</span>
      {children}
    </m.div>
  );
}

export function TileSkeleton({ index }: { index: number }) {
  return (
    <Tile index={index} label="—">
      <div className="h-7 w-20 rounded bg-app-border animate-pulse" />
    </Tile>
  );
}
