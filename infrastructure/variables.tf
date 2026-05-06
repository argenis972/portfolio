variable "database_url" {
  description = "PostgreSQL Database URL (Supabase)"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis URL (Upstash)"
  type        = string
  sensitive   = true
}

variable "sentry_dsn" {
  description = "Sentry DSN for backend observability"
  type        = string
  sensitive   = true
}
