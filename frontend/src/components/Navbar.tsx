import { Sun, Moon, Languages } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../hooks/useApi';
import { fetchAbout, fetchSkills } from '../api/portfolioService';
import { scrollToSection } from '../utils/scrollToSection';

export default function Navbar() {
  const { language, setLanguage, t } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const queryClient = useQueryClient();

  const prefetch = (key: readonly unknown[], fn: () => Promise<unknown>) => {
    queryClient.prefetchQuery({
      queryKey: key,
      queryFn: fn,
      staleTime: 20 * 60 * 1000,
    });
  };

  return (
    <nav className="fixed top-0 w-full z-50 glass border-b border-app-border/70">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex-shrink-0 hidden md:block">
            {/* Optional logo or leave empty. Kept div for flex spacing. */}
          </div>
          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-1">
              <button
                onClick={() => scrollToSection('metrics')}
                onMouseEnter={() => prefetch(queryKeys.about, fetchAbout)}
                className="hover:text-app-primary px-3 py-3 rounded-md text-xs font-mono uppercase tracking-widest transition-colors text-app-text"
              >
                {t('nav.metrics')}
              </button>
              <button
                onClick={() => scrollToSection('chaos')}
                className="hover:text-app-primary px-3 py-3 rounded-md text-xs font-mono uppercase tracking-widest transition-colors text-app-text"
              >
                {t('nav.chaos')}
              </button>
              <button
                onClick={() => scrollToSection('observability')}
                className="hover:text-app-primary px-3 py-3 rounded-md text-xs font-mono uppercase tracking-widest transition-colors text-app-text"
              >
                {t('nav.observability')}
              </button>
              <button
                onClick={() => scrollToSection('about')}
                onMouseEnter={() => {
                  prefetch(queryKeys.about, fetchAbout);
                  prefetch(queryKeys.skills, fetchSkills);
                }}
                className="hover:text-app-primary px-3 py-3 rounded-md text-xs font-mono uppercase tracking-widest transition-colors text-app-text"
              >
                {t('nav.about')}
              </button>
              <button
                data-testid="nav-contact"
                onClick={() => scrollToSection('contato')}
                className="hover:text-app-primary px-3 py-3 rounded-md text-xs font-mono uppercase tracking-widest transition-colors text-app-text"
              >
                {t('nav.contact')}
              </button>
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
    </nav>
  );
}
