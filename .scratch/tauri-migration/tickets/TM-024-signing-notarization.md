# TM-024 - Signing and notarization

**Priority:** P3
**Depends on:** TM-023
**Blocks:** TM-025
**Status:** proposed

## Context / evidence

Current macOS build only does ad-hoc `codesign --force --deep --sign -` with
`spctl --assess ... || true` (non-failing) and **no notarization** and no
stapling (`python-app.yml:140-144`). Windows builds are unsigned. The README
documents a Debug.command for users to diagnose Gatekeeper kills
(`README.md:22-26`), i.e. users today see blocked-app behavior.

## Required work

1. macOS: sign with a Developer ID Application certificate (hardened runtime,
   appropriate entitlements for the sidecar), notarize with an App Store
   Connect API key, staple. Apply to the .app bundle and the sidecar binary.
2. Windows: optional Authenticode signing (per assumption Q6); at minimum keep
   the SmartScreen instructions honest.
3. Update the Debug.command / diagnostics to validate the new signature and
   notarization state.
4. Keep ad-hoc signing for local dev builds only.

## Acceptance criteria

- [ ] Notarized build passes `spctl --assess` with no Gatekeeper prompt on a
      clean macOS machine.
- [ ] Hardened runtime lets the sidecar launch and write beside user files.
- [ ] Windows build (if signed) passes SmartScreen review or is documented.

## Risk

- Credential management in CI (Apple API key, cert). Requires the product
  decision/credential availability from assumption Q6.
- Entitlements must not break the sidecar's file access (e.g. no sandbox
  entitlement, or correct temporary-exception).

## Validation strategy

- Release-validation checklist on real hardware: download the zipped app on a
  fresh macOS machine, run, verify no prompt; verify notarization log clean.
- CI gate: `spctl` and `codesign --verify --deep --strict` must pass.