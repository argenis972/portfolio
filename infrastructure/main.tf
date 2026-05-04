terraform {
  required_providers {
    koyeb = {
      source  = "koyeb/koyeb"
      version = "~> 0.2"
    }
  }
}

provider "koyeb" {
  token = var.koyeb_token
}

resource "koyeb_app" "portfolio" {
  name = "argenis-portfolio"
}

resource "koyeb_service" "backend" {
  app_id = koyeb_app.portfolio.id
  name   = "api"

  definition {
    type = "GIT"

    git {
      repository = "github.com/Argenis1412/portfolio"
      branch     = "main"
      workdir    = "/"
    }

    ports {
      port     = 8000
      protocol = "HTTP"
    }

    routes {
      path = "/"
      port = 8000
    }

    env {
      key   = "ENVIRONMENT"
      value = "production"
    }

    env {
      key   = "DATABASE_URL"
      value = var.database_url
    }

    env {
      key   = "REDIS_URL"
      value = var.redis_url
    }

    env {
      key   = "SENTRY_DSN"
      value = var.sentry_dsn
    }

    health_checks {
      http {
        path = "/health"
        port = 8000
      }
      grace_period = 30
      interval     = 30
      restart_limit = 3
      timeout      = 10
    }

    regions = ["fra"]
    instance_types = ["free"]
  }
}
