# Issue 016: __init__.py doesn't export TravelBotDaemon

**Priority:** Medium
**Category:** Correctness
**Status:** Open
**Location:** `travelbot/__init__.py:16-31`

## Problem

The `__init__.py` module docstring shows this usage:

```python
from travelbot import TravelBotDaemon
daemon = TravelBotDaemon()
daemon.run_polling_loop()
```

But `__all__` only exports `['EmailClient', 'extract_text_from_pdf']`, and `TravelBotDaemon` is not imported in `__init__.py`. The documented usage raises `ImportError`.

## Impact

- The primary class users need (`TravelBotDaemon`) cannot be imported via the documented shorthand
- Package API is inconsistent with its own documentation

## Root Cause

`TravelBotDaemon` was not added to the package-level imports when `__init__.py` was created, even though the docstring documents it as the primary entry point.

## Suggested Fix

Add the import and export in `__init__.py`:

```python
from .daemon import TravelBotDaemon

__all__ = ['TravelBotDaemon', 'EmailClient', 'extract_text_from_pdf']
```

## Acceptance Criteria

- [ ] `from travelbot import TravelBotDaemon` works
- [ ] `__all__` includes `TravelBotDaemon`
- [ ] Docstring usage example is valid
