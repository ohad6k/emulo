# Emulo Account, Pricing, Google Sign-In, And Legal Design

## Purpose

Emulo needs a commercial account path that feels credible to both developers and non-developers while preserving the open-source product and the verified server-side billing boundary. This design replaces the existing technical beta presentation, adds Google alongside GitHub, explains annual value clearly, and publishes the policies a visitor should be able to inspect before sign-in or payment.

This is a structural redesign, not a recolor. The current split-screen account experience, status badges, and implementation-oriented copy are removed.

## Design Principles

1. Product language, not infrastructure language. Visitors should see what Emulo does and what choice they are making, not OAuth, D1, Polar, hashed sessions, server truth, or deployment status.
2. Broad audience. GitHub remains for developers; Google is equally prominent for creators, operators, founders, and other AI power users.
3. Calm confidence. Warm neutral surfaces, charcoal text, clear spacing, and restrained borders replace the navy/teal beta-dashboard look.
4. Honest claims. The free product remains capable. Pro is the managed continuity layer. No checkout-live, cloud-complete, or performance claim is shown without proof.
5. Safety is invisible but real. OAuth validation, token handling, webhook truth, and fail-closed billing stay in the Worker and tests, not in marketing copy.

## Account Experience

### Page structure

The account page uses a full-height warm ivory canvas with a compact Emulo header at top left. The header contains the real dual-profile Emulo icon and the EMULO wordmark. The page body centers one responsive panel approximately 460 pixels wide. The panel is not a floating dashboard card full of labels; it is a focused identity gateway.

The signed-out hierarchy is:

- Emulo icon and wordmark in the global header.
- Eyebrow: `EMULO ACCOUNT` only if it improves hierarchy; omit it if the title is sufficient.
- Title: `Sign in to Emulo`.
- Supporting copy: `Access your account and manage Emulo Pro.`
- Primary provider choice: `Continue with Google` with the official multicolor Google G mark on a white, bordered button.
- Divider: `or`.
- Secondary provider choice: `Continue with GitHub` with the official GitHub mark on a charcoal button.
- Privacy microcopy: `Emulo uses your sign-in provider only to verify your identity.`
- Footer links: `Privacy`, `Terms`, `Refunds`.

Google is first because it is the broader commercial path. GitHub remains equally usable and visually strong, but no longer defines the entire audience.

### Removed elements

The following must not appear:

- `Private account`
- `Signed out`
- `Production`
- `Private beta`
- `Connect your Emulo account`
- `View open source`
- `Your account session is stored as an opaque, hashed browser session`
- Any reference to server-side payment truth, Polar-hosted checkout, OAuth scopes, D1, internal account IDs, or provider tokens on the customer-facing page
- The old flat robot SVG as the main brand mark

### Authenticated states

The same centered shell is reused after sign-in. It changes content rather than switching to a different visual system.

- No plan: `Your Emulo account is ready.` followed by a concise explanation that Emulo Pro is not active. If checkout is still disabled, the page says `Emulo Pro is not available for purchase yet.` It does not send the user back to open source or call the state private.
- Active: `Emulo Pro is active.` with the plan cadence and renewal/end date only when confirmed by webhook-backed account state. The management action reads `Manage subscription`.
- Past due or grace: explain the billing issue in plain language and offer `Manage subscription`.
- Ended/refunded: state the actual entitlement result without blame or implementation detail.
- Provider failure: `Sign-in is temporarily unavailable. Please try again.` Provider-specific wording may identify Google or GitHub when only one path failed.

### Branding asset

Use the optimized real asset `assets/emulo-oauth.png` for the Worker-served account icon and favicon. It is already under 1 MB and visually matches the repository identity. The browser tab, global header, account panel, and legal pages should show a consistent Emulo mark.

## Google And GitHub Behavior

Both options create an authenticated Emulo browser session through the Worker. Google requests only basic identity scopes (`openid`, `email`, and `profile`). GitHub keeps its current minimal behavior and does not request repository access.

The UI must not promise that Google and GitHub automatically open the same account. At launch, they are separate provider identities because silent email matching is unsafe and GitHub does not currently provide an email. A future explicit linking experience can let an authenticated user prove both providers before merging.

The Google consent experience must use the name `Emulo`, the real Emulo logo, the public homepage, the public Privacy Policy and Terms, and `ohadkrispin@gmail.com` as support contact. The operator is described as `Emulo, operated by Ohad Krispin in Israel`; the design must not imply a registered company.

## Pricing Design And Copy

The existing two-product structure remains: permanent free/open source and optional Emulo Pro. The section should feel like a clear product decision, not a billing control panel.

### Section framing

- Label: `OPEN SOURCE + MANAGED CONTINUITY`
- Heading: `Start free. Add continuity when your workflows depend on it.`
- Supporting copy: `Emulo stays useful on your machine. Emulo Pro adds the managed layer for people who want continuity without maintaining it themselves.`

### Free card

- Label: `Emulo`
- Heading: `Free and open source.`
- Price: `$0`
- Body: explain local session mining, local profile ownership, and the capable MIT-licensed core in concise language.
- Action: `Get Emulo`
- Destination: GitHub repository.

### Pro card

- Label: `Emulo Pro`
- Heading: `Managed continuity for the way you work.`
- Body: only include capabilities that are live or explicitly marked as coming soon. Do not invent sync, team, analytics, or performance claims.
- Monthly row: `$9 / month` and action `Choose monthly`.
- Annual row: original annualized price `$108` struck through, `$79 / year`, badge `Save 27%`, and action `Choose annual`.
- Both actions route to the Emulo account page while checkout remains disabled. They do not link directly to provider checkout or expose product IDs.

### Removed pricing language

- `Install from GitHub`
- `Open account`
- `Private beta`
- `Payment truth stays server-side`
- `GitHub signs you in, Polar hosts checkout...`
- Any description of webhook or entitlement implementation

## Legal Pages

Create three public pages with the same warm editorial system and compact Emulo header. Each page must have a clear title, last-updated date, readable content width, section navigation only if useful, contact link, and links to the other policies.

### Privacy Policy

The policy describes actual account-service data flows:

- Google or GitHub provider identity, including the stable provider subject/ID needed for account lookup.
- Google email/name data only to the extent returned by the basic identity scopes and used for the sign-in experience; the stable provider subject, not email, is the durable identity key.
- Hashed browser-session identifiers stored in D1.
- Normalized subscription, customer, and entitlement metadata from Polar; no raw payment-card data is handled by Emulo.
- IP address forwarding to Polar checkout when present and required by the existing server flow.
- Infrastructure providers: Google, GitHub, Cloudflare, Polar, and Vercel.
- No raw AI coding session logs or mined personal profiles are uploaded by the account/billing service.
- Retention, security, international processing, user rights, contact, and policy updates in language proportionate to the current product.

### Terms of Service

The Terms identify Emulo as operated by Ohad Krispin in Israel and cover:

- Eligibility and account responsibility.
- Separation between the MIT-licensed open-source software and Emulo Pro service.
- Subscription pricing, automatic renewal, cancellation, and access consequences.
- Polar's role as Merchant of Record and its buyer terms at checkout.
- Acceptable use and prohibition on abusing the service or interfering with other users.
- Ownership of Emulo service/branding while preserving the repository's open-source license.
- Service availability, changes, termination, warranty disclaimer, proportionate limitation of liability, mandatory rights, Israeli governing law, and contact.

### Refund Policy

Proposed commercial policy:

- First subscription payment: request a refund within 14 days of purchase.
- Renewal payment: request a refund within 7 days of renewal.
- Cancellation stops future renewals but does not itself refund prior payments.
- A refund does not automatically cancel a subscription; cancellation is handled separately when required.
- Requests go to `ohadkrispin@gmail.com` with the account email and order reference, never full card details.
- Polar processes approved refunds as Merchant of Record and may issue refunds independently to prevent disputes.
- Mandatory consumer rights continue to apply.

This refund window is a proposed product decision that requires Ohad's approval before the policy is treated as final.

## Responsive And Accessibility Requirements

- Account panel fits at 390 CSS pixels without horizontal scrolling.
- Provider buttons are at least 44 pixels tall, keyboard reachable, and have visible focus states.
- Provider icons are decorative when button text already names the provider, avoiding duplicate screen-reader announcements.
- Text and controls meet WCAG AA contrast against the warm neutral background.
- Motion is unnecessary. If any hover transition exists, it is subtle and respects reduced motion.
- Legal pages use semantic headings, readable line length, and descriptive links.
- Struck-through `$108` remains understandable to assistive technology; `$79/year` and `Save 27%` carry the primary meaning.

## Verification Acceptance

The design is accepted only when:

1. Desktop and mobile screenshots show a structurally centered account experience with the real Emulo icon.
2. Google and GitHub buttons are both functional in tested environments and neither requires repository/product-data scopes.
3. Every rejected label and technical sentence is absent from rendered HTML.
4. Pricing shows `$0`, `$9/month`, `$79/year`, the `$108` comparison, and `Save 27%` with professional actions.
5. Privacy, Terms, and Refund pages are linked before sign-in and payment intent.
6. The policies match the actual code/provider boundaries and contain no registered-company fiction.
7. Checkout remains disabled until a separately approved live-money verification.
8. Existing GitHub auth, account sessions, and Polar entitlement tests remain green.

## Non-Goals

- Automatic Google/GitHub account merging.
- Self-service identity linking.
- Password authentication.
- Access to Gmail, Drive, Calendar, YouTube, repositories, or other provider data.
- Team/workspace accounts.
- Enabling real-money checkout in this design release.
- Claiming cloud capabilities that are not implemented and proven.
