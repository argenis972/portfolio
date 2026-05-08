# ADR-18: Infrastructure as Code Strategy

**Status:** Accepted
**Date:** 2026-05-04
**Version:** v1.7.0

## Context

To demonstrate operational excellence, the portfolio required an Infrastructure as Code (IaC) layer. However, the system relies on multiple third-party SaaS providers (Koyeb for compute, Supabase for PostgreSQL, Upstash for Redis) that have varying levels of support for Terraform, especially regarding their free tiers.

Attempting to fully automate the provisioning of all these services often leads to overly complex modules, unsupported providers, or brittle scripts that are difficult for reviewers to run.

## Decision

We will provision a Minimum Viable IaC setup using Terraform. This setup is strictly scoped to:
- The Koyeb application and service configuration.
- Environment variable injection (`TF_VAR_*`).

We are intentionally leaving third-party stateful services (Upstash Redis, Supabase) as manual setup steps.

## Rationale

1. **Clarity over Automation:** The primary goal of this repository is to serve as an engineering portfolio. A clear, readable Terraform configuration that provisions the core compute layer in `< 10 commands` is more valuable than a complex, fragile script that attempts to automate everything.
2. **Reproducibility Focus:** This setup prioritizes the reproducibility of the backend service (how the container runs, scaling, health checks, ports) over full infrastructure parity.
3. **Free Tier Limitations:** Automating the free-tier setups of external database providers often violates the goal of a clean codebase due to provider constraints or lack of official support.

## Consequences

- **Positive:** Any developer or reviewer can understand the deployment topology in 5 minutes by reading `infrastructure/main.tf`.
- **Positive:** The IaC layer remains simple, maintainable, and highly reliable.
- **Negative:** Bootstrapping a completely new environment from scratch still requires manual intervention to create the database and Redis instances before running Terraform. This is an accepted trade-off documented in `infrastructure/README.md`.
