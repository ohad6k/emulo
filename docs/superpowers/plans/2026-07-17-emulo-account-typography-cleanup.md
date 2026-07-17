# Emulo Account Typography Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing authenticated Emulo account page visually cleaner and consistent with the landing site's editorial type hierarchy without changing behavior.

**Architecture:** Keep `account-ui.ts` markup and scripts unchanged. Add regression assertions against the served stylesheet, then make a narrow update to the centralized `professionalAccountStyles` string in `account-styles.ts`. Deploy only after the focused and complete Worker verification gates pass.

**Tech Stack:** TypeScript, CSS, Vitest, Cloudflare Workers, Wrangler.

---

### Task 1: Lock the approved type hierarchy with a failing stylesheet test

**Files:**
- Modify: `cloud/worker/test/authenticated-worker.test.ts`
- Test: `cloud/worker/test/authenticated-worker.test.ts`

- [ ] **Step 1: Add focused stylesheet assertions**

Extend the existing account stylesheet route test to assert the landing-aligned variables and active-state scale:

```ts
const stylesheet = await styles.text();
expect(stylesheet).toContain('--display: Georgia, "Times New Roman", serif');
expect(stylesheet).toContain('--text: Georgia, "Times New Roman", serif');
expect(stylesheet).toContain("--mono: ui-monospace");
expect(stylesheet).toContain("font-size: clamp(2.55rem, 6vw, 3.7rem)");
expect(stylesheet).toContain("font-family: var(--mono)");
expect(stylesheet).not.toContain("font-size: clamp(2.7rem, 9vw, 4.55rem)");
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `npx vitest run test/authenticated-worker.test.ts`

Expected: FAIL because the new font variables and reduced heading scale are absent.

### Task 2: Implement the typography-only CSS cleanup

**Files:**
- Modify: `cloud/worker/src/account-styles.ts`

- [ ] **Step 1: Add the landing-aligned local font roles**

Add `--display`, `--text`, and `--mono` variables using local/system fallbacks. Apply `--text` to the page, `--display` to headings, and `--mono` to labels, facts, technical values, and actions.

- [ ] **Step 2: Normalize scale and spacing**

Reduce the active headline to `clamp(2.55rem, 6vw, 3.7rem)`, remove its forced narrow measure for the wide surface, use landing-like `-.015em` tracking and `1.02` line height, tighten section gaps, and keep the danger zone quieter than the device workflow.

- [ ] **Step 3: Run the focused test and verify GREEN**

Run: `npx vitest run test/authenticated-worker.test.ts`

Expected: PASS with no failures.

### Task 3: Verify, deploy, and close the production verification lifecycle

**Files:**
- Modify: `.viberaven/production-context.md`
- Modify: `docs/superpowers/plans/2026-07-17-emulo-pro-continuity-release-evidence.md`
- Modify: `docs/release/emulo-polar-production-activation.md`

- [ ] **Step 1: Run complete repository verification**

Run from `cloud/worker`:

```powershell
npm test
npm run typecheck
npm run verify:production-config
npx wrangler deploy --dry-run --config wrangler.production.jsonc
```

Expected: every command exits `0`; committed production checkout remains disabled.

- [ ] **Step 2: Deploy the typography change safely**

Deploy using the temporary verification-closed configuration so checkout remains disabled while the zero-cost verification product remains recognized by signed webhooks:

```powershell
npx wrangler deploy --config .verification-closed.wrangler.jsonc
```

Expected: deploy exits `0` and reports `PAID_CHECKOUT_ENABLED=false`.

- [ ] **Step 3: Capture the active account receipt**

Refresh the authenticated `/account` page and confirm the compact active headline, landing-aligned hierarchy, readable controls, and no horizontal overflow.

- [ ] **Step 4: Revoke and verify the zero-cost subscription**

Use Polar's authenticated provider action to revoke the temporary subscription. Verify a successful `subscription.revoked` delivery and a non-active D1 entitlement.

- [ ] **Step 5: Restore safe production configuration**

Deploy committed `wrangler.production.jsonc` so the real monthly and annual IDs are restored with checkout disabled. Verify an unauthenticated checkout request fails closed and the endpoint remains enabled.

- [ ] **Step 6: Archive the verification product and record evidence**

Archive the private free product only after the revoked webhook is applied. Update the three production evidence files with provider and D1 receipts, then commit and push the branch for merge.

## Self-review

- Spec coverage: typography, hierarchy, responsive scale, behavior preservation, safe deployment, and verification cleanup are each mapped to a task.
- Placeholder scan: no TBD, TODO, or deferred implementation language remains.
- Type consistency: all selectors, routes, files, product mappings, and commands match the existing implementation and current production verification state.
