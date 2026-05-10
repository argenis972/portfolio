import React, { Suspense } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/hero/Hero';
import { ThemeProvider } from './context/ThemeContext';
import { LogProvider } from './context/LogContext';
import { ChaosModeProvider } from './context/ChaosContext';
import { LazyMotion, domAnimation } from 'framer-motion';

// Above-fold critical path (eager)
const SystemStatusBanner = React.lazy(() => import('./components/SystemStatusBanner'));
const LiveMetricsBento   = React.lazy(() => import('./components/LiveMetricsBento'));

// Operational sections
const ChaosPlayground = React.lazy(() => import('./components/ChaosPlayground'));
const ArchitectureTradeoffs = React.lazy(() => import('./components/ArchitectureTradeoffs'));
const TraceViewer     = React.lazy(() => import('./components/TraceViewer'));
const LogStream       = React.lazy(() => import('./components/LogStream'));
const FeaturedIncident = React.lazy(() => import('./components/FeaturedIncident'));
const ChaosModeBanner    = React.lazy(() => import('./components/ChaosModeBanner'));
const DecisionProcessor = React.lazy(() => import('./components/DecisionProcessor'));

// Info sections

const About           = React.lazy(() => import('./components/About'));
const Experience      = React.lazy(() => import('./components/Experience'));

const Projects        = React.lazy(() => import('./components/Projects'));
const Contact         = React.lazy(() => import('./components/Contact'));
const ServerWakeupNotice = React.lazy(() => import('./components/ServerWakeupNotice'));
const SocialRail      = React.lazy(() => import('./components/SocialRail'));
const Footer          = React.lazy(() => import('./components/Footer'));

const SectionFallback = () => (
  <div className="h-24 w-full flex items-center justify-center text-app-muted text-xs opacity-40 tracking-widest font-mono animate-pulse">
    LOADING...
  </div>
);

function App() {
  return (
    <ThemeProvider>
      <LogProvider>
        <ChaosModeProvider>
          <LazyMotion features={domAnimation}>
            <div className="min-h-screen flex flex-col pt-16 selection:bg-app-primary/30 selection:text-app-text transition-colors duration-300">
              <Navbar />

              {/*
                Banner render logic — two independent axes:
                  A) chaos active + system degraded → ChaosModeBanner (unified, collapsible, shows detail on expand)
                  B) chaos active + system OK       → ChaosModeBanner (collapsed label only)
                  C) chaos off    + system degraded → SystemStatusBanner alone (no chaos label)
                  D) chaos off    + system OK       → nothing renders

                ChaosModeBanner returns null when preset === 'off' (cases C & D).
                SystemStatusBanner returns null when chaos is active — it yields to the unified banner.
              */}
              <Suspense fallback={null}>
                <ChaosModeBanner />
              </Suspense>

              <Suspense fallback={null}>
                <DecisionProcessor />
              </Suspense>

              <Suspense fallback={null}>
                <SocialRail />
              </Suspense>

              <Suspense fallback={null}>
                <SystemStatusBanner />
              </Suspense>

              <main className="flex-grow">
                {/* 1 — Hero: KPI strip above the fold */}
                <Hero />

                <Suspense fallback={<SectionFallback />}>

                  {/* 2 — About: bio + photo + links */}
                  <About />

                  {/* 3 — Live Metrics: tiles + sparkline */}
                  <LiveMetricsBento />

                  {/* 4 — Architecture Trade-offs: bridge section */}
                  <ArchitectureTradeoffs />

                  {/* 5 — Chaos Playground: control panel */}
                  <ChaosPlayground />

                  {/* 5 — Trace Viewer: per-request waterfall */}
                  <TraceViewer />

                  {/* 6 — Log Stream: terminal event stream */}
                  <LogStream />

                  {/* 7 — Featured Incident: Production Post-Mortems (INC-001, INC-002, INC-005) */}
                  <FeaturedIncident />


                  {/* 8 — Experience + Education */}
                  <Experience />


                  {/* 10 — Projects */}
                  <Projects />

                  {/* 11 — Contact */}
                  <Contact />

                  {/* Server wakeup notice (cold start UX) */}
                  <ServerWakeupNotice />
                </Suspense>
              </main>

              <Suspense fallback={null}>
                <Footer />
              </Suspense>
            </div>
          </LazyMotion>
        </ChaosModeProvider>
      </LogProvider>
    </ThemeProvider>
  );
}

export default App;
