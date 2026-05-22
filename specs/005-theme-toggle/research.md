# Research: Light/Dark Mode Theme Toggle

**Branch**: `005-theme-toggle` | **Date**: 2026-05-22

## Decision 1: Preference Storage

**Decision**: `localStorage` (client-side, key `theme`)

**Rationale**: The spec explicitly scopes preference to per-device/browser; no cross-device sync is required. `localStorage` requires no server round-trips, no Django model or migration changes, and is supported by all modern browsers. It persists across sessions, satisfying FR-003.

**Alternatives considered**:
- *Django session / server-side*: Would require a view endpoint and AJAX call just to save a visual preference — unnecessary complexity.
- *Database user profile field*: Requires a migration and server round-trip on every toggle; also ties a UI preference to a data model, violating separation of concerns.
- *Cookie*: Survives across browser restarts like `localStorage` but adds HTTP overhead on every request. The Django `SESSION_COOKIE_*` secure settings would require careful handling. No benefit over `localStorage` for a client-only preference.

---

## Decision 2: Theme Application Mechanism

**Decision**: `data-theme` attribute on `<html>` element, toggled by JavaScript; light theme defined as `[data-theme="light"] { ... }` CSS override block.

**Rationale**: The existing stylesheet uses CSS custom properties (`--bg`, `--text-primary`, etc.) on `:root`. Adding a `[data-theme="light"]` selector that overrides those same variables is the minimal, zero-refactor path. Changing one attribute on `<html>` repaints the entire page instantly without JavaScript re-styling any individual element.

**Alternatives considered**:
- *Class toggle on `<body>` or `<html>` (`.dark` / `.light`)*: Equivalent behaviour; `data-theme` attribute is semantically clearer and is the industry convention for CSS theming.
- *Separate stylesheet per theme*: Requires an extra network request and duplicates all token-neutral rules. Rejected — too much overhead.
- *CSS `color-scheme` property only*: Controls browser UI chrome (scrollbars, form controls) but does not retheme custom design tokens. Insufficient on its own; will be used as a complement (`color-scheme: light` / `dark` on `:root`).

---

## Decision 3: FOUC Prevention (Flash of Wrong Theme)

**Decision**: Inline `<script>` placed in `<head>` before any stylesheet link, reading `localStorage` and setting `document.documentElement.dataset.theme` synchronously before first paint.

**Rationale**: JavaScript that runs after the CSS loads but before the body renders prevents the default dark theme from flashing when a user has saved a light preference. The script must be synchronous (no `defer` / `async`) and must precede `<body>` rendering. It is small enough (< 200 bytes) to inline rather than reference as an external file.

**Alternatives considered**:
- *External `theme-init.js` with no `defer`*: Extra network request for a tiny script; inline is faster and simpler.
- *Cookie read on server to set `data-theme` attribute in rendered HTML*: Eliminates any JS-based FOUC entirely, but adds server complexity for a purely cosmetic preference. Rejected.

---

## Decision 4: OS Default Detection

**Decision**: `window.matchMedia('(prefers-color-scheme: dark)')` checked on page load when `localStorage` contains no saved preference.

**Rationale**: Standard browser API; supported by all modern evergreen browsers. Satisfies FR-004 and User Story 3 (P3) with zero external dependencies.

**Alternatives considered**:
- *Default to dark always (ignore OS)*: Simpler but fails FR-004 and degrades first-time experience for light-mode OS users.
- *Server-side `Sec-CH-Prefers-Color-Scheme` client hint*: Draft standard, requires `Accept-CH` response header, limited browser support. Rejected — overkill.

---

## Decision 5: Toggle Control Placement

**Decision**: Icon button in `.topbar` (authenticated pages via `base.html`) and inline near the brand link (auth pages via `base_auth.html`).

**Rationale**: The `.topbar` flex container already spans the full page width and is visible on every authenticated page. Auth pages have no topbar; the brand area at the top is the most natural placement. Both locations are reachable within 1 click from any page (FR-001, SC-001).

**Alternatives considered**:
- *Sidebar footer (below logout button)*: Less visible; users may miss it.
- *Floating button (fixed position)*: Obtrudes on content; accessibility concerns.

---

## Decision 6: Light Theme Palette

**Decision**: Define a light palette that maps to the same token names as the existing dark palette, minimizing downstream CSS changes.

| Token | Dark value | Light value |
|-------|-----------|-------------|
| `--bg` | `#0a0a0a` | `#f5f5f5` |
| `--bg-card` | `#111111` | `#ffffff` |
| `--bg-elevated` | `#1a1a1a` | `#ebebeb` |
| `--bg-hover` | `#1f1f1f` | `#e2e2e2` |
| `--text-primary` | `#ececec` | `#111111` |
| `--text-secondary` | `#9a9a9a` | `#555555` |
| `--text-tertiary` | `#545454` | `#888888` |
| `--border` | `rgba(255,255,255,0.08)` | `rgba(0,0,0,0.10)` |
| `--accent` | `#2c5fc4` (unchanged) | `#2c5fc4` |
| `--accent-bright` | `#3d6fd9` (unchanged) | `#3d6fd9` |
| `--accent-dim` | `rgba(44,95,196,0.14)` | `rgba(44,95,196,0.10)` |
| `--accent-border` | `rgba(44,95,196,0.35)` | `rgba(44,95,196,0.30)` |
| `--green` | `#4ade80` (unchanged) | `#16a34a` |
| `--green-dim` | `rgba(74,222,128,0.10)` | `rgba(22,163,74,0.10)` |
| `--red` | `#f87171` (unchanged) | `#dc2626` |
| `--red-dim` | `rgba(248,113,113,0.10)` | `rgba(220,38,38,0.10)` |

**Rationale**: Maintains brand accent colour consistency across modes. Greens and reds shift to darker, more legible values for light backgrounds.
