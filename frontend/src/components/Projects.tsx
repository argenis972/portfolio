import { motion } from 'framer-motion';
import { useMemo } from 'react';
import Skeleton from './ui/Skeleton';
import { Github, ExternalLink } from 'lucide-react';
import { useProjects } from '../hooks/useApi';
import { useLanguage } from '../context/LanguageContext';
import { ServerWakeupError } from './ServerWakeupNotice';

interface StorySections {
  problem: string;
  constraint: string;
  decision: string;
  tradeoff: string;
  impact: string;
}

function parseProjectStory(raw: string | undefined): StorySections {
  if (!raw) {
    return { problem: '', constraint: '', decision: '', tradeoff: '', impact: '' };
  }

  const paragraphs = (() => {
    if (typeof DOMParser !== 'undefined') {
      const doc = new DOMParser().parseFromString(raw, 'text/html');
      let nodes = doc.querySelectorAll('.project-story p');

      // Fallback: if .project-story is missing or empty, try any p tags
      if (nodes.length === 0) {
        nodes = doc.querySelectorAll('p');
      }

      return Array.from(nodes)
        .map((node) => node.textContent?.trim() ?? '')
        .filter(Boolean);
    }

    return Array.from(raw.matchAll(/<p>(.*?)<\/p>/g))
      .map((match) => match[1].replace(/<[^>]+>/g, '').trim())
      .filter(Boolean);
  })();

  return {
    problem: paragraphs[0] ?? '',
    constraint: paragraphs[1] ?? '',
    decision: paragraphs[2] ?? '',
    tradeoff: paragraphs[3] ?? '',
    impact: paragraphs[4] ?? '',
  };
}

export default function Projects() {
  const { data: projects, isLoading, isError } = useProjects();
  const { language, t } = useLanguage();
  const labels = useMemo(() => ([
    { key: 'problem', label: t('projects.problem') },
    { key: 'constraint', label: t('projects.constraint') },
    { key: 'decision', label: t('projects.decision') },
    { key: 'tradeoff', label: t('projects.tradeoff') },
    { key: 'impact', label: t('projects.impact') },
  ]), [t]);

  if (isLoading) {
    return (
      <section id="projects" className="py-16 max-w-6xl mx-auto px-4">
        <div className="h-10 w-48 bg-app-surface-hover rounded-md mx-auto mb-12 animate-pulse" />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          {[1, 2].map((i) => (
            <div key={i} className="glass rounded-2xl p-8 border border-app-border">
              <Skeleton className="h-8 w-3/4 mb-4" />
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-5/6 mb-6" />
              <Skeleton className="h-28 w-full rounded-xl mb-4" />
              <Skeleton className="h-24 w-full rounded-xl mb-4" />
              <div className="flex gap-2 mb-6">
                <Skeleton className="h-6 w-16 rounded-full" />
                <Skeleton className="h-6 w-16 rounded-full" />
                <Skeleton className="h-6 w-16 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (isError) {
    return (
      <section id="projects" className="py-24 max-w-6xl mx-auto px-4">
        <ServerWakeupError />
      </section>
    );
  }

  if (!projects || projects.length === 0) {
    return (
      <section id="projects" className="py-24 max-w-6xl mx-auto px-4 text-center">
        <h2 className="text-3xl font-bold mb-8 text-app-text">{t('nav.projects')}</h2>
        <p className="text-app-muted">{t('projects.empty')}</p>
      </section>
    );
  }

  return (
    <section id="projects" className="py-16 max-w-6xl mx-auto px-4 relative group overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] bg-[var(--glow-primary)] rounded-full blur-[120px] -z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.1, margin: '0px 0px -100px 0px' }}
        transition={{ duration: 0.8 }}
      >
        <div className="mb-12 text-center max-w-3xl mx-auto">
          <h2 className="text-3xl md:text-5xl font-bold text-app-text tracking-widest">
            {t('nav.projects')}
          </h2>
          <p className="mt-4 text-sm md:text-base text-app-muted leading-relaxed">
            {t('projects.subtitle')}
          </p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          {projects.map((project, index) => {
            const shortDescription = project.short_description[language as keyof typeof project.short_description];
            const story = parseProjectStory(project.full_description?.[language as keyof typeof project.full_description]);

            return (
              <motion.article
                key={project.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.1 }}
                transition={{ duration: 0.5, delay: index * 0.08 }}
                className="glass rounded-2xl border border-app-border p-6 md:p-8 hover:border-app-primary/40 hover:shadow-[0_0_30px_rgba(212,163,115,0.18)] transition-all duration-300"
              >
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-[0.25em] text-app-primary mb-2">
                      {t('projects.case_study')}
                    </div>
                    <h3 className="text-2xl font-bold text-app-text">{project.name}</h3>
                  </div>
                  {project.highlighted && (
                    <span className="rounded-full border border-app-primary/20 bg-app-primary/10 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.2em] text-app-primary">
                      {t('projects.featured')}
                    </span>
                  )}
                </div>

                <p className="text-sm leading-relaxed text-app-muted mb-5">
                  {shortDescription}
                </p>

                <div className="grid gap-3 md:grid-cols-2 mb-5">
                  {labels.map(({ key, label }) => {
                    const value = story[key as keyof StorySections];
                    return (
                      <div key={key} className="rounded-xl border border-app-border/60 bg-app-surface/35 p-4">
                        <div className="text-[10px] font-mono uppercase tracking-[0.22em] text-app-muted mb-2">
                          {label}
                        </div>
                        <p className="text-sm leading-relaxed text-app-text/85">{value}</p>
                      </div>
                    );
                  })}
                </div>

                <div className="rounded-xl border border-app-border/60 bg-[#0F141A] p-4 mb-5 font-mono text-xs text-slate-300">
                  <div className="text-[10px] uppercase tracking-[0.22em] text-app-muted mb-3">{t('projects.stack')}</div>
                  <div className="flex flex-wrap gap-x-6 gap-y-2">
                    <div>
                      <span className="text-slate-400">{t('projects.runtime')}:</span>
                      <span className="ml-2 text-slate-100">{project.technologies.slice(0, 3).join(' / ')}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">{t('projects.surface')}:</span>
                      <span className="ml-2 text-slate-100">{project.features?.length ?? 0} signals</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 mb-6">
                  {project.technologies.slice(0, 10).map((tech) => (
                    <span key={tech} className="rounded-full border border-app-primary/10 bg-app-primary/5 px-3 py-1 text-xs font-semibold text-app-primary">
                      {tech}
                    </span>
                  ))}
                  {project.technologies.length > 10 && (
                    <span className="rounded-full border border-app-border bg-app-surface-hover px-3 py-1 text-xs font-medium text-app-muted">
                      +{project.technologies.length - 10}
                    </span>
                  )}
                </div>

                <div className="flex gap-4 mt-auto border-t border-app-border pt-4">
                  {project.repository && (
                    <a href={project.repository} target="_blank" rel="noopener noreferrer" className="flex-1 rounded-xl border border-app-border bg-app-surface px-4 py-2.5 text-sm font-semibold text-app-text transition-colors hover:border-app-primary hover:text-app-primary flex items-center justify-center gap-2">
                      <Github className="w-5 h-5" />
                      {t('projects.source_code')}
                    </a>
                  )}
                  {project.demo && (
                    <a href={project.demo} target="_blank" rel="noopener noreferrer" className="flex-1 rounded-xl bg-app-primary px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-app-primary-hover flex items-center justify-center gap-2 premium-shadow">
                      <ExternalLink className="w-5 h-5" />
                      {t('projects.live_demo')}
                    </a>
                  )}
                </div>
              </motion.article>
            );
          })}
        </div>
      </motion.div>
    </section>
  );
}
