import { motion, AnimatePresence } from 'framer-motion';
import { Code2, Mail, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useAbout } from '../hooks/useApi';

const WhatsAppIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.72 1.041 3.712 1.585 5.703 1.585h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
  </svg>
);

export default function Footer() {
  const { t } = useLanguage();
  const { data: about } = useAbout();
  const [copiedEmail, setCopiedEmail] = useState(false);
  const [copiedWhatsApp, setCopiedWhatsApp] = useState(false);
  const email = about?.email || 'argenisbackend@gmail.com';
  const phone = about?.phone || '(41) 9 9510-3364';

  const handleCopyEmail = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(email);
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  const handleCopyWhatsApp = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(phone);
    setCopiedWhatsApp(true);
    setTimeout(() => setCopiedWhatsApp(false), 2000);
  };



  const maskPhone = (str: string) => str.replace(/\d(?=.{4})/g, '•');

  const contactCards = [
    {
      key: 'email',
      label: 'Email',
      value: email,
      icon: <Mail className="w-4 h-4" />,
      accent: 'text-app-primary bg-app-primary/10 group-hover:bg-app-primary group-hover:text-white',
      buttonAccent: 'group-hover:text-app-primary',
      copied: copiedEmail,
      onCopy: handleCopyEmail,
    },
    {
      key: 'whatsapp',
      label: 'WhatsApp',
      value: maskPhone(phone),
      icon: <WhatsAppIcon className="w-4 h-4" />,
      accent: 'text-[#25D366] bg-[#25D366]/10 group-hover:bg-[#25D366] group-hover:text-white',
      buttonAccent: 'group-hover:text-[#25D366]',
      copied: copiedWhatsApp,
      onCopy: handleCopyWhatsApp,
    },
  ];

  return (
    <footer className="mt-12 w-full border-t border-app-border bg-transparent py-10 transition-colors duration-300">
      <div className="mx-auto max-w-6xl px-4">
        <div className="mx-auto max-w-3xl text-center">
          <div className="grid gap-3 md:grid-cols-2">
            {contactCards.map((card) => (
              <motion.button
                key={card.key}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                onClick={card.onCopy}
                className="group flex min-h-[68px] items-center gap-3 rounded-xl border border-app-border bg-app-surface/50 px-4 py-3 text-left shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-app-primary/40 hover:bg-app-surface-hover/60"
              >
                <div className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full transition-colors duration-300 ${card.accent}`}>
                  {card.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.22em] text-app-muted">{card.label}</p>
                  <p className="truncate text-xs font-semibold text-app-text sm:text-sm">{card.value}</p>
                </div>
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-app-border bg-app-bg/40">
                  <AnimatePresence mode="wait">
                    {card.copied ? (
                      <motion.div
                        key={`${card.key}-check`}
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                      >
                        <Check className="w-4 h-4 text-emerald-500" />
                      </motion.div>
                    ) : (
                      <motion.div
                        key={`${card.key}-copy`}
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                      >
                        <Copy className={`w-4 h-4 text-app-muted transition-colors ${card.buttonAccent}`} />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.button>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-4">
            <a
              href="https://github.com/Argenis1412/portfolio"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-app-border bg-app-surface/40 px-4 py-2 text-[10px] font-bold uppercase tracking-[0.2em] text-app-muted transition-colors hover:border-app-primary/40 hover:text-app-primary"
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>{t('projects.source_code')}</span>
            </a>
          </div>

          <p className="mt-6 text-xs font-medium tracking-wide text-app-muted">
          {t('footer.rights')}
          </p>
        </div>
      </div>
    </footer>
  );
}
