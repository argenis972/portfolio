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

variable "ambiente" {
  description = "Environment (development, production)"
  type        = string
  default     = "production"
}

variable "api_host" {
  description = "API Host"
  type        = string
  default     = "0.0.0.0"
}

variable "api_port" {
  description = "API Port"
  type        = string
  default     = "8000"
}

variable "nome_app" {
  description = "Application Name"
  type        = string
  default     = "Portfolio Backend API"
}

variable "origens_permitidas" {
  description = "CORS Allowed Origins"
  type        = string
}

variable "regex_origens_permitidas" {
  description = "CORS Allowed Origins Regex"
  type        = string
}

variable "otlp_endpoint" {
  description = "OTLP Endpoint for Traces"
  type        = string
  default     = ""
}

variable "resend_api_key" {
  description = "Resend API Key"
  type        = string
  sensitive   = true
}

variable "resend_from_email" {
  description = "Resend From Email"
  type        = string
}

variable "resend_to_email" {
  description = "Resend To Email"
  type        = string
}

variable "trusted_proxy_depth" {
  description = "Trusted Proxy Depth"
  type        = number
  default     = 1
}
