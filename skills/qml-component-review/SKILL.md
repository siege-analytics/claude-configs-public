---
name: qml-component-review
description: "Optional generic review checklist for Qt Quick/QML component boundaries; never assumes a particular plugin or application architecture."
allowed-tools: Read Grep Glob
---

# QML component review

Use this compatibility-preserving skill only when explicitly requested for a QML review. No repository identity for the historical ChordLibrary/MuseScore consumer has been verified; this skill does not auto-route from a QML filename, `plugin/ui/`, or an application name. Do not prescribe a deployment command, test runner, state-group names, or a host-specific plugin lifecycle without the target repository's own instructions.

## Review the actual component contract

1. Read the parent, component, imports, and local conventions before proposing a boundary. Determine whether the component owns state, reads injected properties, or calls services. Properties-in/signals-out is one possible design, not a universal QML requirement.
2. Verify property types, required inputs, bindings, signal declarations and handlers against their actual call sites. Flag missing wiring and binding loops with a concrete reproducer; don't require a particular signal suffix or internal-property prefix.
3. Check ownership of mutations and business logic. If the local architecture delegates mutations to a parent, test that emitted signals reach it and that child components do not mutate shared state unexpectedly. Otherwise respect the established ownership model.
4. Check import availability, module versions, IDs, anchors/layout and visibility in the supported Qt runtime. A singleton or JavaScript import is not intrinsically wrong; only reject it when incompatible with the verified runtime or local architecture.
5. Test the affected interactions and failure paths using the repository's declared runner and supported host. If manual host verification is needed, report it as pending rather than claiming a deploy succeeded.

For legacy ChordLibrary-specific reviews, first establish an authoritative repository identity and consult its project-owned instructions. The preserved [historical example](reference.md) is non-prescriptive; references to `ChordLibrary.qml`, `WalkthroughPanel.qml`, `deploy.sh`, and MuseScore are not evidence of a current consumer and do not authorize global instructions.
