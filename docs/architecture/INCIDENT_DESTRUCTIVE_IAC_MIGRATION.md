# Incident Post-Mortem: INC-008
## 🛑 Destructive IaC Migration (Free Tier Constraints)

**Date:** 2026-05-07  
**Severity:** P2 (Planned Maintenance / Migration Downtime)  
**Status:** Resolved (Migration Complete)  
**Downtime:** 14 Hours

---

### 📝 Executive Summary
To finalize the transition of the backend infrastructure to a fully managed Terraform state, the system underwent a "Cold Migration." Due to platform constraints in the Koyeb Free Tier—specifically the inability to maintain parallel resource ownership or multiple active services—a zero-downtime migration was impossible. The existing manual deployment was decommissioned to allow Terraform to claim ownership of the domain and network hooks.

### 🔍 Symptoms
- **Service Status:** API unavailable during the 14-hour migration window.
- **Errors:** `502 Bad Gateway` (Platform-level) while resources were being reconciled.
- **Context:** The transition from "ClickOps" to "IaC" required a clean slate to avoid state drift and resource conflicts.

### 🕵️ Root Cause Analysis
1.  **Platform Quotas:** The Koyeb Free Tier enforces a 1-service-per-app limit and strict domain exclusivity.
2.  **Resource Ownership Conflict:** The manual deployment held the CNAME and SSL hooks for `api.argenisbackend.com`. Terraform could not provision a new service with the same domain without the previous resource being destroyed first.
3.  **State Reconciliation:** Ensuring 100% reproducibility required purging all unmanaged resources to guarantee that the Terraform state reflected the absolute truth of the production environment.

### 🛡️ Mitigation & Execution
1.  **Manual Decommissioning:** Purged legacy apps and services to release domain hooks.
2.  **IaC Provisioning:** Executed `terraform apply` to recreate the entire stack (App, Service, Secrets, Domain, Regional configuration) in a single atomic operation.
3.  **Regional Optimization:** Leveraged the window to migrate the backend to the `was` (Washington D.C.) region for better colocation with downstream dependencies.
4.  **Credential Rotation:** Re-established Resend API keys and SMTP identities within the new IaC-managed secret vault.

### 📈 Reliability Enhancements
- **100% Reproducibility:** Verified that the entire backend stack can be recreated from a blank slate using only the Terraform configuration and GitHub Secrets.
- **Operational Consistency:** Eliminated "shadow configuration" by centralizing all environment variables in the Koyeb Secrets vault managed by code.

### 💡 Lessons Learned
- **Provider Constraints dictate Strategy:** In restricted environments, maintenance windows must be accepted as a trade-off for infrastructure consistency and reproducibility.
- **The "Unmanaged" Tax:** Migrating unmanaged infrastructure into IaC may require destructive reconciliation steps when provider ownership and state cannot be safely imported or shared.
- **Verification through Destruction:** A successful "from-scratch" deployment is the ultimate test of IaC health.
