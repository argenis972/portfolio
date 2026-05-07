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

variable "metrics_basic_auth_username" {
  description = "Basic auth username for Prometheus metrics"
  type        = string
  sensitive   = true
}

variable "metrics_basic_auth_password" {
  description = "Basic auth password for Prometheus metrics"
  type        = string
  sensitive   = true
}
