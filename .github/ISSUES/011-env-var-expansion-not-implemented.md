# Issue 011: Environment variable expansion documented but not implemented

**Priority:** High
**Category:** Correctness
**Status:** Open
**Location:** `travelbot/daemon.py:73-76`, `docs/configuration.md:107-121`

## Problem

The configuration documentation shows `${TRAVELBOT_OPENAI_KEY}` syntax for referencing environment variables in `config.yaml`, but the code simply calls `yaml.safe_load()` which does not expand environment variables. Values like `"${TRAVELBOT_OPENAI_KEY}"` are treated as literal strings, causing authentication failures for anyone following the documented approach.

## Impact

- Users following the docs to secure their credentials will get authentication failures with no clear error message
- Credentials must be stored in plain text in config.yaml, contrary to documented security guidance
- The documented "Recommended" approach for credential management does not work

## Root Cause

`daemon.py:75-76` uses `yaml.safe_load()` which is a standard YAML parser with no environment variable interpolation support:

```python
def load_config(self):
    config_file = os.path.join(os.path.dirname(__file__), self.config_path)
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)
```

## Suggested Fix

Either:
1. Add a post-processing step to `load_config()` that walks the config dict and expands `${VAR}` patterns using `os.environ`
2. Or update the documentation to remove the environment variable references and document alternative approaches (e.g., setting values before YAML load)

## Acceptance Criteria

- [ ] Environment variable syntax works as documented, OR documentation is corrected
- [ ] Users have a clear, working path to avoid storing secrets in plain text
- [ ] A test validates the chosen approach
