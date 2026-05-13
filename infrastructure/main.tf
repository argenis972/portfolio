terraform {
  cloud {
    organization = "portafolio"
    workspaces {
      name = "portfolio-infra"
    }
  }

  required_providers {
    koyeb = {
      source  = "koyeb/koyeb"
      version = "~> 0.1"
    }
  }
}

provider "koyeb" {
}

# Triggering deployment with Local Execution Mode to ensure secrets are passed correctly.
# Final sync to include Resend configuration.

resource "koyeb_domain" "backend" {
  name     = "api.argenisbackend.com"
  app_name = koyeb_app.portfolio.name
}

locals {
  # --- INFRASTRUCTURE STABILITY REGISTRY ---
  # To avoid "Secrets do not exist" errors, we must keep Terraform resource keys (the keys in for_each)
  # and Koyeb secret names STABLE, even if we change the key name the application sees.

  raw_secrets_registry = {
    "AMBIENTE"                    = { app_key = "ENVIRONMENT", value = var.environment }
    "NOME_APP"                    = { app_key = "APP_NAME", value = var.app_name }
    "ORIGENS_PERMITIDAS"          = { app_key = "ALLOWED_ORIGINS", value = var.allowed_origins }
    "REGEX_ORIGENS_PERMITIDAS"    = { app_key = "REGEX_ALLOWED_ORIGINS", value = var.regex_allowed_origins }
    "DATABASE_URL"                = { app_key = "DATABASE_URL", value = var.database_url }
    "REDIS_URL"                   = { app_key = "REDIS_URL", value = var.redis_url }
    "SENTRY_DSN"                  = { app_key = "SENTRY_DSN", value = var.sentry_dsn }
    "METRICS_BASIC_AUTH_USERNAME" = { app_key = "METRICS_BASIC_AUTH_USERNAME", value = var.metrics_basic_auth_username }
    "METRICS_BASIC_AUTH_PASSWORD" = { app_key = "METRICS_BASIC_AUTH_PASSWORD", value = var.metrics_basic_auth_password }
    "RESEND_API_KEY"              = { app_key = "RESEND_API_KEY", value = var.resend_api_key }
    "RESEND_FROM_EMAIL"           = { app_key = "RESEND_FROM_EMAIL", value = var.resend_from_email }
    "RESEND_TO_EMAIL"             = { app_key = "RESEND_TO_EMAIL", value = var.resend_to_email }
    "OTLP_ENDPOINT"               = { app_key = "OTLP_ENDPOINT", value = var.otlp_endpoint }
    "API_HOST"                    = { app_key = "API_HOST", value = var.api_host }
    "API_PORT"                    = { app_key = "API_PORT", value = var.api_port }
    "TRUSTED_PROXY_DEPTH"         = { app_key = "TRUSTED_PROXY_DEPTH", value = tostring(var.trusted_proxy_depth) }
  }

  # Filter only non-empty secrets to avoid creating empty ones
  secrets_registry = { for k, v in local.raw_secrets_registry : k => v if v.value != "" && v.value != null }
}

resource "koyeb_secret" "vars" {
  # We use the STABLE legacy key as the Terraform resource key to prevent deletion/recreation
  for_each = nonsensitive(local.secrets_registry)

  # Secret name in Koyeb remains stable (using the legacy key name)
  name  = "portfolio-${lower(replace(each.key, "_", "-"))}"
  value = each.value.value
}

resource "koyeb_app" "portfolio" {
  name = "argenis-portfolio"
}

resource "koyeb_service" "backend" {
  app_name = koyeb_app.portfolio.name

  # Ensure all secrets are fully created before trying to reference them in the service
  depends_on = [koyeb_secret.vars]

  definition {
    name = "api"
    type = "WEB"

    git {
      repository = "github.com/Argenis1412/portfolio"
      branch     = "main"
      workdir    = "/"
      dockerfile {
        dockerfile = "backend/Dockerfile"
      }
    }

    ports {
      port     = 8000
      protocol = "http"
    }

    routes {
      path = "/"
      port = 8000
    }

    # Dynamic generation of environment variables using Secret references
    dynamic "env" {
      for_each = nonsensitive(local.secrets_registry)
      content {
        # The key the application sees (English standard)
        key = env.value.app_key
        # Reference the secret by its stable Terraform key
        secret = koyeb_secret.vars[env.key].name
      }
    }

    health_checks {
      http {
        path = "/health"
        port = 8000
      }
      grace_period  = 30
      interval      = 30
      restart_limit = 3
      timeout       = 10
    }

    scalings {
      min = 0
      max = 1
    }

    instance_types {
      type = "free"
    }

    regions = ["was"]
  }
}

resource "koyeb_service" "worker" {
  app_name = koyeb_app.portfolio.name

  # Ensure all secrets are fully created before trying to reference them in the service
  depends_on = [koyeb_secret.vars]

  definition {
    name = "worker"
    type = "WORKER"

    git {
      repository = "github.com/Argenis1412/portfolio"
      branch     = "main"
      workdir    = "/"
      dockerfile {
        dockerfile = "backend/Dockerfile"
        command    = "python -m app.worker"
      }
    }

    # Dynamic generation of environment variables using Secret references
    dynamic "env" {
      for_each = nonsensitive(local.secrets_registry)
      content {
        key    = env.value.app_key
        secret = koyeb_secret.vars[env.key].name
      }
    }

    scalings {
      min = 0
      max = 1
    }

    instance_types {
      type = "free"
    }

    regions = ["was"]
  }
}

# --- INFRASTRUCTURE STATE MIGRATION ---
# These moved blocks ensure that Terraform renames the resources in the state
# instead of destroying and recreating them, avoiding "name already exists" errors in Koyeb.

moved {
  from = koyeb_secret.vars["ENVIRONMENT"]
  to   = koyeb_secret.vars["AMBIENTE"]
}

moved {
  from = koyeb_secret.vars["APP_NAME"]
  to   = koyeb_secret.vars["NOME_APP"]
}

moved {
  from = koyeb_secret.vars["ALLOWED_ORIGINS"]
  to   = koyeb_secret.vars["ORIGENS_PERMITIDAS"]
}

moved {
  from = koyeb_secret.vars["REGEX_ALLOWED_ORIGINS"]
  to   = koyeb_secret.vars["REGEX_ORIGENS_PERMITIDAS"]
}
