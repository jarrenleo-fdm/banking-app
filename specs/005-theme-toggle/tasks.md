# Tasks: Light/Dark Mode Theme Toggle

**Input**: Design documents from `/specs/005-theme-toggle/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Included — Test-First is NON-NEGOTIABLE per Banking App Constitution Principle II. Write tests first; verify they fail before implementing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on each other)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Verify a clean baseline before any changes

- [x] T001 Run existing test suite to confirm zero failures before starting: `pytest`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: CSS light theme token block — required before any user story can be visually verified

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Add `[data-theme="light"]` CSS custom property override block to `static/css/styles.css` using the full light palette from `specs/005-theme-toggle/research.md` Decision 6 (tokens: `--bg: #f5f5f5`, `--bg-card: #ffffff`, `--bg-elevated: #ebebeb`, `--bg-hover: #e2e2e2`, `--text-primary: #111111`, `--text-secondary: #555555`, `--text-tertiary: #888888`, `--border: rgba(0,0,0,0.10)`, `--accent: #2c5fc4`, `--accent-bright: #3d6fd9`, `--accent-dim: rgba(44,95,196,0.10)`, `--accent-border: rgba(44,95,196,0.30)`, `--green: #16a34a`, `--green-dim: rgba(22,163,74,0.10)`, `--red: #dc2626`, `--red-dim: rgba(220,38,38,0.10)`)
- [x] T003 Add `color-scheme: dark` to the existing `:root` block in `static/css/styles.css`; add `color-scheme: light` inside the new `[data-theme="light"]` block

**Checkpoint**: Applying `data-theme="light"` to `<html>` in DevTools should now render the full light palette

---

## Phase 3: User Story 1 — Toggle Theme Manually (Priority: P1) 🎯 MVP

**Goal**: Users can click a visible toggle button on any page to instantly switch between light and dark themes without a page reload.

**Independent Test**: Open the app, click the theme toggle, verify the entire interface switches theme immediately. Navigate to another page and confirm the theme applies (init script sets the attribute; no persistence test needed for this story).

### Tests for User Story 1 ⚠️ Write FIRST — verify they FAIL before implementing

- [x] T004 [P] [US1] Write pytest-django test in `banking/tests/test_theme_toggle.py` verifying the toggle button (element with `id="theme-toggle"`) is present in the rendered HTML for every authenticated view: dashboard, transactions, billing, billing history
- [x] T005 [P] [US1] Write pytest-django test in `banking/tests/test_theme_toggle.py` verifying the toggle button is present in the rendered HTML for every auth view: login, signup, password reset, password reset done

### Implementation for User Story 1

- [x] T006 [US1] Create `static/js/theme.js` with a `toggleTheme()` function that reads `document.documentElement.dataset.theme`, flips it between `"light"` and `"dark"`, and writes the new value back to `document.documentElement.dataset.theme`
- [x] T007 [P] [US1] Add a theme toggle icon button (`<button id="theme-toggle" onclick="toggleTheme()">`) to the `.topbar` flex container in `templates/base.html`; add `<script src="{% static 'js/theme.js' %}"></script>` before `</body>`
- [x] T008 [P] [US1] Add a theme toggle icon button (`<button id="theme-toggle" onclick="toggleTheme()">`) near the `.auth-brand` area in `templates/base_auth.html`; add `<script src="{% static 'js/theme.js' %}"></script>` before `</body>`

**Checkpoint**: Run `pytest banking/tests/test_theme_toggle.py` — all toggle-button-presence tests pass. Click the toggle in a running browser — theme switches instantly.

---

## Phase 4: User Story 2 — Preference Persists Across Sessions (Priority: P2)

**Goal**: The user's theme choice survives page reloads and browser restarts via `localStorage`.

**Independent Test**: Select dark mode, reload the page — dark mode is restored automatically. Open DevTools → Application → Local Storage and verify the `theme` key is set.

### Tests for User Story 2 ⚠️ Write FIRST — verify they FAIL before implementing

- [x] T009 [US2] Write pytest-django test in `banking/tests/test_theme_toggle.py` verifying the `<html>` element does NOT have a hardcoded `data-theme` attribute in any rendered template — the attribute must be absent from server-rendered HTML (it is set exclusively by the inline client-side init script)

### Implementation for User Story 2

- [x] T010 [US2] Update `toggleTheme()` in `static/js/theme.js` to write the new theme value to `localStorage` via `localStorage.setItem("theme", newTheme)` after updating `document.documentElement.dataset.theme`
- [x] T011 [P] [US2] Add a synchronous inline `<script>` block in `<head>` of `templates/base.html`, placed BEFORE the stylesheet `<link>`, that reads `localStorage.getItem("theme")` and sets `document.documentElement.dataset.theme` to the stored value when present
- [x] T012 [P] [US2] Add the identical inline `<script>` block in `<head>` of `templates/base_auth.html`, placed BEFORE the stylesheet `<link>`

**Checkpoint**: Run `pytest banking/tests/test_theme_toggle.py` — no-hardcoded-attribute test passes. Select a theme, reload the page — preference is restored. Confirm `theme` key in DevTools localStorage.

---

## Phase 5: User Story 3 — Default Respects OS Theme Preference (Priority: P3)

**Goal**: First-time visitors with no saved preference see a theme matching their operating system's light/dark setting.

**Independent Test**: Clear `localStorage`, set OS to dark mode, reload — app opens in dark mode. Clear `localStorage`, set OS to light mode, reload — app opens in light mode. Set an explicit preference that differs from OS — explicit preference wins.

### Implementation for User Story 3

- [x] T013 [P] [US3] Update the inline init `<script>` in `templates/base.html` to fall back to `window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"` when `localStorage.getItem("theme")` returns `null`; the resolved value is applied to `document.documentElement.dataset.theme`
- [x] T014 [P] [US3] Apply the identical init script update to `templates/base_auth.html`

**Checkpoint**: All three user stories are independently functional. Run the full manual test sequence from `specs/005-theme-toggle/quickstart.md`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Static analysis clean-up and final end-to-end validation

- [x] T015 [P] Run `flake8 .` and resolve any violations
- [x] T016 [P] Run `pylint banking accounts banking_app` and resolve any violations
- [x] T017 [P] Run `bandit -r banking accounts banking_app` and resolve any warnings
- [x] T018 Run full test suite `pytest` and confirm all pre-existing tests still pass alongside new theme toggle tests
- [ ] T019 [P] Perform manual end-to-end validation per all six steps in `specs/005-theme-toggle/quickstart.md` (toggle, reload, localStorage key, OS dark, OS light, explicit-preference override)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2
- **US2 (Phase 4)**: Depends on Phase 3 — extends the toggle handler and adds init scripts
- **US3 (Phase 5)**: Depends on Phase 4 — extends the init scripts with the OS fallback
- **Polish (Phase 6)**: Depends on all user story phases completing

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no story dependencies
- **US2 (P2)**: Extends US1's `static/js/theme.js` toggle handler — must follow US1
- **US3 (P3)**: Extends US2's inline init scripts — must follow US2

### Within Each User Story

- Tests MUST be written first and confirmed to FAIL before implementation (Constitution Principle II — NON-NEGOTIABLE)
- `static/js/theme.js` changes before template changes that call its functions
- Both template file changes within a story are independent [P]

### Parallel Opportunities

- T004 and T005 (US1 tests) target different views — write sequentially in the same file or coordinate carefully
- T007 and T008 (US1 toggle buttons) — different template files, fully parallel
- T011 and T012 (US2 init scripts) — different template files, fully parallel
- T013 and T014 (US3 OS fallback) — different template files, fully parallel
- T015, T016, T017 (static analysis) — fully parallel

---

## Parallel Example: User Story 1

```bash
# Write tests first (same file — write sequentially to avoid conflicts):
Task: "T004 Write authenticated-view toggle-button test in banking/tests/test_theme_toggle.py"
Task: "T005 Write auth-view toggle-button test in banking/tests/test_theme_toggle.py"

# Confirm tests FAIL, then implement in parallel:
Task: "T007 Add toggle button to templates/base.html"
Task: "T008 Add toggle button to templates/base_auth.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline test run)
2. Complete Phase 2: Foundational (CSS light tokens — CRITICAL)
3. Complete Phase 3: User Story 1 (toggle button + JS handler)
4. **STOP and VALIDATE**: Click toggle in browser — theme switches. `pytest` passes.
5. Ship MVP if approved.

### Incremental Delivery

1. Setup + Foundational → light CSS tokens defined
2. US1 → toggle button works, theme flips instantly; T004/T005 pass
3. US2 → preference survives reload; T009 passes; `theme` key visible in DevTools
4. US3 → OS default respected on first visit (no localStorage)
5. Polish → static analysis clean, full suite green

### Single-Developer Sequence

```
T001 → T002 → T003 → T004 → T005 → T006 → T007+T008 → T009 → T010 → T011+T012 → T013+T014 → T015+T016+T017 → T018 → T019
```

---

## Notes

- [P] tasks operate on different files and have no dependency on each other
- Constitution Principle II (Test-First) is NON-NEGOTIABLE — tests must exist and fail before implementation begins
- The inline `<script>` in `<head>` MUST be synchronous (no `defer`/`async`) and MUST appear BEFORE the stylesheet `<link>` tag to prevent flash of wrong theme (FOUC)
- `static/js/theme.js` is loaded at the end of `<body>` for the toggle handler; the FOUC-prevention init script is a separate inline block in `<head>`
- No Django models, migrations, views, or URLs are modified by this feature
- Verify `localStorage` key `theme` in browser DevTools → Application → Local Storage during manual testing
