# Emulo Account Typography Cleanup

## Decision

Keep the existing account-page structure and every billing, entitlement, device, export, and deletion interaction. Apply a focused typography and spacing cleanup so the authenticated account surface feels like the Emulo landing site rather than an oversized generic document.

## Chosen direction

Use the landing site's three-role editorial system without adding remote font dependencies:

- restrained serif display text for page and section headings;
- readable serif body copy for explanations;
- compact monospace-style labels and actions for product controls.

The rejected alternative is a structural dashboard redesign. The user explicitly likes the current design and requested only cleaner type, copy, scale, and fit.

## Visual changes

- Reduce the active-state headline so it reads as a product status, not a landing-page hero.
- Remove the forced narrow headline measure that creates the awkward two-line break.
- Tighten heading tracking and use a firmer display weight consistent with the landing page.
- Move body copy from generic UI sans styling toward the landing site's editorial text voice.
- Give labels, facts, buttons, inputs, and technical values a compact mono/system-mono treatment.
- Normalize button height, weight, casing, and letter spacing so primary and secondary actions feel related.
- Reduce excessive vertical gaps while preserving clear section separation.
- Keep the danger zone fully visible and accessible, but make its typography quieter than the active plan and device workflow.

## Functional boundaries

No HTML data attributes, form actions, route URLs, polling logic, entitlement logic, billing logic, webhook logic, device limits, deletion confirmation phrase, CSP, or provider configuration may change.

The private production verification subscription remains a temporary test fixture. Checkout remains disabled during the UI change.

## Responsive behavior

Desktop keeps the existing centered wide account surface. Mobile remains a single column with full-width actions and no horizontal overflow. Heading sizes must remain legible at 320-390 CSS pixels without dominating the viewport.

## Verification

- Add focused CSS regression expectations before changing production styles.
- Observe the new tests fail against the current oversized/sans rules.
- Implement only the style changes required for those expectations.
- Run focused account UI tests, the complete Worker suite, production-config guards, and TypeScript typecheck.
- Deploy with checkout disabled and the temporary verification product mapping preserved until the active-state visual receipt is captured.
- After the receipt, revoke the $0 verification subscription, verify the signed revoked lifecycle, restore the real monthly product mapping with checkout disabled, and archive the verification product.

## Self-review

The scope is intentionally limited to one stylesheet and its focused tests. It contains no placeholders, no external font dependency, no behavioral change, and no conflict with the active production verification sequence.
