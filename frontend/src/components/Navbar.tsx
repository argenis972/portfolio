import { useState, useEffect } from 'react';
import { Sun, Moon, Languages, Menu, X } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../hooks/useApi';
import { fetchAbout, fetchSkills } from '../api/portfolioService';
import { scrollToSection } from '../utils/scrollToSection';
import { m, AnimatePresence } from 'framer-motion';

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const { language, setLanguage, t } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };

    // Close drawer if viewport grows past the md breakpoint (768px) so that
    // CSS-hidden drawers do not keep the body scroll-locked.
    const handleResize = () => {
      if (window.innerWidth >= 768 && isOpen) setIsOpen(false);
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', handleResize);
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', handleResize);
    };
  }, [isOpen]);

  const handleNavClick = (section: string) => {
    setIsOpen(false);
    scrollToSection(section);
  };

  const prefetch = (key: readonly unknown[], fn: () => Promise<unknown>) => {
    queryClient.prefetchQuery({
      queryKey: key,
      queryFn: fn,
      staleTime: 20 * 60 * 1000,
    });
  };

  const navItems = [
    { id: 'metrics', label: t('nav.metrics'), prefetchFn: () => prefetch(queryKeys.about, fetchAbout) },
    { id: 'chaos', label: t('nav.chaos') },
    { id: 'observability', label: t('nav.observability') },
    { id: 'about', label: t('nav.about'), prefetchFn: () => { prefetch(queryKeys.about, fetchAbout); prefetch(queryKeys.skills, fetchSkills); } },
    { id: 'contact', label: t('nav.contact'), testId: 'nav-contact' },
  ];

  return (
    <nav className="fixed top-0 w-full z-50 glass border-b border-app-border/70">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Mobile Menu Button */}
          <div className="flex-shrink-0 md:hidden flex items-center">
            <button
              onClick={() => setIsOpen(true)}
              className="p-2 rounded-md text-app-text hover:bg-app-surface-hover transition-colors focus:outline-none focus:ring-2 focus:ring-app-primary"
              aria-label="Open Menu"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>

          <div className="flex-shrink-0 hidden md:block">
            {/* Optional logo or leave empty. Kept div for flex spacing. */}
          </div>

          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  data-testid={item.testId}
                  onClick={() => handleNavClick(item.id)}
                  onMouseEnter={item.prefetchFn}
                  className="hover:text-app-primary px-3 py-3 rounded-md text-xs font-mono uppercase tracking-widest transition-colors text-app-text"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-full border border-app-border/50 bg-app-surface/60 hover:bg-app-surface-hover transition-colors text-app-text"
              aria-label="Toggle Theme"
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>
            <div className="relative flex items-center">
              <div className="absolute left-2.5 pointer-events-none text-app-text/70">
                <Languages className="w-4 h-4" />
              </div>
              <select
                aria-label="Select Language"
                value={language}
                onChange={(e) => setLanguage(e.target.value as 'pt' | 'en' | 'es')}
                className="bg-app-surface border border-app-border text-sm rounded-lg focus:ring-app-primary focus:border-app-primary block pl-9 pr-3 py-2 transition-smooth shadow-sm text-app-text"
              >
                <option value="pt">PT</option>
                <option value="en">EN</option>
                <option value="es">ES</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {isOpen && (
          <>
            <m.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
              onClick={() => setIsOpen(false)}
              aria-hidden="true"
            />
            <m.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 w-3/4 max-w-sm bg-app-bg border-r border-app-border shadow-2xl z-50 md:hidden flex flex-col"
            >
              <div className="flex items-center justify-between h-16 px-4 border-b border-app-border/50">
                <span className="font-mono font-bold text-app-primary tracking-widest text-sm">MENU</span>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 rounded-md text-app-text hover:bg-app-surface-hover transition-colors focus:outline-none focus:ring-2 focus:ring-app-primary"
                  aria-label="Close Menu"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto py-6 px-4 flex flex-col gap-2">
                {navItems.map((item) => (
                  <button
                    key={item.id}
                    data-testid={item.testId ? `mobile-${item.testId}` : undefined}
                    onClick={() => handleNavClick(item.id)}
                    className="flex items-center w-full px-4 py-4 rounded-lg text-sm font-mono uppercase tracking-widest text-app-text hover:bg-app-surface hover:text-app-primary transition-all border border-transparent hover:border-app-border/50 text-left"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </m.div>
          </>
        )}
      </AnimatePresence>
    </nav>
  );
}
