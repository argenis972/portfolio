# Frontend Refinement Implementation Plan

**State**: In Execution
**Branch**: `refactor/frontend-chaos-refinement`

This document outlines the structured attack plan for refining the SRE portfolio's UI, focusing on clarity under pressure, reading hierarchies, and strengthening the "Chaos Playground" as the flagship feature.

## PHASE 1 & 2 — Credibility Basics and Hierarchy
- **Fix PRO-TIP bug**: Remove the duplicated `PRO-TIP:` text from translation files.
- **Fix `1,011` format**: Ensure thousands-separated metrics use the comma format via `toLocaleString('en-US')`.
- **Centralized DEGRADED state**: Make `SystemStatusBanner.tsx` the single source of truth for degradation status, avoiding repetition in individual cards.
- **STABLE without Cause**: Ensure a `STABLE` state in the banner does not show an incident cause.
- **Global synthetic declaration**: Declare only once at the global level that the dashboard uses synthetic data (`~52% synthetic`), removing repetitions on individual cards.
- **Confidence as metadata**: Move the confidence indicator away from primary KPIs to subtle metadata.

## PHASE 3 — Narrative and Flow (Architecture Trade-offs)
- **Visual Order**: Audit and fix the CSS context to guarantee the `ArchitectureTradeoffs` section renders visually above `ChaosPlayground` in the final DOM.

## PHASE 4 — Chaos as Star Feature
- **Dramatic visual feedback**: Add quick flashes to metric cards (P95, Error Rate) immediately upon activating a chaos mode.
- **Aggressive buttons**: Increase the visual weight and styling for stress/failure buttons.
- **Keyword colorized logs**: Apply keyword highlighting (`TIMEOUT`, `RETRY`, `OPEN`) in the terminal/event stream.
- **Prominent Incident History**: Increase the visibility and contrast of post-mortems within the `FeaturedIncident.tsx` component.

## PHASE 5 — Color Discipline
- **Global Audit**: Clean up arbitrary use of semantic colors across `index.css` and React components, strictly enforcing:
  - 🔴 Red: `DEGRADED` / `ERROR`
  - 🟡 Yellow: `WARNING` / `RECOVERING`
  - 🟢 Green: `STABLE` / `OK`
  - 🟣 Purple: Chaos / Synthetic
  - ⬜ Neutral: Everything else
