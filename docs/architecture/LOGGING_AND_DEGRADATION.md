# Structured Logging & Degraded Mode

## 1. Useful vs Pretty Logs: Automated Action Triggers

Instead of outputting raw text dumps, the system outputs structured JSON logs. This enables automated tracing and immediate action rules.

### Identified Pattern & Action Rule
**Pattern Identified:** A repetitive chain of `psycopg2.OperationalError` triggers within 5 seconds under high load.
**Rule:** `IF (Database_Timeout_Count > 5 in 10s) AND (CPU_Utilization > 85%)`

**Action (Automated):**
1. **Trip Circuit Breaker** immediately (bypass halfway open state).
2. **Activate Drain Mode** — purge the lowest priority 20% of the async queue.
3. **Emit `System_Degraded` event** to telemetry tools.

#### Structured Log Example
```json
{
  "timestamp": "2026-04-20T19:05:00Z",
  "level": "CRITICAL",
  "event": "circuit_breaker_tripped",
  "actor": "chaos_latency_injector",
  "metrics": {
    "error_rate": 0.08,
    "p95_latency_ms": 3500,
    "active_connections": 100
  },
  "automated_action_taken": "queue_drained",
  "suggested_human_action": "Verify database instance capacity or expand pool size."
}
```

---

## 2. Degraded Mode: The Survival Payload

When the system triggers "Survival Mode" due to the aforementioned rule, it alters the standard API response wrapper. This dictates frontend behavior to save client resources and mask failure elegantly.

### JSON Structure Strategy (Backend -> React)

```json
{
  "status": "success",
  "data": {
    // Normal or cached data payload
  },
  "system_telemetry": {
    "status": "degraded",
    "active_circuit_breakers": 1,
    "ui_directives": {
      "disable_animations": true,
      "hide_secondary_metrics": true,
      "throttle_polling": 30000
    },
    "message": "System is operating under heavy load. Non-essential features are disabled."
  }
}
```
*Frontend Reaction:* Upon receiving `disable_animations: true`, React strips Framer Motion wrappers and uses static renders to save the client's CPU while the slow response is processed.
