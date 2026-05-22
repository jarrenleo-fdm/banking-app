# Data Model: Light/Dark Mode Theme Toggle

**Branch**: `005-theme-toggle` | **Date**: 2026-05-22

## Overview

This feature introduces no new database entities. The only state is the user's theme preference, which is stored client-side in `localStorage`.

## Client-Side State

| Key | Storage | Type | Values | Default |
|-----|---------|------|--------|---------|
| `theme` | `localStorage` | string | `"dark"` \| `"light"` | OS `prefers-color-scheme`, falling back to `"dark"` |

### Lifecycle

1. **Page load**: Read `localStorage.getItem("theme")`. If absent, read `window.matchMedia("(prefers-color-scheme: dark)")`. Set `document.documentElement.dataset.theme` accordingly.
2. **Toggle**: Flip `document.documentElement.dataset.theme` between `"light"` and `"dark"`. Write the new value to `localStorage.setItem("theme", newValue)`.
3. **Subsequent visits**: Step 1 restores the saved value automatically.

## No Database Changes

No Django models are modified. No migrations are required.
