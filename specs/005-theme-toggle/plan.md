# Implementation Plan: Light/Dark Mode Theme Toggle

**Branch**: `005-theme-toggle` | **Date**: 2026-05-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-theme-toggle/spec.md`

## Summary

Add a light/dark mode theme toggle to all pages of the banking application. The current UI is dark-only; this feature introduces a complementary light theme defined with CSS custom properties and a client-side vanilla JS toggle that reads and writes the user's preference to `localStorage`, falling back to the OS `prefers-color-scheme` setting on first visit.

## Technical Context

**Language/Version**: Python 3.14.5 / Django 5.2  
**Primary Dependencies**: Django 5.2 (with Argon2), django-environ; vanilla JS (no framework)  
**Storage**: `localStorage` (client-side preference only; no DB changes); SQLite3 backend for app data  
**Testing**: pytest-django 4.11, factory-boy 3.3, pytest-cov 6.2; flake8 / pylint / bandit for static analysis  
**Target Platform**: Web browser (modern evergreen browsers; no IE11 support required)  
**Project Type**: Web application (Django monolith — server-rendered templates, minimal client JS)  
**Performance Goals**: Theme switch completes in under 300ms perceived by user  
**Constraints**: No flash of wrong theme on page load (init script runs in `<head>` before first paint); no server round-trips for theme preference  
**Scale/Scope**: Affects all authenticated and unauthenticated views; two base templates cover all pages

**Active Tier: Prototype / Learning**

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle          | Status         | Notes                                                                                                                                                                                                                               |
| ------------------ | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I — Security       | ✅ PASS        | Theme toggle is purely cosmetic; no user data exposed, no session/auth change, no XSS risk (sets `dataset.theme`, never `innerHTML`). All Django security middleware remains untouched.                                             |
| II — Test-First    | ✅ PASS        | Tests written before implementation. Template tests verify toggle control presence and correct `data-theme` initialization in HTML. JS behavior is non-financial and covered by manual verification (no JS test runner in project). |
| III — SonarQube    | ✅ PASS (tier) | Prototype tier — SonarQube not required. Compensating controls: flake8, pylint, bandit run locally before each commit.                                                                                                              |
| IV — Auditability  | ✅ PASS        | Theme preference is cosmetic; no audit record required. No financial or security event involved.                                                                                                                                    |
| V — Data Integrity | ✅ PASS        | No database changes; no monetary values involved.                                                                                                                                                                                   |

Post-design re-check: **All gates still pass.** No database migrations. No new endpoints. No money-moving code.

## Project Structure

### Documentation (this feature)

```text
specs/005-theme-toggle/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
static/
├── css/
│   └── styles.css          # Add [data-theme="light"] token block
└── js/
    └── theme.js             # NEW: theme preference init, OS detection, toggle handler

templates/
├── base.html               # Add <script> init in <head>; add toggle button in .topbar
└── base_auth.html          # Add <script> init in <head>; add toggle button near brand
```

**Structure Decision**: Single-project layout. The feature is entirely client-side (CSS + JS) with minor template changes. No new Django views, models, or URLs are needed.

## Complexity Tracking

**No violations requiring Complexity Tracking.** Prototype-tier relaxations (SonarQube, `select_for_update`) are pre-approved in the constitution and first recorded in `specs/001-core-banking-operations/plan.md`.
