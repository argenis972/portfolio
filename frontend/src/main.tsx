import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { LanguageProvider } from './context/LanguageContext.tsx'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as Sentry from '@sentry/react'

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN || "",
  sendDefaultPii: false,
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Static data: 15 min stale, 30 min in cache (gcTime >> staleTime)
      staleTime: 15 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      // Static portfolio: no need to refetch on tab change or mount
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      // 1 retry maximum — with 4 the recruiter waits ~30s before seeing error
      retry: 1,
      retryDelay: 1000,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Sentry.ErrorBoundary fallback={
      <div className="flex h-screen w-full items-center justify-center bg-zinc-950 text-white">
        <h2>Oops! Un error inesperado ocurrió en la aplicación.</h2>
      </div>
    }>
      <QueryClientProvider client={queryClient}>
        <LanguageProvider>
          <App />
        </LanguageProvider>
      </QueryClientProvider>
    </Sentry.ErrorBoundary>
  </React.StrictMode>,
)
