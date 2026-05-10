/**
 * Zod validation schemas for the portfolio API.
 * Kept in sync with the backend Pydantic models.
 */
import { z } from 'zod';

export const LocalizedStringSchema = z.object({
  pt: z.string(),
  en: z.string(),
  es: z.string(),
});

// Summary schema (used in list endpoints)
export const ProjectSchema = z.object({
  id: z.string(),
  name: z.string(),
  short_description: LocalizedStringSchema,
  full_description: LocalizedStringSchema.optional(),
  technologies: z.array(z.string()),
  features: z.array(z.string()).optional().default([]),
  learnings: z.array(z.string()).optional().default([]),
  highlighted: z.boolean(),
  repository: z.string().nullable(),
  demo: z.string().nullable(),
  image: z.string().nullable(),
});

// Detail schema (used in single-project endpoints)
export const ProjectDetailedSchema = ProjectSchema.extend({
  full_description: LocalizedStringSchema,
  features: z.array(z.string()),
  learnings: z.array(z.string()),
});

export const SkillSchema = z.object({
  name: z.string(),
  category: z.string(),
  level: z.number(),
  icon: z.string().nullable(),
});

export const ExperienceSchema = z.object({
  id: z.string(),
  role: LocalizedStringSchema,
  company: z.string(),
  location: z.string(),
  start_date: z.string(),
  end_date: z.string().nullable(),
  description: LocalizedStringSchema,
  technologies: z.array(z.string()),
  current: z.boolean(),
});

export const FormationSchema = z.object({
  id: z.string(),
  course: LocalizedStringSchema,
  institution: z.string(),
  location: z.string(),
  start_date: z.string(),
  end_date: z.string().nullable(),
  description: LocalizedStringSchema,
  current: z.boolean(),
});

export const PhilosophyItemSchema = z.object({
  id: z.string(),
  name: z.string(),
  role: LocalizedStringSchema,
  image_url: z.string(),
  description: LocalizedStringSchema,
});

export const MetricsSummarySchema = z.object({
  p95_ms: z.number().int(),
  p95_status: z.enum(['healthy', 'degraded']),
  requests_24h: z.number().int(),
  error_rate: z.number(),
  error_rate_pct: z.string(),
  error_rate_status: z.enum(['stable', 'warning', 'investigating']),
  system_status: z.enum(['operational', 'degraded', 'down']),
  uptime: z.string(),
  window: z.string(),
  timestamp: z.string(),
  retries_1h: z.number().int().default(0),
  last_incident: z.string().default('none'),
  last_incident_ago: z.string().default('none'),
  // Sub-system status
  worker_status: z.enum(['ok', 'delayed']).default('ok'),
  queue_backlog: z.number().int().default(0),
  cache_status: z.enum(['direct', 'serving']).default('direct'),
  cache_ttl_s: z.number().int().default(0),
  active_path: z.enum(['sync', 'async', 'fallback']).default('sync'),
  // State machine lifecycle
  system_lifecycle: z.enum(['NORMAL', 'DEGRADED', 'RECOVERING', 'STABLE']).default('NORMAL'),
  total_incidents_24h: z.number().int().default(0),
});

export const AboutSchema = z.object({
  name: z.string(),
  title: z.string(),
  location: z.string(),
  email: z.string(),
  phone: z.string(),
  github: z.string(),
  linkedin: z.string(),
  description: LocalizedStringSchema,
  availability: LocalizedStringSchema,
});
