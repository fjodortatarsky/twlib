# Security issues report (Python)

**Scope inspected**
- `frontend/` (`run.py`, `wsgi.py`, `app/*.py`, `tests/tests_marc.py`)
- `picstore/` (`app.py`, `auth.py`, `config.py`, `storage.py`)
- Deployment hints: `docker-compose.yaml`, `docker-compose.dev.yaml`

Focus: injection, auth/session/secrets, unsafe server config, parsing of untrusted data, path handling, and information exposure.

## Findings (prioritized)

### 1. High — SRU/CQL query injection via unescaped user input
**Where**
- `frontend/app/sru_client.py:158,397` — letter queries built with `f'...="{letter}*"'`
- `frontend/app/sru_client.py:539,542,545,548,565,569,573,577` — search queries built with `f'...="{query}"'` / `cql.anywhere="{query}"`
- `frontend/app/sru_client.py:191,359,413` — record IDs interpolated into `rec.id=...`
- `frontend/app/routes.py:48-49,68-74,118,259,272-275,289` — `q/attr/letter/...` taken from request/URL and passed into SRU calls (letter only uppercased, not validated as a single allowed character)

**Why it matters**
- Values are embedded into CQL/CCL/PQF query strings without escaping or strict validation. Inputs containing quotes, wildcards, or query syntax can alter query structure.
- Depending on the Zebra/SRU backend, this can enable query manipulation, unauthorized data retrieval patterns, or denial-of-service (expensive/broad queries). At minimum it is a correctness and input-trust boundary issue.

**Notes**
- `page/sort/category/per_page` are better constrained in routes (`type=int`, allowlists/comparisons in places), but `query`, `letter`, and path IDs are not safely encoded for the query language.

**Recommended remediation**
- Enforce strict allowlists/validation (e.g. `letter` as a single expected character; validate `authority_id`/`publication_id`/`department_id` format; centralize `attr/sort/category` checks).
- Escape/parameterize values for the SRU/CQL/CCL dialect in use (or use a safe query builder). Never interpolate raw user/ID values into query strings.
- Add tests for inputs containing `"`, `\`, `)`, wildcards, and backend-relevant operators.

### 2. High — Hardcoded secrets and insecure default authentication (picstore)
**Where**
- `picstore/config.py:8` — `SECRET_KEY = "picstore-dev-secret-do-not-use-in-production"`
- `picstore/config.py:12` — `SESSION_COOKIE_SECURE = False` (hardcoded)
- `picstore/auth.py:15` — `STUB_USERS = {"admin": "admin"}`
- `picstore/app.py:16` — loads config as-is; `docker-compose.yaml:56-64` shows no secret/auth env overrides

**Why it matters**
- A fixed, known Flask secret key allows session forgery/tampering if deployed as-is.
- Hardcoded `admin/admin` credentials are effectively a built-in backdoor for any exposed instance still using the stub.
- `SESSION_COOKIE_SECURE = False` permits cookies over plain HTTP; acceptable only for local/dev, risky if reused.

**Positive notes**
- CSRF protection and `hmac.compare_digest` are implemented (`picstore/app.py:23-44`, `picstore/auth.py:20-26`), and sessions are rotated on login (`session.clear()`).

**Recommended remediation**
- Load `SECRET_KEY` and credentials from environment/secret store; fail fast if missing in non-dev.
- Remove or gate stub auth behind explicit dev-only config; replace with real authentication/integration.
- Make `SESSION_COOKIE_SECURE`, `HttpOnly`, and `SameSite` environment-driven with secure production defaults.

### 3. High — Debug server exposed on all interfaces in entry scripts
**Where**
- `frontend/run.py:15` — `app.run(host="0.0.0.0", port=5000, debug=True)`
- `picstore/app.py:273` — `app.run(host="0.0.0.0", port=5001, debug=True)`
- `docker-compose.dev.yaml` — enables dev/debug mode (`FLASK_ENV=development`, `FLASK_DEBUG=1`, `--reload`)

**Why it matters**
- Flask debug mode on a network-reachable interface can expose an interactive debugger/tracebacks and internal state if triggered in an unsafe environment.
- Risk is highest if these scripts or dev compose are used outside a trusted local context. (`wsgi.py` and `docker-compose.yaml` production paths do not set debug.)

**Recommended remediation**
- Ensure `debug=False` for any network-exposed run; keep debug only in explicit local dev tooling.
- Prefer WSGI server entrypoints in production and avoid running `__main__` debug servers in deployed environments.
- Audit compose/env separation so dev flags cannot leak into production.

### 4. Medium — XML parsing of untrusted SRU responses without hardened parser
**Where**
- `frontend/app/parsers.py:12,129,151` — `xml.etree.ElementTree.fromstring(...)`
- `frontend/app/marc.py:1-2,30` — `lxml.etree.fromstring(...)`
- Inputs sourced from remote SRU endpoints (`frontend/app/sru_client.py:64,84`)

**Why it matters**
- Parsing upstream/attacker-influenced XML with default parsers can be exposed to entity-expansion/DTD-related issues depending on parser and configuration.
- Hardening (e.g. `defusedxml` or explicitly disabling DTD/entities/external resolution) is a safer baseline for untrusted feeds.

**Recommended remediation**
- Use `defusedxml` for stdlib parsing or configure parsers to forbid DTD/entity expansion and external resolution.
- Treat SRU responses as untrusted; consider response size/time limits and basic structure validation.

### 5. Medium — Error handling and debug output can leak internal details
**Where**
- `frontend/app/sru_client.py:67-69,86-88,182` — logs exceptions/warnings with base URL/error context
- `frontend/app/routes.py:312-314,318,330` — `print(...)` of internal IDs/counts/categories in request paths
- `frontend/app/sru_client.py:549` — `target` set only in specific branches; unexpected `attr` assigns `cql` but not `target` before `target.search_retrieve(...)` (logic bug that can raise)

**Why it matters**
- Prints/logs in request handling can leak operational/internal data.
- Unhandled exceptions in debug/dev contexts increase information disclosure risk.

**Recommended remediation**
- Replace request-path `print` statements with structured logging at appropriate levels; avoid exposing sensitive/raw upstream errors to users.
- Fix/guard undefined-`target` paths and return controlled errors.

### 6. Low/Informational — Path and upload handling is mostly defensive (picstore)
**Where**
- `picstore/storage.py:22,75-77,173-191,207-208,279-296` — strict `authorityid` regex, fixed filenames under controlled base dir
- `picstore/storage.py:86-114` — Pillow pixel limits, format normalization, atomic-ish writes
- `picstore/app.py:64-79,106-116` — filename/extension/length validation; metadata via `yaml.safe_dump`
- `picstore/storage.py:176` — reads metadata with `yaml.safe_load`

**Assessment**
- No direct path traversal found in image/metadata access paths due to allowlisted IDs and fixed paths.
- Use of `yaml.safe_load`/`safe_dump` and image constraints are positive controls.

### 7. Low — Minor robustness/DoS considerations
**Where**
- `picstore/storage.py:239-271` — module-global `_linked_cache` has TTL but no size bound/eviction
- `frontend/app/sru_client.py:126-144,378-393` — thread pools (up to 15 workers) spawned per request for index-letter checks

**Why it matters**
- Unbounded caches and per-request fan-out/threading can be abused for resource exhaustion under load (availability concern).

**Recommended remediation**
- Add bounds/eviction to in-memory caches and consider rate limiting/caching for expensive index endpoints.
- Keep dependencies up to date (Pillow, Flask, lxml, requests).

## Overall assessment
- **Most critical risks:** unescaped SRU query construction from user input, hardcoded app secret + stub credentials in `picstore`, and debug servers bound to `0.0.0.0` in runnable scripts.
- **Strengths observed:** `picstore` includes several good controls (strict `authorityid` validation, CSRF checks, safe YAML handling, Pillow pixel limits, normalized image output), which reduce file-handling risk but do not offset the higher-priority issues above.
