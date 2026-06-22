# Foreground vs Background Mode — Root Cause

## The real issue: `ANTHROPIC_API_KEY`, not `ANTHROPIC_BASE_URL`

When `terminal(background=true)` spawns a subprocess chain, **`ANTHROPIC_API_KEY` is absent** from the child environment. `ANTHROPIC_BASE_URL` propagates correctly through `os.environ.copy()` — verified by diagnostic.

Claude Code checks `ANTHROPIC_API_KEY` for its "logged in" gate **before** making any API request. Even though cc-switch replaces the key with its own provider credentials, Claude Code still needs *any non-empty value* to pass the auth check. A missing key → "Not logged in · Please run /login" in ~20ms (no API call attempted).

## Verified fix

Add a dummy `ANTHROPIC_API_KEY` to the subprocess environment:

```python
env = os.environ.copy()
env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:15721"
if "ANTHROPIC_API_KEY" not in env:
    env["ANTHROPIC_API_KEY"] = "cc-switch-proxy"  # any non-empty value works
```

This allows background execution. All 13 Setting A turns completed successfully in background (v4.5.3 + v4-pro, total elapsed ~10 min).

## Diagnostic script

To verify the env in any subprocess chain:

```python
import subprocess, os, sys
env = os.environ.copy()
env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:15721"
code = """
import os
print('ANTHROPIC_BASE_URL=', os.environ.get('ANTHROPIC_BASE_URL', 'NOT_SET'))
print('ANTHROPIC_API_KEY set:', 'ANTHROPIC_API_KEY' in os.environ)
"""
result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
print(result.stdout)
```

If `ANTHROPIC_API_KEY set: False` appears, the fix above is needed.

## Foreground still works without the fix

Foreground `terminal()` calls inherit the parent shell's full environment including `ANTHROPIC_API_KEY`, so no dummy key is needed. The `export ANTHROPIC_BASE_URL=...` pattern in the pre-flight section remains correct for foreground runs.
