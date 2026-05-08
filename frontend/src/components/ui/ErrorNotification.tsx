/**
 * ErrorNotification — toast displayed when the metrics API is unavailable.
 *
 * Receives traceId and lastSuccessAt as props from useLiveMetrics — it owns
 * no internal state about API status. Manages only the clipboard copy feedback.
 */
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLanguage } from '../../context/LanguageContext';

interface ErrorNotificationProps {
  /** Error from ApiError.traceId — may be undefined if backend didn't send it */
  traceId?: string;
  /** Unix timestamp (ms) of last successful fetch from useLiveMetrics */
  lastSuccessAt: number | null;
  /** Whether to show the notification at all */
  visible: boolean;
}

function formatTimeAgo(ts: number | null, t: (key: string, params?: Record<string, string | number>) => string): string {
  if (ts === null) return t('metrics.error.time_ago.unknown');
  const diff = Math.floor((Date.now() - ts) / 1000);
  if (diff < 60) return t('metrics.error.time_ago.s', { diff });
  if (diff < 3600) return t('metrics.error.time_ago.m', { diff: Math.floor(diff / 60) });
  return t('metrics.error.time_ago.h', { diff: Math.floor(diff / 3600) });
}

export default function ErrorNotification({
  traceId,
  lastSuccessAt,
  visible,
}: ErrorNotificationProps) {
  const [copied, setCopied] = useState(false);
  const { t } = useLanguage();

  const handleCopy = useCallback(() => {
    if (!traceId) return;
    navigator.clipboard.writeText(traceId).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [traceId]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          role="alert"
          aria-live="polite"
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          className="fixed top-20 right-4 z-[60] shadow-2xl w-80
                     glass rounded-2xl px-5 py-4 flex flex-col gap-2 border border-status-error/30"
        >
          <div className="flex items-start gap-3">
            <span className="text-status-error mt-0.5 flex-shrink-0">⚠</span>
            <div className="flex flex-col gap-1 min-w-0">
              <p className="text-sm font-semibold text-app-text">
                {t('metrics.error.unavailable')}
              </p>

              {/* Trace ID row */}
              {traceId ? (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-mono text-app-muted">
                    {t('metrics.error.trace')}:{' '}
                    <span className="text-app-text">{traceId}</span>
                  </span>
                  <button
                    onClick={handleCopy}
                    aria-label="Copy trace ID"
                    className="text-xs font-mono px-2 py-0.5 rounded-md
                               bg-app-surface-hover hover:bg-app-border
                               text-app-muted hover:text-app-text
                               transition-smooth"
                  >
                    {copied ? `✓ ${t('metrics.error.copied')}` : t('metrics.error.copy')}
                  </button>
                </div>
              ) : (
                <span className="text-xs font-mono text-app-muted">
                  {t('metrics.error.no_trace')}
                </span>
              )}

              {/* Last successful fetch */}
              <span className="text-xs text-app-muted">
                {t('metrics.error.last_fetch')}:{' '}
                <span className="font-mono">{formatTimeAgo(lastSuccessAt, t)}</span>
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
