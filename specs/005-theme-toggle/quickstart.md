# Quickstart: Light/Dark Mode Theme Toggle

**Branch**: `005-theme-toggle` | **Date**: 2026-05-22

## What's changing

| File | Change |
|------|--------|
| `static/css/styles.css` | Add `[data-theme="light"]` token block and `color-scheme` declarations |
| `static/js/theme.js` | New file: theme init, OS detection, toggle handler |
| `templates/base.html` | Inline init script in `<head>`; toggle button in `.topbar` |
| `templates/base_auth.html` | Inline init script in `<head>`; toggle button near brand |

No new URLs, views, models, or migrations.

## Running the feature locally

```bash
# Start the dev server (no changes to startup)
python manage.py runserver

# Run the test suite (write tests first)
pytest

# Static analysis
flake8 .
pylint banking accounts banking_app
bandit -r banking accounts banking_app
```

## Testing the toggle manually

1. Open the app at `http://localhost:8000`
2. Click the theme toggle in the top-right of the topbar — the entire UI should switch theme instantly.
3. Reload the page — the selected theme should be preserved.
4. Open DevTools → Application → Local Storage → verify `theme` key is set.
5. Clear `localStorage`, set OS to dark mode → reload → app should open in dark mode.
6. Set OS to light mode, clear `localStorage` → reload → app should open in light mode.

## Test coverage targets

Template tests (pytest-django):

- Toggle button is present in the rendered HTML for every authenticated view.
- Toggle button is present in the rendered HTML for every auth view (login, signup, password reset, password reset done).
- The `<html>` element does not set a hardcoded theme — theme is driven by the init script.

All existing tests must continue to pass.
