# Design Decisions & Ambiguity Resolutions

This document records every significant ambiguity encountered during development and the reasoning behind each resolution. The assignment spec left many choices open — this explains what I chose, why, and what would change if the context were different.

---

## 1. Shared-Schema Multi-Tenancy (not separate schemas, not separate databases)

**The ambiguity:** The spec says "multi-tenant" but doesn't specify the isolation mechanism.

**Decision:** Shared database, shared schema, with `tenant_id` foreign key on every data table.

**Why:**
- **Operational simplicity.** One Django migration path. One database backup. One connection pool. Schema-per-tenant (PostgreSQL's `CREATE SCHEMA`) requires `django-tenants` or `django_multitenant`, which modify the ORM's query pipeline and complicate testing. Database-per-tenant requires a router and makes cross-tenant admin queries nearly impossible.
- **Django's strength is the ORM.** Adding `.filter(tenant=request.tenant)` to querysets is straightforward and testable. The `TenantMiddleware` pattern (resolve tenant from request, attach to queryset) is well-understood.
- **Scale fit.** For an early-stage ESG platform with <100 tenants, each uploading a few CSV files per month, there is no performance reason for physical isolation. The composite indexes `(tenant_id, scope, record_date)` keep queries fast.
- **Trade-off.** No hard data isolation between tenants. A bug in a queryset filter could leak data. Mitigations: tenant-scoped manager methods, middleware enforcement, test coverage. At enterprise scale or with compliance requirements (SOC 2 Type II), you'd revisit this.

**What would change my mind:** A customer requiring contractual data isolation (common in financial services), or >1,000 tenants where index cardinality becomes a concern.

---

## 2. SAP Flat File CSV (not IDoc, not OData, not RFC)

**The ambiguity:** The spec says "SAP" but doesn't specify the integration method.

**Decision:** Accept CSV flat-file exports from SAP transaction MB51 (Material Document List) or equivalent custom ABAP reports.

**Why:**
- **Accessibility.** Every SAP installation supports CSV/Excel export from ALV grid reports. IDoc requires SAP middleware (PI/PO or CPI), OData requires SAP Gateway setup, and RFC requires ABAP function modules. Most mid-market companies can export a CSV from MB51 immediately, without SAP Basis involvement.
- **Real-world prevalence.** In ESG/sustainability teams, the most common data collection pattern is: someone runs MB51 with a date range and material filter, exports to Excel, and emails it. This is the format we should accept first.
- **SAP header handling.** We support both German technical names (MBLNR, BWART, MATNR, WERKS, MENGE, MEINS, BUDAT) and English equivalents via the `SAP_HEADER_MAP` in `parsers.py`. The parser is case-insensitive and strips whitespace, which handles the common "export from ALV then open in Excel" workflow that introduces formatting inconsistencies.
- **Date format flexibility.** SAP exports dates in `DD.MM.YYYY` (German locale, which is the default for many SAP installations) or `YYYYMMDD` (SAP internal format, seen when exporting via SE16/SE16N). Our `date_utils.parse_date()` handles both, plus ISO format as a fallback.

**What we lose:** Real-time data flow. With CSV upload, data freshness depends on how often someone runs the export. With OData/RFC, we could poll SAP for new material documents daily or on demand.

**Production path:** Phase 1 (this) is CSV upload. Phase 2 would add an SAP CPI iFlow that pushes material documents via webhook when movement type 261 is posted. Phase 3 would be a direct OData connection to SAP S/4HANA's Material Document API (`API_MATERIAL_DOCUMENT_SRV`).

---

## 3. Utility CSV Upload (not PDF parsing, not Green Button API)

**The ambiguity:** The spec says "utility portals" but doesn't specify whether we parse PDFs, call APIs, or accept CSVs.

**Decision:** Accept CSV exports from utility portals or facility management systems.

**Why:**
- **Format standardization.** Utility bill PDFs vary wildly — different layouts per utility, multi-page bills, summary vs. detail views, sometimes scanned images. PDF parsing (via Tabula, Camelot, or OCR) achieves ~70-85% accuracy in the best case and requires per-utility template configuration. CSV is a tractable problem; PDF parsing is not, for an intern project timeline.
- **Green Button XML is rare in practice.** The ESPI/Green Button standard exists but adoption outside of California residential utilities is limited. Most commercial/industrial customers download billing data as CSV from their utility's business portal or from an energy management platform (EnergyCAP, Schneider Electric, Urjanet/Arcadia).
- **Column flexibility.** Our `UTILITY_HEADER_MAP` accepts multiple column name variations: `Billing_Period_Start`, `billing_start`, `start_date`, etc. This handles the reality that no two utilities format their CSVs identically.

**What we lose:** Automation. With Green Button Connect My Data (CMD), the utility pushes data directly to our platform via OAuth2. This eliminates manual downloads entirely, which is the eventual goal.

---

## 4. Travel CSV Upload (not Concur API, not Navan webhook)

**The ambiguity:** The spec says "corporate travel" but doesn't specify the integration method.

**Decision:** Accept CSV exports from travel expense platforms (SAP Concur, Navan, Chrome River).

**Why:**
- **Concur's export is highly customizable.** Per SAP's own documentation, the CSV export schema is configured by each organization's Concur administrator (Administration > Expense > File Export). There is no single standard format. We handle this with flexible header mapping.
- **API complexity.** Concur's V4 API (`/api/v4.0/expense/reports`) requires OAuth2 with company-level authorization, scoped API keys, and webhook configuration for status change notifications. For an intern project, CSV upload is the right starting point.
- **Distance computation fallback.** Travel CSVs often include departure/arrival IATA codes but NOT distance. Our parser computes great-circle distance from IATA coordinates when `distance_km` is missing. This is documented as an approximation — actual flight paths are 5-10% longer.

**Production path:** Connect to Concur's Extract API V1 (`/api/expense/extract/v1.0/`) which provides scheduled batch exports. Or use Concur's Event notifications to receive webhook callbacks when reports are approved.

---

## 5. Synchronous Processing (not Celery/Redis)

**The ambiguity:** The spec doesn't specify whether file processing should be async.

**Decision:** Parse and normalize CSVs synchronously within the Django request-response cycle.

**Why:**
- **File sizes are small.** A 35-row SAP export processes in <100ms. Even a 1,000-row utility bill takes <2 seconds. The overhead of Celery (Redis broker, worker process, result backend, task serialization) is unjustified for this workload.
- **Simpler error handling.** Synchronous processing means the user sees the result immediately: "34 valid rows, 1 error." With async processing, we'd need a polling/websocket mechanism to update the UI when the job completes, plus retry logic for transient failures.
- **Deployment simplicity.** No Redis server, no Celery worker process, no process supervisor (supervisord/systemd). The app runs with `manage.py runserver` and works.

**What breaks at scale:** A 100,000-row CSV would take >30 seconds and likely hit Gunicorn's worker timeout. At that point, you need:
1. Celery with Redis broker for task queuing
2. `django-channels` or SSE for progress updates
3. Chunked processing (process 5,000 rows per task, chain tasks)
4. Dead-letter queue for failed tasks

See TRADEOFFS.md for the full analysis.

---

## 6. Row-Level Approval (not batch-level)

**The ambiguity:** Should analysts approve individual records or entire uploads?

**Decision:** Row-level review workflow on `EmissionRecord` (pending → reviewed → approved → locked).

**Why:**
- **Data quality varies within an upload.** A utility CSV might contain 24 actual reads and 1 estimated read that's 3× normal. An SAP export might have 30 valid consumption records and 1 reversal (movement type 102). The analyst needs granularity to approve the good data and flag the suspicious data.
- **Auditor expectations.** GHG verification auditors expect to see evidence that individual data points were reviewed, not just batches. ISO 14064-3 verification requires "assessment of the accuracy of the data."
- **Dashboard filtering.** The review dashboard filters by `status`, which is per-record. This makes the "pending review" queue immediately useful.

**Trade-off:** Row-level approval is tedious for large uploads. An analyst processing 1,000 utility readings doesn't want to click "approve" 1,000 times. Mitigations we'd add:
- Bulk approve action: "Approve all rows in this upload where consumption is within ±20% of the facility's historical average."
- Smart flagging: auto-flag rows where values exceed 2σ from the rolling mean.

---

## 7. Separate AuditLog Table (not django-simple-history)

**The ambiguity:** How to implement audit trails.

**Decision:** Custom `AuditLog` model with explicit action types and JSON change diffs.

**Why:**
- **Storage efficiency.** `django-simple-history` creates a complete copy of the model row on every `save()`. For `EmissionRecord` with 15+ fields, that's ~1KB per change. Our AuditLog stores only the changed fields as a JSON diff: `{"status": {"old": "pending", "new": "approved"}}` — typically <200 bytes.
- **Cross-model querying.** "Show me everything user X did today" is one query: `AuditLog.objects.filter(user=x, timestamp__date=today)`. With `simple-history`, you'd UNION across `HistoricalEmissionRecord`, `HistoricalIngestionJob`, etc.
- **Semantic richness.** Our `Action` enum includes `approve`, `flag`, `lock`, `upload` — business-level actions, not just CRUD operations. An auditor can filter for all `lock` events to see when reporting periods were finalized.
- **Write-once guarantee.** AuditLog entries have no `update` or `delete` methods exposed. The `auto_now_add` timestamp is immutable. `simple-history` entries are technically mutable if someone has database access.

---

## 8. Rule-Based Scope Classification with Analyst Override

**The ambiguity:** How to assign GHG Protocol scopes to emission records.

**Decision:** Auto-classify scope by source type, with a `scope_override` field for analyst correction.

**Why:**
- **Source type is a strong signal.** SAP fuel procurement → Scope 1 is correct for >95% of cases. Utility electricity → Scope 2 is correct for >98% of cases. Travel → Scope 3 Category 6 is correct for >99% of cases. A rules engine or ML classifier would be overengineered.
- **Edge cases exist but are rare.** Diesel purchased via SAP but used in a contractor's vehicle might be Scope 3 (not Scope 1). Electricity for a subleased floor might be Scope 3 Category 13 (downstream leased assets). These are best handled by analyst judgment, not rules.
- **Override + mandatory reason = audit trail.** `scope_override` is paired with `override_reason`, and both are captured in the AuditLog. An auditor can see: "Analyst X reclassified this diesel record from Scope 1 to Scope 3 because: 'Diesel supplied to third-party logistics contractor per contract §4.2.'"

---

## 9. UUIDs as Primary Keys

**The ambiguity:** Integer PKs vs. UUIDs.

**Decision:** `uuid.uuid4` as the PK for all models.

**Why:**
- **Security.** Integer PKs expose record counts and enable enumeration attacks. UUID PKs are opaque — you can't guess other tenants' record IDs.
- **Distributed systems readiness.** If we ever shard or run multiple application servers, UUIDs don't collide. Integer sequences require coordination.
- **API aesthetics.** `/api/emissions/a1b2c3d4-...` doesn't reveal how many records exist. `/api/emissions/47/` tells an attacker there are at least 47 records.

**Trade-off:** UUIDs are larger (16 bytes vs. 4-8 bytes for int), make indexes wider, and slightly slow range queries. For our data volumes (<100k records per tenant), this is immaterial. At millions of records, we'd consider ULIDs (sortable UUIDs) or prefixed IDs.

---

## 10. JSONField for validation_errors and raw_data

**The ambiguity:** How to store per-row validation errors and original source data.

**Decision:** PostgreSQL `jsonb` via Django's `JSONField`.

**Why for `raw_data`:**
- SAP column sets vary by customer. One installation exports 8 columns, another exports 15. A fixed-schema approach would either miss data or require schema changes per customer.
- `jsonb` preserves the original CSV row exactly as received. Critical for auditing.
- PostgreSQL's `jsonb` supports containment queries (`raw_data__contains={"WERKS": "1000"}`) if we ever need to search within raw data.

**Why for `validation_errors`:**
- Errors are heterogeneous: a row might have `[{"type": "missing_field", "field": "quantity"}, {"type": "invalid_date", "field": "posting_date"}]`. A normalized errors table would be a join per error per row.
- The frontend consumes the error array directly to render inline error badges in the data grid. No transformation needed.
- Errors are read-once (during review) and never updated. There's no query pattern that benefits from normalization.

---

## 11. emission_factor_value as a Snapshot (not a live FK lookup)

**The ambiguity:** Should EmissionRecord store the factor value used, or just reference the factor and look it up at query time?

**Decision:** Store both `emission_factor_id` (reference) and `emission_factor_value` (snapshot).

**Why:**
- **Reproducibility.** When an auditor asks "how did you get 6,750 kg CO₂e for this record?", the answer must be: "2,500 L × 2.70 kg/L = 6,750 kg." If we only stored the FK, and the factor was later updated to 2.72, we'd show a different number than what was originally calculated.
- **Factor versioning.** DEFRA publishes new factors every year. When we load 2025 factors and deactivate 2024 factors, existing 2024 records must still show the 2024 factor value that was actually used.
- **Performance.** Dashboard aggregation queries (`SUM(co2e_kg) GROUP BY scope, reporting_period`) don't need to join the EmissionFactor table.

---

## Questions I'd Ask the PM

If I had access to a product manager before building, I'd ask:

### Q1: What's the expected upload frequency and file size?
"Are customers uploading monthly CSVs with 50-100 rows, or quarterly dumps with 50,000 rows? This determines whether synchronous processing is viable or whether we need Celery from day one."

### Q2: Do customers need market-based Scope 2 reporting?
"Location-based Scope 2 uses grid-average factors (which we support). Market-based requires tracking RECs, supplier contracts, and residual-mix factors. That's a major scope expansion — should we plan for it?"

### Q3: How do tenants want to handle multi-facility reporting?
"Do all facilities roll up into one report, or does each facility get its own report? Do they need the GHG Protocol's equity-share vs. operational-control boundary approach? This affects how we structure the Tenant→Facility relationship."

### Q4: What's the approval workflow in practice?
"Does one analyst review everything, or are there facility-level analysts who can only approve their site's data? Do we need approval delegation (analyst approves, but admin signs off)? The current flat four-role model might not be enough."

### Q5: Should we support re-processing when emission factors are updated?
"When DEFRA publishes 2025 factors, do customers want to retroactively recalculate all 2024 records? Or do they keep the original calculations and start using new factors going forward? This has significant implications for the data model — do we version emission records or treat them as immutable once approved?"

### Q6: What calendar does the reporting period follow?
"Most companies report on calendar years (Jan-Dec), but some use fiscal years (Apr-Mar in the UK, Oct-Sep in the US federal government). Do we need configurable reporting periods, or is YYYY-MM sufficient?"

### Q7: Are there data retention requirements?
"GHG Protocol recommends keeping base-year data indefinitely. Some regulations (EU CSRD) require 5+ years of historical data. Should we build soft-delete with retention policies, or is hard-delete acceptable?"
