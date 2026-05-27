# SOURCES.md — Data Source Research

For each of the three data sources, this document covers what real-world format we researched, what we learned, how we designed our sample data, and what would break in a real deployment.

---

## 1. SAP — Fuel and Procurement Data

### What we researched

We looked at how SAP Materials Management (MM) exposes material movement data, specifically through transactions that facilities and procurement teams use daily:

- **MB51** — Material Document List. This is the standard SAP report for viewing material movements (goods receipts, goods issues, consumption postings). It can be exported as a flat file (CSV/TSV) via SAP GUI's `System → List → Save → Local File → Unconverted` option.
- **ME2M** — Purchase Orders by Material. Used when procurement teams need to pull purchasing data. Can also be exported as flat files.
- **MIGO** — Goods Movement. The transaction for posting goods receipts (movement type 101), goods issues (201, 261), and returns (102). Each posting creates a material document with a unique MBLNR.

We chose **MB51 flat-file export** because it's the most common way facilities teams actually extract fuel consumption data from SAP. It doesn't require any IT configuration, custom RFC, or API access — the user just runs the report with their filters and hits export.

### What we learned

SAP flat-file exports have several characteristics that make ingestion challenging:

1. **German field names are the default.** Unless someone has customized the SAP GUI language, column headers come out as the underlying field technical names: MBLNR (Materialbelegnummer = material document number), BWART (Bewegungsart = movement type), MATNR (Materialnummer = material number), WERKS (Werk = plant), MENGE (Menge = quantity), MEINS (Mengeneinheit = unit of measure), BUDAT (Buchungsdatum = posting date), WAERS (Währung = currency), DMBTR (Betrag in Hauswährung = amount in local currency).

2. **Date formats vary.** SAP stores dates internally as YYYYMMDD (e.g., `20250218`). When exported through the GUI, the format depends on the user's locale settings — German users get DD.MM.YYYY, US users get MM/DD/YYYY, and some exports retain the internal YYYYMMDD format. A single export can contain mixed formats if rows were entered by users with different locale settings.

3. **Movement types encode business meaning.** 101 = goods receipt from vendor (fuel delivered), 201 = goods issue to cost center (fuel consumed for non-production), 261 = goods issue to production order (fuel consumed in production), 102 = reversal of goods receipt (correction). You can't just sum all quantities — you need to understand which movements represent actual consumption vs. inventory movements.

4. **Plant codes are opaque.** WERKS values like `1000`, `2000`, `3000` mean nothing without a plant code master table (T001W in SAP). In our system, this is the PlantCodeMapping table.

5. **Units are inconsistent.** Even within the same company, one plant might record diesel in liters (L), another in gallons (GAL), and LPG might be in kilograms (KG) or liters depending on how the material master was configured.

### What our sample data looks like

Our `sap_fuel_export.csv` contains 36 rows with authentic SAP column headers (MBLNR, BWART, MATNR, WERKS, MENGE, MEINS, BUDAT, WAERS, DMBTR, SGTXT, LIFNR) spanning January–June 2025 across three plants:

- **Plant 1000** — European plant (EUR currency, liters and M³)
- **Plant 2000** — Second European plant (EUR, liters/KG/M³)
- **Plant 3000** — US plant (USD, gallons and liters)

Deliberate edge cases included:

| Row | Issue | Why |
|-----|-------|-----|
| Row 6, 17, 28 | YYYYMMDD date format (no dots) | Tests multi-format date parser |
| Row 10 | GAL unit instead of L | Tests unit normalization |
| Row 14–15 | Exact duplicate rows | Tests duplicate detection |
| Row 15 | 85,000 L in one month | Suspiciously high — tests flagging |
| Row 18 | Empty MENGE (quantity) | Tests missing-field validation |
| Row 23 | Empty MATNR (material number) | Tests partial-data handling |
| Row 27 | Empty DMBTR (amount) | Tests nullable amount field |
| Row 29 | Negative quantity (-10000 L) with BWART 102 | Tests reversal handling |
| Row 33 | Zero quantity | Tests zero-value edge case |
| Row 35 | New material FUEL-DSL-002 (bio-diesel) | Tests unknown material handling |

### What would break in a real deployment

- **Character encoding** — SAP GUI exports can be in Latin-1, UTF-8, or Windows-1252 depending on OS. Our parser handles UTF-8-BOM and Latin-1 fallback, but exotic encodings would fail.
- **Multi-company code exports** — if a client has multiple SAP company codes (BUKRS), the export might include data from entities we shouldn't be processing together.
- **Custom fields** — many SAP installations add Z-fields (custom columns) to material documents. Our parser would silently ignore these, which might mean missing relevant data.
- **Volume** — large enterprises might have 50,000+ material movements per month. Our synchronous parser would time out.

### What we chose to handle vs. ignore

**Handled**: Movement types 101/201/261/102, German headers, multi-format dates, mixed units (L/GAL/KG/M³), duplicate detection, missing field validation, reversal postings.

**Ignored**: IDoc XML format, OData/BAPI API integration, custom Z-fields, cross-company code filtering, SAP S/4HANA journal entry format (ACDOCA), non-fuel materials (we only process FUEL-* material numbers in practice).

---

## 2. Utility Data — Electricity

### What we researched

We looked at how facilities teams typically access electricity consumption data:

- **Utility portal CSV exports** — most large utilities (Duke Energy, PG&E, ConEdison, National Grid, AEP, CPS Energy) offer online portals where commercial customers can download billing and usage data as CSV or Excel. The column structure varies by utility but typically includes: account number, meter ID, billing period dates, kWh consumption, demand (kW), cost, and tariff type.
- **Green Button data standard** — the US DOE's Green Button initiative defines a standard XML schema (ESPI — Energy Services Provider Interface) for energy usage data. However, adoption is inconsistent, and most facilities teams prefer the simpler CSV download.
- **ENERGY STAR Portfolio Manager** — many organizations use this EPA tool to track energy consumption, which exports data in a specific CSV format. However, the raw utility data still needs to be entered into Portfolio Manager first.

We chose **utility portal CSV export** because it requires zero IT setup and is what facilities teams actually do. They log into their utility's website, navigate to the billing history page, set a date range, and click "Download CSV."

### What we learned

1. **Billing periods don't align with calendar months.** Utilities read meters on their own schedule. A "January" bill might cover December 15 to January 14, or January 3 to February 2. The billing period depends on the meter read route, not the calendar. This makes month-over-month comparisons non-trivial.

2. **Multiple meters per facility.** A single building might have separate meters for general service (lighting, HVAC) and industrial/large power (manufacturing equipment). Each meter can have a different tariff type and rate structure.

3. **Actual vs. estimated reads.** If a meter reader can't access a meter, the utility estimates consumption based on historical patterns. Estimated reads can be significantly off — sometimes 2–3x the actual value. The next actual read catches up with a correction, creating spikes and dips in the data.

4. **Demand charges (kW) vs. consumption (kWh).** Commercial tariffs often include both an energy charge (per kWh consumed) and a demand charge (based on peak kW during the billing period). For emissions calculation, we care about consumption (kWh), not demand (kW), but both appear in the data.

5. **Tariff types encode rate structures.** "C&I General Service", "Industrial Large Power", "Small General Service" — these determine the rate per kWh and affect cost but not the emissions calculation directly.

### What our sample data looks like

Our `utility_meter_readings.csv` contains 28 rows across 4 facilities with realistic billing structures:

- **Headquarters Building** (ACC-10045) — 2 meters (MTR-1001 general, MTR-1002 auxiliary), Austin TX
- **Westside Manufacturing Plant** (ACC-20078) — 2 meters (MTR-2001 large power, MTR-2002 general), San Antonio TX
- **East Distribution Center** (ACC-30112) — 2 meters (MTR-3001 large power, MTR-3002 general), Dallas TX
- **Regional Office Portland** (ACC-40201) — 1 meter (MTR-4001), Portland OR

Deliberate edge cases:

| Row | Issue | Why |
|-----|-------|-----|
| Row 11 | MTR-2001 reads 398,000 kWh (vs. ~130k normal) | Estimated read — suspiciously high; tests flagging |
| Row 16 | Gap: MTR-3001 skips Mar 15–Apr 14 period | Missing billing period; tests gap detection |
| Row 20 | Estimated read type | Tests actual vs. estimated tracking |
| Row 25 | Overlapping period (May 10 vs. May 15 start) | Overlapping bill dates; tests duplicate/overlap detection |
| Row 28 | Estimated read on manufacturing meter | Estimated read on high-consumption meter |
| All | Billing periods run 15th-to-14th or 18th-to-17th | Non-calendar-month billing; tests period handling |

### What would break in a real deployment

- **Per-utility format differences** — every utility formats their CSV differently. Column names, date formats, even the delimiter (comma vs. semicolon for European utilities) vary. We'd need a template/mapping per utility provider.
- **Time-of-use data** — some utilities provide interval data (15-minute or hourly readings) instead of monthly totals. This generates 100x more rows.
- **Net metering** — facilities with solar panels may have negative consumption values during some periods.
- **Rate changes mid-period** — if a tariff rate changes during a billing period, some utilities split the bill into two line items for the same period.

### What we chose to handle vs. ignore

**Handled**: Multiple meters per facility, non-calendar billing periods, actual vs. estimated reads, suspicious-value detection, multiple tariff types, overlapping period detection.

**Ignored**: Interval/time-of-use data (15-min readings), Green Button XML format, PDF bill parsing, net metering, multi-utility aggregation, demand response events.

---

## 3. Corporate Travel — Flights, Hotels, Ground Transport

### What we researched

We looked at how corporate travel platforms expose trip and expense data:

- **SAP Concur** — the dominant enterprise travel and expense platform. Concur's API (v3 and v4) exposes expense reports, travel itineraries, and receipts. However, most clients interact with Concur through its expense report export feature, which produces CSV/Excel files with trip-level detail.
- **Navan (formerly TripActions)** — newer competitor to Concur. Offers similar CSV export functionality from its analytics dashboard.
- **Corporate travel agency exports** — companies using traditional TMCs (BCD Travel, CWT, Amex GBT) receive periodic data feeds in CSV/Excel format with trip details.

We chose **Concur-style CSV export** because Concur dominates the enterprise market, and the CSV export is the path of least resistance — no API keys, no OAuth, no IT involvement. The sustainability lead just goes to Concur Analytics, filters by date range, and downloads.

### What we learned

1. **Trip data is multi-segment.** A single business trip generates multiple line items: outbound flight, return flight, hotel stays, car rentals, rail tickets. These need to be processed individually for emissions but are logically grouped by Report_ID.

2. **Distances aren't always provided.** For flights, Concur sometimes includes distance (in km or miles) and sometimes doesn't — it depends on the airline's GDS integration. When distance is missing, you need to compute it from airport codes using the Haversine formula or a great-circle distance calculator.

3. **IATA airport codes are the key.** Three-letter IATA codes (JFK, LAX, LHR, SIN) are the universal identifier for airports. We use these to look up coordinates and compute distances. However, small regional airports may use ICAO codes instead, and some entries might have city names instead of codes.

4. **Cabin class affects emissions.** Business and first class passengers occupy more floor space per seat, so airlines allocate a larger share of fuel consumption to them. DEFRA provides class-specific emission factors: economy ≈ 0.255 kg CO₂e/pkm, premium economy ≈ 0.403, business ≈ 0.739, first ≈ 1.013 kg CO₂e/pkm.

5. **Hotels and car rentals need different factors.** Hotel emissions are typically calculated per room-night (varies by country and hotel class). Car rental emissions depend on distance driven (km) and vehicle type. These are Scope 3 Category 6 (Business Travel) alongside flights.

6. **Multi-currency expenses.** International travel involves multiple currencies (USD, GBP, EUR, SGD, JPY, CNY). For cost tracking this matters, but for emissions we only need the physical quantities (km, nights, etc.).

### What our sample data looks like

Our `travel_expense_report.csv` contains 31 rows across 14 expense reports, covering flights, hotels, car rentals, and one rail trip:

- **13 flight segments** — domestic (JFK→LAX, AUS→DEN, DFW→MIA, SEA→BOS, SFO→AUS) and international (ORD→LHR, SFO→SIN, JFK→BOM, LAX→NRT, FRA→DEL, MIA→BOG, PVG→ZZZ, IAH→LHR, BOS→CDG)
- **10 hotel stays** — various durations and currencies
- **3 car rentals** — with estimated distances
- **1 rail trip** — Tokyo→Osaka Shinkansen (515 km)

Deliberate edge cases:

| Row | Issue | Why |
|-----|-------|-----|
| Row 5 | Missing distance for ORD→LHR flight | Tests IATA distance computation |
| Row 10 | Missing return date | Tests nullable return date handling |
| Row 11 | Missing distance for JFK→BOM | Tests long-haul distance computation |
| Row 14 | Hotel cost in JPY (1890 JPY — suspiciously low, likely per-night) | Tests multi-currency awareness |
| Row 20 | Missing distance for SEA→BOS | Tests domestic distance computation |
| Row 24 | Unknown airport code ZZZ for Chenzhou | Tests unknown IATA code handling |
| Row 26 | First class (highest emission factor) | Tests class-specific factor selection |
| Row 3, 21, 31 | Car rentals with estimated km | Tests ground transport emissions |
| Row 15 | Rail (Shinkansen) — different transport mode | Tests non-air travel handling |

### What would break in a real deployment

- **Concur API schema changes** — Concur has evolved its API from v1 through v4 with breaking changes in field names and structures. A CSV parser is more stable than an API integration.
- **Personal vs. business expenses** — Concur exports may include personal charges that were incorrectly categorized. We'd need a flag or filter.
- **Radiative forcing multiplier** — at high altitudes, aircraft emissions have a stronger warming effect than the same CO₂ at ground level. The multiplier ranges from 1.7x to 2.7x depending on the methodology. We use DEFRA factors which include a partial RF adjustment, but this is a genuine area of scientific uncertainty.
- **Connecting flights** — a trip from Austin to Tokyo might route through Dallas and Los Angeles. The total distance should be AUS→DFW + DFW→LAX + LAX→NRT, not the great-circle AUS→NRT. We compute direct great-circle distance, which underestimates actual flight distance by 5–15%.
- **Airline-specific emission factors** — newer, more fuel-efficient aircraft (A350, 787) have lower per-passenger-km emissions than older models (747, A340). Using fleet-average factors loses this granularity.

### What we chose to handle vs. ignore

**Handled**: Multi-segment trips (air, hotel, car, rail), IATA code to distance computation (Haversine), cabin class differentiation, multi-currency data, missing return dates, unknown airport codes (flagged as validation warning).

**Ignored**: Concur API integration (OAuth + pagination + incremental sync), radiative forcing multiplier (documented as a known limitation), connecting flight routing, airline-specific factors, personal expense filtering, frequent-flyer offset tracking.

---

## Emission Factors — Sources and Methodology

Our emission factor database is pre-seeded from two primary sources:

### EPA GHG Emission Factors Hub (2024)
- Table 1: Stationary combustion factors for common fuels
- Diesel: 2.68 kg CO₂e per liter (10.16 kg CO₂e per gallon)
- Natural gas: 1.89 kg CO₂e per cubic meter
- LPG/Propane: 1.51 kg CO₂e per liter

### UK DEFRA / BEIS Conversion Factors (2024)
- Used for travel emissions as DEFRA provides class-specific factors
- Air travel economy: 0.255 kg CO₂e per passenger-km
- Air travel business: 0.739 kg CO₂e per passenger-km
- Air travel first: 1.013 kg CO₂e per passenger-km
- Rail: 0.041 kg CO₂e per passenger-km
- Car (average): 0.171 kg CO₂e per km
- Hotel room-night: 31.1 kg CO₂e (UK average)

### US EPA eGRID (2022 data, published 2024)
- US national average grid emission factor: 0.386 kg CO₂e per kWh
- Used as the default for utility data normalization

All factors are stored with their source, year, and applicability region. When a more specific factor is available (e.g., regional grid factor vs. national average), the normalizer uses the most specific match.
