# Case Study: INC-002 (Cold Start Latency)

**Confidence Score**: `High` (Real production data, >2 sources: Koyeb metrics, Supabase connection logs).
**Tag**: `REAL`

### 1. Context
- **Service**: Portfolio API data endpoints (`/projects`, `/about`, `/stack`).
- **Timeline**: v1.2.0 to v1.4.1.
- **Impact**: Significant latency degradation for initial user page loads.

### 2. Symptom
First API requests following periods of low traffic exhibited P95 latency between 280ms and 400ms. This occurred despite an active 14-minute cron keep-alive targeting the `/health` endpoint.

### 3. Initial Hypotheses
Assumed the 14-minute cron interval was insufficient to prevent Koyeb's free-tier container sleep cycle.

### 4. Partial/Human Cause
Diagnostic error (wrong bottleneck identified). The keep-alive cron was working; the container was warm. However, `/health` did not require a database connection. The latency was entirely due to the TCP/TLS overhead of establishing a new connection to Supabase (PostgreSQL) on the first read request.

### 5. Before vs After

| Metric | Before (PostgreSQL) | After (JSONRepository) |
| :--- | :--- | :--- |
| **Data Read P95 Latency** | ~320ms | < 50ms |
| **External I/O on Read** | TCP + TLS handshake | 0 (In-memory) |
| **State Storage** | Supabase DB | Memory-mapped JSON |

### 6. Real vs Reproduced
- **Source**: `REAL`.
- **Limitations**: Metrics extracted directly from Koyeb edge logs and Supabase connection tracking. No simulated data.

### 7. Lessons & Guardrails
- **Lesson**: Utilizing remote transactional databases for static, read-heavy data introduces blocking connection overhead that negates container readiness.
- **Guardrail**: Implemented `JSONRepository` (ADR-05). Static content is loaded into memory at container boot. PostgreSQL usage is now strictly gated to mutations (e.g., `POST /contact`).
