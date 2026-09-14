# TM-020 - Security hardening

**Priority:** P2
**Depends on:** TM-003
**Blocks:** none
**Status:** proposed

## Context / evidence

The app is fully local today: no network imports anywhere in `src/` (grep for
requests/urllib/socket/http finds nothing; the only `subprocess` use is opening
folders on macOS, `photometry_processing_widget.py:5, 95-103`). The proposed
architecture requires the backend to "bind to localhost only and use a
per-launch capability or token so it is not an unauthenticated network service"
(`.scratch/architecture/01-...md:37-39`).

## Required work

1. If using a localhost transport: bind 127.0.0.1 only, require the per-launch
   token on every request, random port, no CORS for non-app origins, TLS not
   required on loopback (document the risk). If using stdio (assumption Q1):
   no listening socket at all; token handshake over the pipe.
2. Webview CSP: no remote content, no `unsafe-inline` scripts, allow only the
   bundled assets; confirm no external fetch/iframe in any screen.
3. Path handling: file/dialog scopes — never run shell commands on user data;
   validate that paths come from native dialogs and are not constructed from
   untrusted content. Preserve today's read-only-ish posture (analysis reads
   CSVs, writes only beside source or user-chosen locations).
4. IPC input validation: size limits, type validation on every method (schema
   tests from TM-001), reject unknown methods/oversized payloads.
5. Sidecar sandboxing: macOS hardened runtime + entitlements (TM-024); Windows
   no admin elevation required.

## Acceptance criteria

- [ ] Unauthenticated requests to the backend are rejected.
- [ ] Webview CSP report shows zero remote URLs; all assets bundled.
- [ ] No new network surface beyond the chosen transport.
- [ ] Fuzz/malformed requests to the sidecar do not crash it (errors, not
      crashes).

## Risk

- Low for stdio; moderate for localhost (network service needs hardening). Keep
  the choice consistent with TM-001 (Q1).

## Validation strategy

- Automated: start sidecar, send unauthenticated + malformed requests, assert
  rejection and no crash.
- CSP scan of bundled HTML/JS.
- Security review pass before Gate 4.