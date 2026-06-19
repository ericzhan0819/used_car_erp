# P1-ACC-6F-C-0A Split QA And Formal Preflight Baseline Semantics

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-C-0A`

## Purpose

P1-ACC-6F-C-0A fixes submit preflight baseline semantics before any formal submit test.

The preflight now separates P1-ACC-6E QA draft baseline expectations from formal Used Car Vehicle draft observation.

## Baseline Modes

`target_mode = qa_draft` means the target is the P1-ACC-6E QA Draft Sales Invoice identified by remarks marker `P1-ACC-6E QA Draft Sales Invoice`.

`baseline_mode = clean_site_expected` keeps the original clean-site warning behavior on `erpnext-coa.test`. GL Entry, Stock Ledger Entry, or submitted Sales Invoice counts greater than zero remain warnings for QA draft checks.

`target_mode = formal_vehicle_draft` means the target can be traced from `Used Car Vehicle.sales_invoice` and does not carry the QA marker.

`baseline_mode = formal_flow_observe_only` records GL Entry and Stock Ledger Entry counts as observations only. Formal vehicle flow normally has earlier Stock Entry and Journal Entry activity before Sales Invoice draft submit, so those ledger counts are not formal draft payload errors.

`target_mode = unknown` still blocks submit readiness. A draft without QA marker and without linked vehicle is not treated as formal flow.

## Submitted Sales Invoice Pollution

Submitted Sales Invoice count greater than zero remains a clean baseline warning because it can interfere with the first submitted Sales Invoice QA judgment.

For formal draft preflight this warning is explicitly a clean baseline risk, not a formal draft payload error.

## Boundaries

This phase does not submit Sales Invoice, create fixtures, create Sales Invoice, create Used Car Vehicle, create Stock Entry, create GL Entry, create Stock Ledger Entry, create Payment Entry, create Journal Entry, create Delivery Note, modify Chart of Accounts, or modify ERPNext / Frappe core.

The next phase may create formal flow QA fixture data or proceed toward the real submit test only after this baseline semantics split is in place.
