import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Loader2, AlertCircle, Terminal, ShieldCheck, Clock3 } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useAbout } from '../hooks/useApi';
import { useContactForm } from '../hooks/useContactForm';

const WhatsAppIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.72 1.041 3.712 1.585 5.703 1.585h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
  </svg>
);

export default function Contact() {
  const { t, language } = useLanguage();
  const { data: about } = useAbout();
  const {
    formData, errors, traceResult, idempotencyKey,
    status, submitError, responseStatusCode, responseTraceId,
    queueStatus, deliveryMode, downstream, responseTone,
    handleChange, handleSubmit
  } = useContactForm();

  const handleWhatsApp = () => {
    if (!about?.phone) return;
    const cleanNumber = about.phone.replace(/\D/g, '');
    const finalNumber = cleanNumber.startsWith('55') ? cleanNumber : `55${cleanNumber}`;
    const message = language === 'es'
      ? '¡Hola Argenis! Vi tu portafolio y me gustaría hablar contigo.'
      : language === 'en'
      ? 'Hello Argenis! I saw your portfolio and would like to talk!'
      : 'Olá Argenis! Vi seu portfólio e gostaria de conversar!';
    window.open(
      `https://wa.me/${finalNumber}?text=${encodeURIComponent(message)}`,
      '_blank',
      'noopener,noreferrer'
    );
  };

  const availability = about?.availability?.[language as 'pt' | 'en' | 'es'] ?? '...';
  const specRows = [
    { label: t('contact.spec.endpoint'), value: 'POST /api/v1/contact' },
    { label: t('contact.spec.idempotency'), value: 'Idempotency-Key header' },
    { label: t('contact.spec.protection'), value: t('contact.spec.protection_value') },
    { label: t('contact.spec.availability'), value: availability },
    { label: t('contact.spec.delivery_mode'), value: 'background_tasks' },
    { label: t('contact.spec.response'), value: t('contact.spec.response_value') },
  ];

  return (
    <section id="contato" className="py-16 max-w-6xl mx-auto px-4 relative group overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-[var(--glow-primary)] rounded-full blur-[140px] -z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.1, margin: "0px 0px -100px 0px" }}
        transition={{ duration: 0.8 }}
      >
        <div className="max-w-3xl mx-auto mb-14 text-center">
          <h2 className="text-3xl md:text-5xl font-bold text-app-text tracking-widest uppercase">
            {t('contact.title')}
          </h2>
          <p className="mt-4 text-sm md:text-base text-app-muted leading-relaxed">
            {t('contact.subtitle')}
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-[0.95fr_1.35fr] items-stretch">
          <motion.aside
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.1 }}
            transition={{ duration: 0.6 }}
            className="flex flex-col h-full glass rounded-2xl p-6 md:p-8 border border-app-border hover:border-app-primary/40 transition-all duration-500"
          >
            <div className="inline-flex items-start self-start items-center gap-2 rounded-full border border-app-primary/20 bg-app-primary/5 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.25em] text-app-primary">
              <ShieldCheck className="h-3.5 w-3.5" />
              {t('contact.api.title')}
            </div>

            <h3 className="mt-5 text-2xl font-bold text-app-text">
              {t('contact.api.summary')}
            </h3>

            <div className="mt-8 space-y-4">
              {specRows.map((row) => (
                <div key={row.label} className="rounded-xl border border-app-border bg-app-surface/40 px-4 py-3">
                  <p className="text-[10px] font-mono uppercase tracking-[0.25em] text-app-muted">{row.label}</p>
                  <p className="mt-2 text-sm text-app-text break-words">{row.value}</p>
                </div>
              ))}
            </div>

            <div className="mt-auto pt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              <a
                href={`mailto:${about?.email ?? ''}`}
                className="flex items-center justify-center gap-3 rounded-xl border border-app-border bg-app-surface/50 px-4 py-4 text-sm font-semibold text-app-text transition-colors hover:border-app-primary/40 hover:text-app-primary"
              >
                <Mail className="h-4 w-4" />
                {t('contact.channel.email')}
              </a>
              <button
                type="button"
                onClick={handleWhatsApp}
                className="flex items-center justify-center gap-3 rounded-xl bg-[#0A854D] px-4 py-4 text-sm font-semibold text-white transition-colors hover:bg-[#075E54]"
              >
                <WhatsAppIcon className="h-5 w-5 flex-shrink-0" />
                {t('contact.whatsapp')}
              </button>
            </div>
          </motion.aside>

          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, amount: 0.1 }}
            transition={{ duration: 0.6 }}
            className="overflow-hidden rounded-2xl border border-[#2A2A2A] bg-[#0B0F14] shadow-[0_20px_60px_rgba(0,0,0,0.35)]"
          >
            <div className="flex items-center justify-between border-b border-[#20262D] bg-[#11161D] px-4 py-3 font-mono text-[11px] text-slate-400">
              <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-status-error" />
                <div className="h-2.5 w-2.5 rounded-full bg-status-warn" />
                <div className="h-2.5 w-2.5 rounded-full bg-status-ok" />
              </div>
                <span>{t('contact.form.title')}</span>
              </div>
              <div className={`inline-flex items-center gap-2 uppercase tracking-[0.2em] ${responseTone}`}>
                <Terminal className="h-3.5 w-3.5" />
                {t(`contact.console.status.${status}`)}
              </div>
            </div>

            <form onSubmit={handleSubmit} noValidate className="p-5 md:p-7">
              <input type="text" name="website" id="hp_website" aria-label="Website" style={{ position: 'absolute', left: '-5000px' }} tabIndex={-1} autoComplete="off" />
              <input type="text" name="fax" id="hp_fax" aria-label="Fax" style={{ position: 'absolute', left: '-5000px' }} tabIndex={-1} autoComplete="off" />

              <div className="mb-6 grid gap-3 rounded-xl border border-[#20262D] bg-[#0F141A] p-4 font-mono text-xs text-slate-300 md:grid-cols-2">
                <div>
                  <span className="text-slate-500">{t('contact.console.request')}:</span>
                  <span className="ml-2 text-app-primary">POST /api/v1/contact</span>
                </div>
                <div className="break-all">
                  <span className="text-slate-500">{t('contact.spec.idempotency')}:</span>
                  <span className="ml-2 text-slate-300">{idempotencyKey}</span>
                </div>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <div className="flex flex-col gap-2">
                  <label htmlFor="name" className="text-[11px] font-mono uppercase tracking-[0.25em] text-slate-500">{t('contact.name')}</label>
                   <input
                     type="text"
                     id="name"
                     name="name"
                     placeholder={t('contact.placeholder.name')}
                     value={formData.name}
                     onChange={handleChange}
                     className={`rounded-xl border bg-[#11161D] px-4 py-3 text-sm text-slate-100 outline-none transition-all placeholder:text-slate-500 ${errors.name ? 'border-status-error/60 focus:ring-2 focus:ring-status-error/20' : 'border-[#20262D] focus:border-app-primary/60 focus:ring-2 focus:ring-app-primary/20'}`}
                   />
                   <AnimatePresence>
                     {errors.name && (
                       <motion.p initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="flex items-center gap-1 text-[11px] text-status-error">
                         <AlertCircle className="h-3.5 w-3.5" />
                         {t(`contact.error.${errors.name}`)}
                       </motion.p>
                     )}
                   </AnimatePresence>
                </div>

                <div className="flex flex-col gap-2">
                  <label htmlFor="email" className="text-[11px] font-mono uppercase tracking-[0.25em] text-slate-500">{t('contact.email')}</label>
                   <input
                     type="email"
                     id="email"
                     name="email"
                     placeholder={t('contact.placeholder.email')}
                     value={formData.email}
                     onChange={handleChange}
                     className={`rounded-xl border bg-[#11161D] px-4 py-3 text-sm text-slate-100 outline-none transition-all placeholder:text-slate-500 ${errors.email ? 'border-status-error/60 focus:ring-2 focus:ring-status-error/20' : 'border-[#20262D] focus:border-app-primary/60 focus:ring-2 focus:ring-app-primary/20'}`}
                   />
                   <AnimatePresence>
                     {errors.email && (
                       <motion.p initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="flex items-center gap-1 text-[11px] text-status-error">
                         <AlertCircle className="h-3.5 w-3.5" />
                         {t(`contact.error.${errors.email}`)}
                       </motion.p>
                     )}
                   </AnimatePresence>
                </div>
              </div>

              <div className="mt-5 flex flex-col gap-2">
                <label htmlFor="subject" className="text-[11px] font-mono uppercase tracking-[0.25em] text-slate-500">{t('contact.subject')}</label>
                <input
                  type="text"
                  id="subject"
                  name="subject"
                  placeholder={t('contact.placeholder.subject')}
                  value={formData.subject}
                  onChange={handleChange}
                  className="rounded-xl border border-[#20262D] bg-[#11161D] px-4 py-3 text-sm text-slate-100 outline-none transition-all placeholder:text-slate-500 focus:border-app-primary/60 focus:ring-2 focus:ring-app-primary/20"
                />
              </div>

              <div className="mt-5 flex flex-col gap-2">
                <label htmlFor="message" className="text-[11px] font-mono uppercase tracking-[0.25em] text-slate-500">{t('contact.message')}</label>
                <textarea
                  id="message"
                  name="message"
                  rows={6}
                  placeholder={t('contact.placeholder.message')}
                  value={formData.message}
                  onChange={handleChange}
                  className={`resize-none rounded-xl border bg-[#11161D] px-4 py-3 text-sm text-slate-100 outline-none transition-all placeholder:text-slate-500 ${errors.message ? 'border-status-error/60 focus:ring-2 focus:ring-status-error/20' : 'border-[#20262D] focus:border-app-primary/60 focus:ring-2 focus:ring-app-primary/20'}`}
                />
                <AnimatePresence>
                  {errors.message && (
                    <motion.p initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="flex items-center gap-1 text-[11px] text-status-error">
                      <AlertCircle className="h-3.5 w-3.5" />
                      {t(`contact.error.${errors.message}`)}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                <div className="inline-flex items-center gap-2 rounded-xl border border-[#20262D] bg-[#0F141A] px-4 py-3 font-mono text-xs text-slate-400">
                  <Clock3 className="h-4 w-4 text-app-primary" />
                  {t('contact.spec.response_value')}
                </div>
                <motion.button
                  whileHover={status !== 'loading' ? { scale: 1.02 } : {}}
                  whileTap={status !== 'loading' ? { scale: 0.98 } : {}}
                  type="submit"
                  disabled={status === 'loading'}
                  className="inline-flex items-center justify-center gap-3 rounded-xl bg-app-primary px-6 py-3.5 text-xs font-bold uppercase tracking-[0.25em] text-app-primary-text transition-all duration-300 hover:bg-app-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {status === 'loading' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
                  {status === 'loading' ? t('contact.sending') : t('contact.send')}
                </motion.button>
              </div>

              <div className="mt-6 overflow-hidden rounded-xl border border-[#20262D] bg-[#0F141A] font-mono text-xs text-slate-300">
                <div className="border-b border-[#20262D] px-4 py-3 text-[11px] uppercase tracking-[0.25em] text-slate-500">
                  {t('contact.console.title')}
                </div>
                <div className="space-y-2 px-4 py-4 leading-6">
                  <div>
                    <span className="text-slate-500">$</span>
                    <span className="ml-2 text-slate-200">curl -X POST /api/v1/contact</span>
                  </div>
                  <div>
                    <span className="text-slate-500">{t('contact.console.request')}:</span>
                    <span className="ml-2 text-slate-300">payload=name,email,subject,message</span>
                  </div>
                  <div>
                    <span className="text-slate-500">{t('contact.console.response')}:</span>
                    {status === 'success' && traceResult ? (
                      <span className="ml-2 text-status-ok">200 OK ({traceResult.durationMs}ms)</span>
                    ) : status === 'error' ? (
                      <span className="ml-2 text-status-error">{responseStatusCode ?? 500} ERROR</span>
                    ) : status === 'loading' ? (
                      <span className="ml-2 text-status-warn">{t('contact.sending')}</span>
                    ) : (
                      <span className="ml-2 text-slate-500">{t('contact.console.ready')}</span>
                    )}
                  </div>

                  {responseTraceId && (
                    <div>
                      <span className="text-slate-500">{t('contact.console.trace')}:</span>
                      <span className="ml-2 break-all text-status-info">{responseTraceId}</span>
                    </div>
                  )}

                  {status === 'success' && traceResult && (
                    <>
                      <div>
                        <span className="text-slate-500">{t('contact.console.queue')}:</span>
                        <span className="ml-2 text-status-warn">{queueStatus}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">{t('contact.console.mode')}:</span>
                        <span className="ml-2 text-slate-300">{deliveryMode}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">{t('contact.console.downstream')}:</span>
                        <span className="ml-2 text-slate-300">{downstream}</span>
                      </div>
                    </>
                  )}

                  {status === 'success' && (
                    <div className="text-status-ok">{t('contact.console.delivered')}</div>
                  )}

                  {status === 'error' && (
                    <div className="text-status-error">{submitError || t('contact.console.rejected')}</div>
                  )}
                </div>
              </div>
            </form>
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
}
