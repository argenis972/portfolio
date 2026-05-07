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

resource "koyeb_domain" "backend" {
  name = "api.argenisbackend.com"
}

resource "koyeb_app" "portfolio" {
  name = "argenis-portfolio"
}

resource "koyeb_service" "backend" {
  app_name = koyeb_app.portfolio.name

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

    env {
      key   = "AMBIENTE"
      value = var.ambiente
      type  = "PLAINTEXT"
    }

    env {
      key   = "API_HOST"
      value = var.api_host
      type  = "PLAINTEXT"
    }

    env {
      key   = "API_PORT"
      value = var.api_port
      type  = "PLAINTEXT"
    }

    env {
      key   = "DATABASE_URL"
      value = var.database_url
      type  = "PLAINTEXT"
    }

    env {
      key   = "METRICS_BASIC_AUTH_USERNAME"
      value = var.metrics_basic_auth_username
      type  = "PLAINTEXT"
    }

    env {
      key   = "METRICS_BASIC_AUTH_PASSWORD"
      value = var.metrics_basic_auth_password
      type  = "PLAINTEXT"
    }

    env {
      key   = "NOME_APP"
      value = var.nome_app
      type  = "PLAINTEXT"
    }

    env {
      key   = "ORIGENS_PERMITIDAS"
      value = var.origens_permitidas
      type  = "PLAINTEXT"
    }

    env {
      key   = "OTLP_ENDPOINT"
      value = var.otlp_endpoint
      type  = "PLAINTEXT"
    }

    env {
      key   = "REDIS_URL"
      value = var.redis_url
      type  = "PLAINTEXT"
    }

    env {
      key   = "REGEX_ORIGENS_PERMITIDAS"
      value = var.regex_origens_permitidas
      type  = "PLAINTEXT"
    }

    env {
      key   = "RESEND_API_KEY"
      value = var.resend_api_key
      type  = "PLAINTEXT"
    }

    env {
      key   = "RESEND_FROM_EMAIL"
      value = var.resend_from_email
      type  = "PLAINTEXT"
    }

    env {
      key   = "RESEND_TO_EMAIL"
      value = var.resend_to_email
      type  = "PLAINTEXT"
    }

    env {
      key   = "SENTRY_DSN"
      value = var.sentry_dsn
      type  = "PLAINTEXT"
    }

    env {
      key   = "TRUSTED_PROXY_DEPTH"
      value = tostring(var.trusted_proxy_depth)
      type  = "PLAINTEXT"
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

    regions = ["fra"]
  }
}
