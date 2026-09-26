# Flood Event Inventory — SIH26071

Purpose: identify candidate additional independently-verifiable flood/
inundation events for the Chennai Metropolitan Region, beyond the two
currently used (November 2021 Episode 1 and Episode 2), to reduce the
project's single biggest scientific limitation — a 2-episode LOEO
validation.

**Methodology and honesty note**: everything below comes from public web
search and search-result snippets performed by an AI assistant with no
account access to NDEM, Bhuvan, or any ISRO/NRSC data portal, and no
ability to download or inspect actual GIS/shapefile products (a direct
fetch of an NDEM report PDF was blocked by that site's robots.txt). No
candidate below should be treated as usable ground truth until a human
with appropriate portal access has actually obtained, inspected, and
validated the underlying spatial layer. This inventory identifies *leads*,
not *verified events* — consistent with the project's standing rule against
using unverified sources as quantitative labels.

## Status categories
- **VERIFIED**: actual satellite-derived inundation geometry has been
  obtained and inspected by a project member; currently only the
  November 2021 event qualifies.
- **POSSIBLE**: credible evidence (major documented flood event, an NRSC/
  NDEM report referencing satellite analysis) exists, but the actual
  geospatial product has not been obtained/inspected by this project.
- **REJECTED**: source is not authoritative enough for quantitative
  ground-truth labeling (e.g. commercial/community-derived maps), even if
  useful as general context.

---

## Candidate 1 — Cyclone Michaung, December 2023 — **POSSIBLE**

- **Event**: Cyclone Michaung caused severe flooding across Chennai and
  the surrounding region, December 3–5, 2023. Extensively documented in
  IMD bulletins and national/international press: Chennai airport closed
  after runway submersion, city-wide waterlogging, evacuations, reported
  fatalities. IMD-reported rainfall totals of 20–34 cm in 24-48 hours at
  various Chennai-area stations (Poonamallee, Avadi, Tambaram,
  Nungambakkam, Meenambakkam).
- **Satellite source (found via search, not independently accessed)**:
  An NRSC/NDEM document titled "Tamil Nadu Heavy Rains 2023 - Michaung
  Cyclone - Near Real Time Inundation Mapping using satellite data"
  references RISAT-1A (EOS-04) MRS SAR data acquired 07 Dec 2023 (0600
  Hrs), analyzed by NRSC's Flood Disaster Team, with a resulting
  inundation layer sent to TNSAC/TNSDMA and referenced as viewable on the
  Bhuvan flood portal (`bhuvan-app1.nrsc.gov.in/disaster/disaster.php?Id=flood`)
  and the NDEM portal (`ndem.nrsc.gov.in`).
  Document URL (not fetchable by this assistant — blocked by robots.txt):
  `https://ndem.nrsc.gov.in/documents/Disaster_Document/2023/TN/tncyclone50dsc07122023_0600hrs/tncyclone50dsc07122023_0600hrs_report.pdf`
- **District coverage stated in the report** (per search snippet, not
  independently confirmed against the full PDF): inundation "in parts of
  coastal districts to an extent of 148,360 Ha majorly covering
  Kanchipuram, Chengalpattu, Cuddalore, Ranipettai, Tiruvallur,
  Tiruvannamalai, Villupuram districts."
  **Important caveat**: this list does not explicitly name "Chennai"
  district itself — only bordering/overlapping districts (Kanchipuram,
  Tiruvallur, Chengalpattu form part of the wider CMR study area this
  project already uses, but whether the inundation layer's polygons
  actually extend into Chennai district's own boundary, and at what
  timestamp precision, is unconfirmed from the snippet alone.
- **What would be needed to promote this to VERIFIED**:
  1. A human with NDEM/Bhuvan access downloads the actual GIS layer
     (shapefile/GeoJSON) for this event.
  2. Confirm it has polygon coverage intersecting this project's existing
     70,626-cell CMR grid (not just district-level statistics).
  3. Confirm an exact acquisition timestamp (the report cites 07 Dec 2023
     0600 Hrs for the RISAT-1A/EOS-04 pass) usable the same way the
     November 2021 timestamps are used (exact match against AI#1's
     hourly weather series).
  4. Check whether this project's Open-Meteo weather series (2016–2025)
     actually covers December 2023 with the required feature columns —
     very likely yes, given the series already extends through 2025, but
     not independently re-verified in this inventory.
- **Value if confirmed**: this would be a *third* independent episode,
  meaningfully strengthening LOEO from 2-fold toward 3-fold, and from a
  meteorologically different event type (a landfalling cyclone rather than
  a monsoon depression) — likely to test AI#1/AI#2 generalization in a
  genuinely different regime.

## Candidate 2 — Chennai floods, December 2015 — **REJECTED for this project's current scope**

- Well-documented, severe, NRSC reportedly produced inundation mapping at
  the time (referenced secondhand via an open-data catalog entry, "Flood
  inundation zone in Chennai floods of 2015 as per NRSC," on
  `data.opencity.in`).
- **Rejected reason, not a quality judgment**: this project's AI#1 weather
  dataset (Open-Meteo, Chennai) begins in 2016 per `PROJECT_SPEC.md`/
  `DECISIONS.md`. December 2015 predates the available weather feature
  history entirely, so it cannot be integrated into the existing Stage 6
  causal-feature pipeline without a separate, unverified extension of the
  weather dataset backward in time. Flagging as a candidate only if the
  weather dataset's start date is ever revisited — out of scope for now.

## Candidate 3 — Third-party/commercial flood-zone maps (e.g. "Verified.RealEstate" Tamil Nadu flood layer) — **REJECTED**

- A commercial real-estate community site was found publishing a
  statewide "8,904 sq km flood-prone" polygon layer with district-level
  percentages (e.g. "Chennai district 35.62% flood prone").
- **Rejected**: this is not sourced to NRSC/NDEM/ISRO or any stated
  authoritative satellite product in what was found; it describes its own
  derived methodology (polygon union/overlap removal) without a clear,
  checkable satellite-acquisition citation. Per this project's standing
  rule, non-authoritative or unclear-provenance sources must not be used
  as quantitative ground truth, however useful they might be as general
  public risk-communication context elsewhere.

## Not investigated this pass

This inventory is not exhaustive. Other candidate windows not
investigated in this session, worth a future pass: Northeast monsoon
flooding in Chennai in most other years 2016–2025 (several likely had at
least localized waterlogging events with IMD/CWC records, per Candidate 1's
own report referencing "Source: News Media, IMD, CWC" as an intake channel
NRSC itself uses), and whether NRSC's annual "Flood Hazard Zonation"
products (distinct from event-specific rapid-mapping products) could serve
a different validation purpose than the exact-timestamp LOEO design this
project currently uses.

## Recommendation

Do not integrate Candidate 1 (Michaung) into Stage 6/7/8 yet. The single
next concrete action is for someone with NDEM/Bhuvan portal access to
retrieve the actual GIS product for the 07 Dec 2023 0600 Hrs RISAT-1A/
EOS-04 analysis and confirm CMR-grid intersection and Chennai-district
coverage specifically, before any code changes are made. This is a real
external dependency this assistant cannot resolve — no portal
account/access exists in this environment.

## Update — 2026-09-15 — Real GIS data obtained and inspected

Per the mission's explicit instruction to try legitimate public endpoints
(not authentication bypass) before declaring access blocked, a specific,
legitimate, publicly-licensed source was found and actually downloaded and
inspected this session — not just referenced from a search snippet.

### Source found and downloaded

`NDEM_TN_Floods_Inundation.geojsonl.7z` from
`https://github.com/ramSeraph/india_natural_disasters/releases/tag/floods`
(CC0-licensed). Independently corroborated as a legitimate NDEM mirror by
a public Datameet Google Groups thread ("Looking For Flood Data from ISRO
BHUVAN"): *"The flood inundation layers have already been retrieved from
https://ndem.nrsc.gov.in/ ... I merged the various layers available at the
site based on some heuristics and what felt related."* — i.e. a
heuristic, non-exhaustive merge, not a complete mirror of every NDEM
layer.

Downloaded via `curl` (GitHub release assets are within this environment's
allowed network domains — no authentication bypassed, no scraping beyond a
public, licensed release asset), extracted with `7z` (18.7MB archive →
166MB GeoJSONL, 81,123 features, `MultiPolygon` geometries, plain
`[lon, lat]` WGS84-consistent coordinates, feature IDs prefixed
`tnflood50dsc...` matching NDEM's own product-naming convention).

### What was actually verified from this real data

**All 5 of this project's existing Chennai timestamps are present and
independently confirmed** in this separately-sourced mirror:

| Timestamp (from_time) | Features found |
|---|---|
| 08-11-2021 23:00 | 17,117 |
| 10-11-2021 11:00 | 3,666 |
| 10-11-2021 18:00 | 718 |
| 12-11-2021 00:00 | 2,220 |
| 28-11-2021 06:00 | 18,569 |

Sanity-checked: features for these 5 timestamps span latitude ~8–13.25°N,
consistent with a statewide Tamil Nadu product where Chennai's flooding is
part of a broader northeast-monsoon event — this is a real, independent
corroboration of the project's existing ground truth from a source outside
whatever pipeline originally produced the project's own label files (which
were not available in this checkout to directly diff against — noted as a
follow-up, not done this session).

**Two additional, previously-unused, real timestamps exist in the same
dataset**: `16-11-2021 06:00` (15,055 features) and — initially hoped to
be the Michaung Chennai layer — `18-12-2023 18:00` (14,228 features) and
`20-12-2023 11:00` (488 features).

### Honest negative result: none of the new timestamps cover Chennai

Computed bounding boxes for all three new-date feature groups:

| Timestamp | lon range | lat range |
|---|---|---|
| 16-11-2021 06:00 | 77.55–78.53°E | 8.51–10.42°N |
| 18-12-2023 18:00 | 77.82–78.12°E | 8.45–8.79°N |
| 20-12-2023 11:00 | 77.84–78.12°E | 8.45–8.68°N |

All three are clustered entirely in far southern Tamil Nadu (consistent
with the Tirunelveli/Thoothukudi/Kanyakumari area), never reaching
Chennai's latitude (13.08°N). **None of these three new events are usable
for this project** — not a data-quality problem, simply the wrong
geography. This is reported as a genuine negative finding, not spun as a
partial win.

### Why the Michaung Chennai layer specifically wasn't in this download

The Michaung report referenced earlier (`tncyclone50dsc07122023_0600hrs`)
uses a **different NDEM layer-naming prefix** (`tncyclone...`) than every
feature actually present in this downloaded file (`tnflood...`). Combined
with the mirror curator's own description of a "heuristic" merge, the most
likely explanation is that the `tncyclone` layer series (cyclone-specific
rapid-mapping products, as opposed to the general `tnflood` series) simply
wasn't included in this particular community mirror — not that it doesn't
exist. A further, narrower search specifically for a `tncyclone` mirror
found nothing usable this session.

### Updated status: Cyclone Michaung — still **POSSIBLE**, GIS access still **PENDING**

Downgrading nothing, upgrading nothing for Michaung specifically — the
original assessment stands. What changed is that one concrete, legitimate
avenue (this GitHub mirror) has now been tried and exhausted, narrowing
the remaining search space to: (a) direct NDEM/Bhuvan portal access for
the `tncyclone50dsc07122023_0600hrs` product specifically, or (b) finding
a different open mirror that happens to include the `tncyclone` series.

### Genuine value delivered this session even without a new usable event

Independent, reproducible corroboration that all 5 existing project
timestamps correspond to real NDEM-sourced flood layers, from a source
outside the project's own pipeline — a real (if modest) reproducibility/
provenance strengthening, obtained through legitimate public access, not
fabricated.
