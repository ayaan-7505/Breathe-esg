# TRADEOFFS.md — What We Chose Not to Build

This document covers three features we deliberately excluded from the prototype scope, why we made that call, and what the path to production would look like for each.

---

## 1. Asynchronous File Processing (Celery / Redis)

### What it would be

A task queue (Celery with Redis or RabbitMQ as the broker) to process uploaded CSV files in the background. The upload endpoint would return immediately with a job ID, and a worker process would parse, validate, and normalize the file asynchronously. The frontend would poll or use WebSockets for progress updates.

### Why we didn't build it

Our prototype handles files synchronously in the Django request-response cycle. For the data volumes we're demonstrating — sample files with 25–35 rows — this adds zero perceptible latency. Even at 10,000 rows, synchronous processing on a modern server takes under 5 seconds.

Adding Celery introduces three deployment dependencies that meaningfully complicate the 4-day timeline:

1. **Redis** — needs a separate managed service on Render ($0/mo free tier, but another thing to configure and monitor).
2. **Celery worker** — a second process that must be deployed, scaled, and kept alive alongside the web process. Render charges separately for background workers.
3. **Task state management** — we'd need to handle retries, dead-letter queues, idempotency, and race conditions between the worker and the web process.

The net effect: ~1.5–2 days of work for infrastructure that doesn't improve the demo and introduces failure modes we can't easily debug in a 4-day window.

### What breaks without it

- **Files over ~50k rows** will cause request timeouts (Render's default is 30 seconds for free-tier).
- **Concurrent uploads** from multiple analysts will block Django worker threads.
- **No progress feedback** — the user stares at a spinner until the upload completes or times out.
- **No retry logic** — if parsing fails midway, the user has to re-upload the entire file.

### What we'd need to add it

- `celery` + `redis` packages in requirements.txt
- A `celery.py` config in the Django project
- Refactor `ingestion/views.py` to dispatch `run_parser.delay(job.pk)` instead of `run_parser(job)`
- A Celery task with `bind=True` for progress tracking via `self.update_state()`
- A `/api/ingestion/jobs/{id}/progress/` endpoint that reads task state
- Frontend polling or SSE/WebSocket integration
- Redis service in `render.yaml`
- A separate worker service in `render.yaml`

**Estimated effort**: 1.5–2 days for a solid implementation with retry logic and progress tracking.

---

## 2. PDF Bill Parsing for Utility Data

### What it would be

An ingestion pathway that accepts PDF utility bills (the most common format facilities teams actually receive), extracts structured data using OCR or PDF text extraction, and feeds it into the same normalization pipeline as CSV uploads.

### Why we didn't build it

PDF bill parsing is one of the hardest problems in data ingestion. Every utility formats their bills differently — different layouts, different fonts, different table structures, different terminology. A parser that works for ConEdison won't work for PG&E, and neither will work for a municipal utility in Germany.

The realistic approaches:

1. **Template-based extraction** (e.g., Camelot, Tabula) — works only if you hand-craft a template per utility provider. Fragile; breaks when the utility changes their bill format.
2. **OCR + LLM extraction** (e.g., Tesseract + GPT-4 Vision) — more flexible but expensive per-document, requires prompt engineering per format, and has non-trivial error rates on scanned bills.
3. **Third-party services** (e.g., AWS Textract, Google Document AI) — best accuracy but adds a cloud dependency, per-page cost, and data residency concerns for ESG data.

None of these are 4-day features. We chose CSV because it's what facilities teams can actually export from their utility portals today. Every major utility portal (Duke Energy, ConEd, PG&E, National Grid) offers CSV or Excel downloads. PDF parsing is a "nice to have" that doesn't block the core workflow.

### What breaks without it

- Facilities teams that *only* receive paper bills or emailed PDFs have to manually enter data or transcribe to CSV first.
- This is probably 20–30% of real-world utility data, especially for smaller utilities and international sites.

### What we'd need to add it

- A PDF text extraction library (`pdfplumber` or `PyMuPDF`) for digitally-generated PDFs
- Tesseract OCR (`pytesseract`) for scanned PDFs
- A template registry mapping utility providers to extraction rules (regex patterns, table coordinates)
- Validation heuristics to catch OCR errors (e.g., "does this kWh value make physical sense for this meter?")
- A manual correction UI for when extraction gets it wrong
- Optionally: an LLM-based extraction pipeline for unstructured bills

**Estimated effort**: 3–5 days for a single-utility-provider MVP; 2–4 weeks for a multi-provider solution with a template registry.

---

## 3. Real-Time API Integration with SAP / Concur

### What it would be

Direct API connectors that pull data from SAP (via OData or RFC) and Concur (via REST API) in real-time or on a schedule, eliminating the need for manual file uploads.

### Why we didn't build it

**SAP**: Connecting to a live SAP system requires:
- An SAP account with appropriate authorization objects (M_BEST_BSA, M_MSEG_WWA, etc.)
- Network access (SAP systems sit behind corporate firewalls; you'd need SAP Cloud Connector or an on-prem gateway)
- Understanding of the specific SAP modules and customizations the client has deployed
- OAuth2 configuration for SAP BTP or certificate-based auth for RFC

No two SAP installations expose the same API surface. The OData services available depend on which SAP modules are activated, which custom transactions exist, and what the Basis team has configured. Building a "generic SAP connector" is a multi-month project.

**Concur**: The SAP Concur API is better documented, but still requires:
- OAuth2 with company-level tokens (not just user tokens)
- Handling pagination, rate limiting, and incremental sync
- Mapping Concur's expense report schema to our internal model
- Dealing with Concur's various editions (Standard, Professional, Professional with Intelligence)

File upload is the pragmatic choice because it works on day one of client onboarding. The client's IT team doesn't need to configure anything — the sustainability lead just downloads a CSV from their existing system and uploads it.

### What breaks without it

- **Manual process** — someone has to remember to export and upload data periodically.
- **Data freshness** — there's always a lag between when data appears in SAP/Concur and when it's in our system.
- **Human error** — wrong file, wrong date range, accidentally uploading the same file twice (though we handle duplicates).

### What we'd need to add it

For each connector:
- OAuth2 flow with token refresh and secure credential storage
- A scheduled sync job (Celery beat or Django-Q2) that runs daily/weekly
- Incremental sync logic (track last-sync timestamp, only pull new/modified records)
- Error handling with exponential backoff and alerting
- A connector configuration UI where admins set up credentials and mapping rules
- Data mapping configuration (which SAP fields map to which internal fields)

**Estimated effort**: 1–2 weeks per connector for an MVP; 4–6 weeks for production-grade connectors with error handling, retry logic, and monitoring.

---

## Why these three?

These are the three features that would add the most value in a production deployment, ranked by client impact:

1. **API connectors** — eliminate the manual upload step entirely; biggest UX win for analysts.
2. **Async processing** — necessary for enterprise-scale files (100k+ rows per month).
3. **PDF parsing** — unlocks utility data from facilities that can't export CSV.

We chose to build a sharp, defensible prototype with clean file upload → parse → normalize → review → lock workflow instead of spreading thin across infrastructure features that would have been half-baked in 4 days. Each of these features is a "next sprint" item, not a "day one" requirement.
