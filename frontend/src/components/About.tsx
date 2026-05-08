import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { useLanguage } from '../context/LanguageContext';
import { useSkills } from '../hooks/useApi';
import { ChevronRight } from 'lucide-react';

const CATEGORY_ORDER = ['backend', 'banco_dados', 'database', 'devops', 'frontend', 'testing', 'tools', 'automation'];

export default function About() {
  const { t } = useLanguage();
  const { data: skills = [], isLoading: isLoadingSkills } = useSkills();

  const [expandedCat, setExpandedCat] = useState<string | null>(null);

  // Sort and filter categories based on data
  const allCats = Array.from(new Set(skills.map((s) => s.category)));
  const categories = [
    ...CATEGORY_ORDER.filter((c) => allCats.includes(c)),
    ...allCats.filter((c) => !CATEGORY_ORDER.includes(c)),
  ];

  return (
    <section id="about" className="py-12 px-4 max-w-6xl mx-auto">
      <m.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.15 }}
        transition={{ duration: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center"
      >
        {/* Text column */}
        <div>
          <h2 className="text-xs font-mono uppercase tracking-[0.2em] text-app-primary mb-3">
            {t('about.title')}
          </h2>
          <p className="text-sm text-app-muted leading-relaxed mb-6">
            {t('about.bio')}
          </p>

          {!isLoadingSkills && categories.length > 0 && (
            <div className="mb-8">
              <h3 className="text-sm font-bold text-app-text mb-4">
                {t('stack.section_title')}
              </h3>
              <div className="space-y-2">
                {categories.map((category) => {
                  const isExpanded = expandedCat === category;
                  const catSkills = skills.filter((s) => s.category === category);

                  return (
                    <div key={category} className="border border-app-border rounded-lg bg-app-surface overflow-hidden">
                      <button
                        onClick={() => setExpandedCat(isExpanded ? null : category)}
                        className="w-full flex items-center justify-between p-3 text-left hover:bg-app-surface-hover transition-colors focus-visible:outline-none"
                      >
                        <span className="text-xs font-mono uppercase tracking-widest text-app-text">
                          {t(`stack.category.${category}`)}
                        </span>
                        <ChevronRight
                          className={`w-4 h-4 text-app-primary transition-transform duration-300 ${isExpanded ? 'rotate-90' : ''}`}
                        />
                      </button>
                      <AnimatePresence initial={false}>
                        {isExpanded && (
                          <m.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                          >
                            <div className="p-3 pt-0 flex flex-wrap gap-1.5 border-t border-app-border/50">
                              {catSkills.map((skill) => (
                                <span
                                  key={skill.name}
                                  className="inline-flex items-center px-2 py-1 rounded text-xs font-mono text-app-muted hover:text-app-primary hover:bg-app-primary/5 transition-colors border border-transparent hover:border-app-primary/10"
                                >
                                  ▹ {skill.name}
                                </span>
                              ))}
                            </div>
                          </m.div>
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Photo column */}
        <div className="flex justify-center md:justify-end">
          <div className="relative w-[220px] h-[220px] md:w-[280px] md:h-[280px] rounded-full p-1.5 bg-gradient-to-tr from-app-primary to-transparent shadow-[0_0_30px_rgba(212,163,115,0.2)]">
            <div className="w-full h-full rounded-full overflow-hidden bg-app-surface-hover">
              <picture>
                <source srcSet="/profile.webp" type="image/webp" />
                <img
                  src="/profile.jpg"
                  alt="Argenis"
                  width="280"
                  height="280"
                  loading="lazy"
                  className="w-full h-full object-cover rounded-full filter brightness-105"
                />
              </picture>
            </div>
          </div>
        </div>
      </m.div>
    </section>
  );
}
