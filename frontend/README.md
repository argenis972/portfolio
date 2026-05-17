# 🎨 Portfolio Frontend

> **Live Demo:** [argenisbackend.com →](https://argenisbackend.com)

Frontend application built with **React 19** and **Vite**. Engineered as a **strict consumer** of a versioned REST API, featuring declarative data management with TanStack Query and a premium "Graphite & Bronze" aesthetic.

## ✨ Key Features

- **💎 TanStack Query (v5)**:
    - **Predictive Prefetching**: Data is pre-loaded on Link hover/focus.
    - **Background Sync**: Silent revalidation on window focus.
    - **Centralized Mutations**: Robust state management for the contact form.
- **🌍 Scalable i18n**: Externalized JSON manifests in `src/i18n/` for true decoupling of content and code.
- **🎨 Tailwind CSS v4**: Modern styling with native CSS variables and glassmorphism.
- **🛡️ Automated QA**: Husky + lint-staged force 100% lint/test pass before every commit.

## 🏗️ Component Architecture

The UI is built using atomic, highly specialized components to ensure modularity:

- **`MobileNav`**: Responsive drawer menu featuring scroll-lock, isolated focus trapping, and graceful mounting animations.
- **`Banner` / `Hero`**: Themed hero sections utilizing Framer Motion for entrance staggers.
- **`Footer`**: Contains the decoupled social rails and hardcoded contact fallbacks (with explicit mailto links).
- **`ContactForm`**: Self-contained mutation component hooked to the global rate-limiter, providing dynamic error handling and loading states.

## 🧠 Data Fetching Pattern (`useApi.ts`)

All API interactions are localized in `src/hooks/useApi.ts`. We **do not** write `fetch` or `axios` calls directly in components.

- **Queries**: Modular hooks (`useAbout`, `useProjects`, `useSkills`, etc.) encapsulate the fetcher logic, utilizing TanStack Query to cache JSON payloads. Stale times are specifically tuned (e.g., 5 mins for projects, 10 mins for skills, 60 mins for philosophy). Components simply consume `data`, `isLoading`, or `isError`.
- **Mutations**: `useContactMutation()` handles the POST request, orchestrating success toasts and error boundaries without leaking implementation details into `ContactForm`.

## ♿ Accessibility (a11y)

The frontend is built to be resilient for all users, regardless of navigation method:

- **Visible Focus Rings**: All interactive elements (buttons, links, inputs) have explicit `focus-visible` styling tailored to the dark theme.
- **Keyboard Navigation**: Full support for Tab navigation. `MobileNav` utilizes Focus Trap to prevent keyboard users from tabbing into hidden content.
- **Esc Key Support**: Modals and mobile drawers can be dismissed natively using the `Escape` key.
- **Semantic HTML**: Proper use of `<nav>`, `<main>`, `<section>`, and `aria-label` attributes across the application.
## 📂 Source Structure

```
src/
├── api.ts              # API Client & Shared Interfaces
├── hooks/
│   └── useApi.ts       # Centralized query & mutation hooks
├── i18n/
│   ├── en.json         # English translations
│   ├── pt.json         # Portuguese translations
│   └── es.json         # Spanish translations
├── context/
│   ├── LanguageContext.tsx   # Language state + i18n logic
│   └── ThemeContext.tsx      # Dark/light theme state
├── components/         # Atomic UI components
└── App.tsx             # Main layout orchestrator
```

## 🚀 Getting Started

```bash
cd frontend
npm install
npm run dev
```

### 🛠️ Maintenance Scripts

| Script | Description |
|---|---|
| `npm run build` | Production-ready build with type-checking |
| `npm run lint` | ESLint static analysis |
| `npm run test` | Unit tests with Vitest (watch mode) |
| `npm run preview` | Preview production build locally |

## 🧪 Testing & Quality Gate Policy

We use **Vitest** + **@testing-library/react** for unit and component testing.

The project strictly enforces a **Quality Gate Policy**:
1. **Husky pre-commit**: Runs ESLint and Vitest. Commits are blocked if any test fails or if coverage targets are not met.
2. **TypeScript Integrity**: `tsc --noEmit` validates type correctness in both the `Makefile` and the GitHub Actions CI pipeline.
3. **CI/CD Pipeline**: GitHub Actions runs the full lint and test suite on every push. No code reaches `main` without passing these automated gates.
