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

resource "koyeb_domain" "backend" {
  name     = "api.argenisbackend.com"
  app_name = koyeb_app.portfolio.name
}

locals {
  # All potential environment variables
  all_env_vars = {
    "AMBIENTE"                    = var.ambiente
    "API_HOST"                    = var.api_host
    "API_PORT"                    = var.api_port
    "DATABASE_URL"                = var.database_url
    "METRICS_BASIC_AUTH_USERNAME" = var.metrics_basic_auth_username
    "METRICS_BASIC_AUTH_PASSWORD" = var.metrics_basic_auth_password
    "NOME_APP"                    = var.nome_app
    "ORIGENS_PERMITIDAS"          = var.origens_permitidas
    "OTLP_ENDPOINT"               = var.otlp_endpoint
    "REDIS_URL"                   = var.redis_url
    "REGEX_ORIGENS_PERMITIDAS"    = var.regex_origens_permitidas
    "RESEND_API_KEY"              = var.resend_api_key
    "RESEND_FROM_EMAIL"           = var.resend_from_email
    "RESEND_TO_EMAIL"             = var.resend_to_email
    "SENTRY_DSN"                  = var.sentry_dsn
    "TRUSTED_PROXY_DEPTH"         = tostring(var.trusted_proxy_depth)
  }

  # Identify which keys have non-empty values (this list of names is NOT sensitive)
  # We use nonsensitive() to tell Terraform it's safe to use these as resource keys
  env_vars_to_create = nonsensitive([for k, v in local.all_env_vars : k if v != "" && v != null])
}

resource "koyeb_secret" "vars" {
  for_each = toset(local.env_vars_to_create)
  name     = "portfolio-${lower(replace(each.key, "_", "-"))}"
  value    = local.all_env_vars[each.key]
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
      for_each = local.env_vars_to_create
      content {
        key    = env.value
        secret = koyeb_secret.vars[env.value].name
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
