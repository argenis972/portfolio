import { Github, Linkedin } from 'lucide-react';
import { useAbout } from '../hooks/useApi';

export default function SocialRail() {
  const { data: about } = useAbout();

  const githubUrl = about?.github || 'https://github.com/Argenis1412';
  const linkedinUrl = about?.linkedin || 'https://www.linkedin.com/in/argenis1412/';

  return (
    <aside className="pointer-events-none fixed right-4 top-1/2 z-40 hidden -translate-y-1/2 xl:block">
      <div className="pointer-events-auto flex flex-col gap-3 rounded-2xl border border-app-border bg-app-bg/85 p-2 shadow-[0_14px_40px_rgba(0,0,0,0.28)] backdrop-blur">
        <a
          href={githubUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-app-border bg-app-surface/40 text-app-muted transition-colors hover:border-app-primary/40 hover:text-app-primary"
          aria-label="GitHub"
        >
          <Github className="h-5 w-5" />
        </a>
        <a
          href={linkedinUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-app-border bg-app-surface/40 text-app-muted transition-colors hover:border-app-primary/40 hover:text-app-primary"
          aria-label="LinkedIn"
        >
          <Linkedin className="h-5 w-5" />
        </a>
      </div>
    </aside>
  );
}
