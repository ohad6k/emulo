import type { AccountStatus, EntitlementSummary } from "./account-status";
import { professionalAccountStyles } from "./account-styles";

const DOCUMENT_HEADERS = {
  "cache-control": "no-store",
  "content-security-policy":
    "default-src 'none'; img-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  "content-type": "text/html; charset=utf-8",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
};

const ACCOUNT_STYLES = `:root {
  color-scheme: light;
  --ink: #17303a;
  --ink-muted: #52656c;
  --paper: #f6f4ec;
  --paper-deep: #ebe7dc;
  --white: #fffefa;
  --teal: #0f9488;
  --teal-dark: #0f766e;
  --coral: #ff8a5c;
  --line: rgba(23, 48, 58, 0.16);
  --shadow: 0 28px 70px rgba(23, 48, 58, 0.14);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* { box-sizing: border-box; }

html { min-width: 320px; background: var(--paper); }

body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  background:
    linear-gradient(90deg, rgba(23, 48, 58, 0.035) 1px, transparent 1px) 0 0 / 48px 48px,
    var(--paper);
}

a { color: inherit; }

button, a { -webkit-tap-highlight-color: transparent; }

button { font: inherit; }

.site-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(420px, .95fr);
}

.identity-panel {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 100vh;
  padding: clamp(28px, 5vw, 72px);
  background: var(--ink);
  color: var(--paper);
}

.identity-panel::after {
  content: "";
  position: absolute;
  right: -18%;
  bottom: -20%;
  width: min(50vw, 680px);
  aspect-ratio: 1;
  border: 1px solid rgba(246, 244, 236, .13);
  border-radius: 50%;
  box-shadow: 0 0 0 44px rgba(246, 244, 236, .025), 0 0 0 88px rgba(246, 244, 236, .018);
  pointer-events: none;
}

.brand-lockup {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 14px;
  width: fit-content;
  text-decoration: none;
}

.brand-mark {
  width: 54px;
  height: 54px;
  object-fit: contain;
  border-radius: 18px;
  background: var(--paper);
}

.wordmark {
  font-size: 1.08rem;
  font-weight: 800;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.identity-copy {
  position: relative;
  z-index: 1;
  max-width: 760px;
  padding: clamp(56px, 11vh, 140px) 0;
}

.eyebrow {
  margin: 0 0 20px;
  color: #67d7ca;
  font-size: .76rem;
  font-weight: 800;
  letter-spacing: .18em;
  text-transform: uppercase;
}

.identity-copy h1 {
  max-width: 12ch;
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(3rem, 7.2vw, 7.5rem);
  font-weight: 500;
  letter-spacing: -.065em;
  line-height: .89;
}

.identity-copy > p:last-child {
  max-width: 52ch;
  margin: 30px 0 0;
  color: rgba(246, 244, 236, .72);
  font-size: clamp(1rem, 1.45vw, 1.2rem);
  line-height: 1.65;
}

.identity-foot {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  color: rgba(246, 244, 236, .62);
  font-size: .84rem;
}

.environment-badge,
.state-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 6px 11px;
  border: 1px solid currentColor;
  border-radius: 999px;
  font-size: .72rem;
  font-weight: 850;
  letter-spacing: .1em;
  text-transform: uppercase;
}

.environment-badge::before,
.state-badge::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.account-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(26px, 5vw, 72px);
}

.account-surface {
  width: min(100%, 570px);
  padding: clamp(30px, 5vw, 58px);
  border: 1px solid var(--line);
  border-top: 5px solid var(--teal);
  background: rgba(255, 254, 250, .92);
  box-shadow: var(--shadow);
}

.surface-kicker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 38px;
}

.surface-kicker > span:first-child {
  color: var(--ink-muted);
  font-size: .76rem;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.state-badge { color: var(--teal-dark); }
.state-badge[data-tone="attention"] { color: #a04c26; }
.state-badge[data-tone="ended"] { color: var(--ink-muted); }

.account-surface h2 {
  max-width: 13ch;
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2.25rem, 5vw, 4.3rem);
  font-weight: 500;
  letter-spacing: -.05em;
  line-height: .98;
}

.lede {
  margin: 24px 0 0;
  color: var(--ink-muted);
  font-size: 1.02rem;
  line-height: 1.65;
}

.plan-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 34px 0 0;
  border-block: 1px solid var(--line);
}

.plan-fact { padding: 18px 0; }
.plan-fact:nth-child(even) { padding-left: 22px; border-left: 1px solid var(--line); }
.plan-fact:nth-child(n + 3) { border-top: 1px solid var(--line); }
.plan-fact dt { color: var(--ink-muted); font-size: .72rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.plan-fact dd { margin: 7px 0 0; font-weight: 760; }

.action-stack { display: grid; gap: 12px; margin-top: 34px; }

.primary-action,
.secondary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 52px;
  padding: 13px 20px;
  border: 1px solid var(--ink);
  border-radius: 0;
  cursor: pointer;
  font-weight: 820;
  text-decoration: none;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
}

.primary-action { background: var(--ink); color: var(--paper); box-shadow: 6px 6px 0 var(--coral); }
.secondary-action { background: transparent; color: var(--ink); }
.primary-action:hover, .secondary-action:hover { transform: translate(-2px, -2px); }
.primary-action:focus-visible, .secondary-action:focus-visible { outline: 3px solid var(--coral); outline-offset: 4px; }
.primary-action:disabled, .secondary-action:disabled { cursor: wait; opacity: .62; transform: none; }

.plan-choice {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 14px;
  min-height: 74px;
  padding: 14px 16px;
  border: 1px solid var(--line);
}

.plan-choice strong, .plan-choice span { display: block; }
.plan-choice span { margin-top: 3px; color: var(--ink-muted); font-size: .84rem; }
.plan-choice button { min-width: 104px; }

.fine-print,
.action-status {
  color: var(--ink-muted);
  font-size: .82rem;
  line-height: 1.55;
}

.action-status { min-height: 1.4em; margin: 16px 0 0; }

.proof-line {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
  color: var(--ink-muted);
  font-size: .82rem;
  line-height: 1.55;
}

.proof-line::before { content: "✓"; color: var(--teal-dark); font-weight: 900; }

@media (max-width: 900px) {
  .site-shell { grid-template-columns: 1fr; }
  .identity-panel { min-height: auto; padding: 26px; }
  .identity-copy { padding: 64px 0 74px; }
  .identity-copy h1 { max-width: 10ch; font-size: clamp(3.4rem, 14vw, 6rem); }
  .identity-foot { align-items: flex-end; }
  .account-panel { padding: 28px 18px 54px; }
  .account-surface { margin-top: -1px; }
}

@media (max-width: 520px) {
  .identity-copy { padding: 54px 0 58px; }
  .identity-foot { display: grid; }
  .account-surface { padding: 28px 22px 32px; }
  .surface-kicker { align-items: flex-start; flex-direction: column; margin-bottom: 28px; }
  .plan-facts { grid-template-columns: 1fr; }
  .plan-fact:nth-child(even) { padding-left: 0; border-left: 0; }
  .plan-fact + .plan-fact { border-top: 1px solid var(--line); }
  .plan-choice { grid-template-columns: 1fr; }
  .plan-choice button { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
}`;

const ACCOUNT_SCRIPT = `const MAX_STATUS_ATTEMPTS = 12;
const STATUS_DELAY_MS = 1500;

function safePolarUrl(value) {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    const polarHost = url.hostname === "polar.sh" || url.hostname.endsWith(".polar.sh");
    return url.protocol === "https:" && polarHost ? url.toString() : null;
  } catch {
    return null;
  }
}

async function hostedAction(responsePromise) {
  const response = await responsePromise;
  const payload = await response.json();
  const url = response.ok ? safePolarUrl(payload.url) : null;
  if (url === null) throw new Error("hosted action unavailable");
  window.location.assign(url);
}

for (const form of document.querySelectorAll("[data-checkout-form]")) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[data-plan]");
    const status = document.querySelector("#account-action-status");
    const plan = button?.dataset.plan;
    if (!(button instanceof HTMLButtonElement) || !(status instanceof HTMLElement) || (plan !== "monthly" && plan !== "yearly")) return;
    button.disabled = true;
    status.textContent = "Opening secure checkout...";
    try {
      await hostedAction(fetch("/v1/billing/checkout", {
        method: "POST",
        credentials: "same-origin",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ plan }),
      }));
    } catch {
      status.textContent = "Checkout is unavailable. Please retry.";
      button.disabled = false;
    }
  });
}

for (const form of document.querySelectorAll("[data-portal-form]")) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button");
    const status = document.querySelector("#account-action-status");
    if (!(button instanceof HTMLButtonElement) || !(status instanceof HTMLElement)) return;
    button.disabled = true;
    status.textContent = "Opening subscription management...";
    try {
      await hostedAction(fetch("/v1/billing/portal", {
        method: "POST",
        credentials: "same-origin",
      }));
    } catch {
      status.textContent = "The billing portal is unavailable. Please retry.";
      button.disabled = false;
    }
  });
}

function updatePaymentSurface(root, state) {
  const title = root.querySelector("[data-status-title]");
  const copy = root.querySelector("[data-status-copy]");
  const badge = root.querySelector("[data-status-badge]");
  const action = root.querySelector("[data-status-action]");
  if (!(title instanceof HTMLElement) || !(copy instanceof HTMLElement) || !(badge instanceof HTMLElement) || !(action instanceof HTMLAnchorElement)) return false;

  root.dataset.paymentState = state;
  action.href = "/account";
  action.textContent = "Open Emulo account";
  if (state === "active" || state === "trialing") {
    badge.textContent = "Active";
    badge.dataset.tone = "";
    title.textContent = "Emulo Pro activated";
    copy.textContent = "Your Emulo Pro subscription is active.";
    return true;
  }
  if (state === "past_due" || state === "grace") {
    badge.textContent = "Attention";
    badge.dataset.tone = "attention";
    title.textContent = "Billing needs attention";
    copy.textContent = "Open your account to review the subscription. Your local Emulo setup remains yours.";
    return true;
  }
  if (state === "ended" || state === "refunded") {
    badge.textContent = "Paused";
    badge.dataset.tone = "ended";
    title.textContent = "Cloud continuity is paused";
    copy.textContent = "Your local profiles and workflows remain yours.";
    return true;
  }
  return false;
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function pollPaymentStatus() {
  const root = document.querySelector('[data-payment-state="verifying"][data-authenticated="true"]');
  if (!(root instanceof HTMLElement)) return;
  for (let attempt = 0; attempt < MAX_STATUS_ATTEMPTS; attempt += 1) {
    try {
      const response = await fetch("/v1/account/status", {
        method: "GET",
        credentials: "same-origin",
        headers: { accept: "application/json" },
      });
      if (response.status === 401) {
        const title = root.querySelector("[data-status-title]");
        const copy = root.querySelector("[data-status-copy]");
        const badge = root.querySelector("[data-status-badge]");
        const action = root.querySelector("[data-status-action]");
        if (title instanceof HTMLElement) title.textContent = "Sign in to continue";
        if (copy instanceof HTMLElement) copy.textContent = "Use the same Emulo account you selected for your subscription.";
        if (badge instanceof HTMLElement) badge.textContent = "Reconnect";
        if (action instanceof HTMLAnchorElement) {
          action.href = "/v1/auth/github/start";
          action.textContent = "Continue with GitHub";
        }
        return;
      }
      if (response.ok) {
        const payload = await response.json();
        const state = payload?.entitlement?.state;
        if (typeof state === "string" && updatePaymentSurface(root, state)) return;
      }
    } catch {
      // Keep the truthful pending state and retry within the bounded window.
    }
    if (attempt + 1 < MAX_STATUS_ATTEMPTS) await wait(STATUS_DELAY_MS);
  }
  const title = root.querySelector("[data-status-title]");
  const copy = root.querySelector("[data-status-copy]");
  const badge = root.querySelector("[data-status-badge]");
  if (title instanceof HTMLElement) title.textContent = "Still confirming your subscription";
  if (copy instanceof HTMLElement) copy.textContent = "You can return to your account and check again in a moment.";
  if (badge instanceof HTMLElement) badge.textContent = "Pending";
}

function validDevice(value) {
  return value !== null && typeof value === "object" &&
    typeof value.deviceId === "string" && /^dev_[a-f0-9]{32}$/.test(value.deviceId) &&
    typeof value.label === "string" && value.label.length > 0 && value.label.length <= 64 &&
    typeof value.clientVersion === "string" &&
    typeof value.createdAt === "string" &&
    typeof value.lastSeenAt === "string" &&
    (value.state === "active" || value.state === "revoked");
}

function deviceDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Time unavailable" : date.toLocaleString();
}

async function loadDevices(root) {
  const list = root.querySelector("[data-device-list]");
  const status = root.querySelector("[data-continuity-status]");
  if (!(list instanceof HTMLElement) || !(status instanceof HTMLElement)) return;
  try {
    const response = await fetch("/v1/devices", {
      method: "GET",
      credentials: "same-origin",
      headers: { accept: "application/json" },
    });
    const payload = await response.json();
    if (!response.ok || !Array.isArray(payload.devices) || !payload.devices.every(validDevice)) throw new Error("invalid devices");
    list.replaceChildren();
    const active = payload.devices.filter((device) => device.state === "active");
    if (active.length === 0) {
      const empty = document.createElement("p");
      empty.className = "device-empty";
      empty.textContent = "No paired devices yet.";
      list.append(empty);
      return;
    }
    for (const device of active) {
      const row = document.createElement("div");
      row.className = "device-row";
      const copy = document.createElement("div");
      const label = document.createElement("strong");
      label.textContent = device.label;
      const meta = document.createElement("span");
      meta.className = "device-meta";
      meta.textContent = "Emulo " + device.clientVersion + " · Last active " + deviceDate(device.lastSeenAt);
      copy.append(label, meta);
      const revoke = document.createElement("button");
      revoke.type = "button";
      revoke.className = "secondary-action compact-action";
      revoke.textContent = "Revoke";
      revoke.addEventListener("click", async () => {
        if (!window.confirm("Revoke " + device.label + "? This device will stop syncing immediately.")) return;
        revoke.disabled = true;
        status.textContent = "Revoking device...";
        try {
          const revoked = await fetch("/v1/devices/" + encodeURIComponent(device.deviceId), {
            method: "DELETE",
            credentials: "same-origin",
          });
          if (!revoked.ok) throw new Error("revoke failed");
          status.textContent = "Device revoked.";
          await loadDevices(root);
        } catch {
          status.textContent = "The device could not be revoked. Please retry.";
          revoke.disabled = false;
        }
      });
      row.append(copy, revoke);
      list.append(row);
    }
  } catch {
    list.replaceChildren();
    const unavailable = document.createElement("p");
    unavailable.className = "device-empty";
    unavailable.textContent = "Devices could not be loaded. Please retry.";
    list.append(unavailable);
  }
}

function configureContinuityControls() {
  const root = document.querySelector("[data-continuity-root]");
  if (!(root instanceof HTMLElement)) return;
  const pairingButton = root.querySelector("[data-create-pairing-code]");
  const pairingResult = root.querySelector("[data-pairing-result]");
  const pairingCode = root.querySelector("[data-pairing-code]");
  const status = root.querySelector("[data-continuity-status]");
  if (pairingButton instanceof HTMLButtonElement && pairingResult instanceof HTMLElement && pairingCode instanceof HTMLElement && status instanceof HTMLElement) {
    pairingButton.addEventListener("click", async () => {
      pairingButton.disabled = true;
      status.textContent = "Creating a one-time pairing code...";
      try {
        const response = await fetch("/v1/devices/pair/start", {
          method: "POST",
          credentials: "same-origin",
          headers: { accept: "application/json" },
        });
        const payload = await response.json();
        if (!response.ok || typeof payload.pairingCode !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(payload.pairingCode) || !Number.isInteger(payload.expiresIn) || payload.expiresIn < 1 || payload.expiresIn > 600) throw new Error("pairing unavailable");
        pairingCode.textContent = payload.pairingCode;
        pairingResult.hidden = false;
        status.textContent = "Pairing code ready for 10 minutes.";
        window.setTimeout(() => {
          pairingCode.textContent = "Expired";
          status.textContent = "That pairing code expired. Create a new one when you are ready.";
        }, payload.expiresIn * 1000);
      } catch {
        status.textContent = "A pairing code could not be created. Please retry.";
      } finally {
        pairingButton.disabled = false;
      }
    });
  }

  const deletionForm = root.querySelector("[data-continuity-delete-form]");
  const confirmation = root.querySelector("[data-delete-confirmation-input]");
  const deletionButton = root.querySelector("[data-delete-continuity]");
  if (deletionForm instanceof HTMLFormElement && confirmation instanceof HTMLInputElement && deletionButton instanceof HTMLButtonElement && status instanceof HTMLElement) {
    const phrase = "delete-cloud-continuity";
    confirmation.addEventListener("input", () => {
      deletionButton.disabled = confirmation.value !== phrase;
    });
    deletionForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (confirmation.value !== phrase || !window.confirm("Delete all encrypted continuity data and revoke every paired device? Local files will remain.")) return;
      deletionButton.disabled = true;
      status.textContent = "Deleting cloud continuity...";
      try {
        const response = await fetch("/v1/continuity", {
          method: "DELETE",
          credentials: "same-origin",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ confirmation: phrase }),
        });
        if (response.status !== 204) throw new Error("delete failed");
        confirmation.value = "";
        status.textContent = "Cloud continuity deleted. Local files were not changed.";
        pairingResult?.setAttribute("hidden", "");
        await loadDevices(root);
      } catch {
        status.textContent = "Cloud continuity was not deleted. Please retry.";
        deletionButton.disabled = false;
      }
    });
  }
  void loadDevices(root);
}

configureContinuityControls();
void pollPaymentStatus();`;

export interface AccountRenderOptions {
  googleEnabled: boolean;
}

const DEFAULT_RENDER_OPTIONS: AccountRenderOptions = { googleEnabled: true };

function providerActions({ googleEnabled }: AccountRenderOptions): string {
  const googleAction = googleEnabled
    ? `<a class="provider-button provider-google" href="/v1/auth/google/start">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285f4" d="M21.6 12.23c0-.71-.06-1.24-.2-1.8H12v3.4h5.52a4.72 4.72 0 0 1-2.05 3.1v2.2h3.32c1.94-1.79 3.06-4.43 3.06-7.57z"/><path fill="#34a853" d="M12 22c2.77 0 5.1-.91 6.79-2.48l-3.32-2.58c-.92.62-2.1.99-3.47.99-2.67 0-4.93-1.8-5.74-4.23H2.83v2.66A10.26 10.26 0 0 0 12 22z"/><path fill="#fbbc05" d="M6.26 13.7A6.17 6.17 0 0 1 5.94 12c0-.59.1-1.16.32-1.7V7.64H2.83A10.02 10.02 0 0 0 1.75 12c0 1.61.39 3.14 1.08 4.36z"/><path fill="#ea4335" d="M12 6.07c1.5 0 2.84.52 3.9 1.52l2.96-2.95C17.1 3 14.77 2 12 2a10.26 10.26 0 0 0-9.17 5.64l3.43 2.66C7.07 7.87 9.33 6.07 12 6.07z"/></svg>
      <span>Continue with Google</span>
    </a>
    <span class="provider-divider">or</span>`
    : "";
  return `<div class="provider-actions">
    ${googleAction}
    <a class="provider-button provider-github" href="/v1/auth/github/start">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.61-3.37-1.18-3.37-1.18-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.9 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.64-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.03A9.6 9.6 0 0 1 12 7.7a9.6 9.6 0 0 1 2.5.34c1.91-1.3 2.75-1.03 2.75-1.03.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.86V21c0 .27.18.58.69.48A10 10 0 0 0 12 2z"/></svg>
      <span>Continue with GitHub</span>
    </a>
  </div>`;
}

function htmlDocument(
  title: string,
  _environment: "sandbox" | "production",
  surface: string,
  status = 200,
): Response {
  return new Response(
    `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${title}</title>
  <meta name="description" content="Emulo carries your way of working across AI agents.">
  <link rel="icon" href="/emulo.png" type="image/png">
  <link rel="stylesheet" href="/account.css">
</head>
<body>
  <header class="brand-header"><a class="brand-lockup" href="/account" aria-label="Emulo account home"><img class="brand-mark" src="/emulo.png" alt=""><span class="wordmark">Emulo</span></a></header>
  <main class="account-main">${surface}</main>
  <footer class="account-footer"><a href="/privacy.html">Privacy</a><a href="/terms.html">Terms</a><a href="/refunds.html">Refunds</a><a href="mailto:ohadkrispin@gmail.com">Contact</a></footer>
  <script src="/account.js" defer></script>
</body>
</html>`,
    { status, headers: DOCUMENT_HEADERS },
  );
}

export function renderAuthMessagePage(
  status: number,
  title: string,
  heading: string,
  message: string,
): Response {
  return htmlDocument(
    title,
    "production",
    `<article class="account-surface" data-account-state="auth-message">
      <h1>${heading}</h1>
      <p class="lede">${message}</p>
      <div class="action-stack"><a class="primary-action" href="/account">Return to Emulo account</a></div>
    </article>`,
    status,
  );
}

function productLabel(entitlement: EntitlementSummary): string {
  if (entitlement.productCode === "founding-yearly") return "Annual";
  if (entitlement.productCode === "founding-monthly") return "Monthly";
  return "Not started";
}

function activeSurface(entitlement: EntitlementSummary): string {
  return `<article class="account-surface account-surface-wide" data-account-state="${entitlement.state}">
    <div class="surface-kicker"><span>Emulo account</span><span class="state-badge">Active</span></div>
    <h2>Emulo Pro is active</h2>
    <p class="lede">Your subscription is connected. Approved generations can move between paired devices while raw sessions and decryption keys stay local.</p>
    <dl class="plan-facts"><div class="plan-fact"><dt>Plan</dt><dd>${productLabel(entitlement)}</dd></div><div class="plan-fact"><dt>Continuity</dt><dd>End-to-end encrypted</dd></div><div class="plan-fact"><dt>Device limit</dt><dd>5 paired devices</dd></div><div class="plan-fact"><dt>History</dt><dd>500 generations · 64 MiB</dd></div></dl>
    <div class="action-stack"><form data-portal-form><button class="primary-action" type="submit">Manage subscription</button></form><a class="secondary-action" href="/account">Refresh account</a></div>
    <p id="account-action-status" class="action-status" aria-live="polite"></p>
    <section class="continuity-root" data-continuity-root aria-labelledby="continuity-devices-title">
      <div class="continuity-heading">
        <div><p class="section-label">Devices</p><h3 id="continuity-devices-title">Keep your work in step</h3><p class="continuity-copy">Create a short-lived code, then connect Emulo from the device you trust.</p></div>
        <button class="secondary-action compact-action" type="button" data-create-pairing-code>Create pairing code</button>
      </div>
      <div class="pairing-result" data-pairing-result hidden aria-live="polite">
        <span class="section-label">One-time pairing code</span>
        <code class="pairing-code" data-pairing-code></code>
        <p class="continuity-copy">Run <code>emulo-autopilot continuity-connect --label &quot;My device&quot;</code>, then paste this code when prompted. It expires after 10 minutes.</p>
      </div>
      <div class="device-list" data-device-list aria-live="polite"><p class="device-empty">Loading paired devices...</p></div>
      <div class="continuity-links"><a class="secondary-action compact-action" href="/v1/continuity/export" download="emulo-continuity-export.json">Download encrypted export manifest</a></div>
      <section class="danger-zone" aria-labelledby="continuity-delete-title">
        <p class="section-label">Cloud data</p>
        <h3 id="continuity-delete-title">Delete cloud continuity</h3>
        <p class="continuity-copy">This removes hosted encrypted generations and revokes every paired device. Local files stay on your devices.</p>
        <form class="danger-form" data-continuity-delete-form>
          <label for="continuity-delete-confirmation">Type <code>delete-cloud-continuity</code> to confirm.</label>
          <input id="continuity-delete-confirmation" data-delete-confirmation-input autocomplete="off" autocapitalize="none" spellcheck="false">
          <button class="secondary-action" type="submit" data-delete-continuity disabled>Delete cloud continuity</button>
        </form>
      </section>
      <p class="action-status" data-continuity-status aria-live="polite"></p>
    </section>
  </article>`;
}

function attentionSurface(entitlement: EntitlementSummary): string {
  return `<article class="account-surface" data-account-state="${entitlement.state}">
    <div class="surface-kicker"><span>Emulo account</span><span class="state-badge" data-tone="attention">Attention</span></div>
    <h2>Billing needs attention</h2>
    <p class="lede">Open subscription management to resolve the issue. Cloud continuity may enter a grace period, but local Emulo stays yours.</p>
    <dl class="plan-facts"><div class="plan-fact"><dt>Plan</dt><dd>${productLabel(entitlement)}</dd></div><div class="plan-fact"><dt>Local engine</dt><dd>Still available</dd></div></dl>
    <div class="action-stack"><form data-portal-form><button class="primary-action" type="submit">Open billing portal</button></form><a class="secondary-action" href="/account">Refresh account</a></div>
    <p id="account-action-status" class="action-status" aria-live="polite"></p>
  </article>`;
}

function endedSurface(entitlement: EntitlementSummary): string {
  return `<article class="account-surface" data-account-state="${entitlement.state}">
    <div class="surface-kicker"><span>Emulo account</span><span class="state-badge" data-tone="ended">Paused</span></div>
    <h2>Cloud continuity is paused</h2>
    <p class="lede">New cloud writes have stopped. Your local profiles and workflows remain yours, including local history and rollback.</p>
    <dl class="plan-facts"><div class="plan-fact"><dt>Previous plan</dt><dd>${productLabel(entitlement)}</dd></div><div class="plan-fact"><dt>Open source</dt><dd>Unaffected</dd></div></dl>
    <div class="action-stack"><form data-portal-form><button class="primary-action" type="submit">Review subscription</button></form><a class="secondary-action" href="/account">Refresh account</a></div>
    <p id="account-action-status" class="action-status" aria-live="polite"></p>
  </article>`;
}

function noneSurface(checkoutEnabled: boolean): string {
  const actions = checkoutEnabled
    ? `<div class="action-stack">
        <form class="plan-choice" data-checkout-form><div><strong>Emulo Pro annual</strong><span>$79/year · Save 27%</span></div><button class="primary-action" type="submit" data-plan="yearly">Choose annual</button></form>
        <form class="plan-choice" data-checkout-form><div><strong>Emulo Pro monthly</strong><span>$9/month</span></div><button class="secondary-action" type="submit" data-plan="monthly">Choose monthly</button></form>
      </div>`
    : `<p class="fine-print">Emulo Pro is not available for purchase yet.</p>`;
  return `<article class="account-surface" data-account-state="none">
    <h2>${checkoutEnabled ? "Choose Emulo Pro" : "Your Emulo account is ready."}</h2>
    <p class="lede">Your account is connected. The local Emulo engine remains available without a subscription. Emulo Pro adds encrypted continuity, up to 5 devices, conflict-safe history, and a 30-day export window.</p>
    ${actions}
    <p id="account-action-status" class="action-status" aria-live="polite"></p>
  </article>`;
}

export function renderAccountPage(
  status: AccountStatus,
  options: AccountRenderOptions = DEFAULT_RENDER_OPTIONS,
): Response {
  if (!status.authenticated) {
    return htmlDocument(
      "Emulo account",
      status.environment,
      `<article class="account-surface" data-account-state="signed-out">
        <h1>Sign in to Emulo</h1>
        <p class="lede">Access your account and manage Emulo Pro.</p>
        ${providerActions(options)}
        <p class="identity-note">Emulo uses your sign-in provider only to verify your identity.</p>
      </article>`,
    );
  }

  const entitlement = status.entitlement;
  if (entitlement.state === "active" || entitlement.state === "trialing") {
    return htmlDocument("Emulo account", status.environment, activeSurface(entitlement));
  }
  if (entitlement.state === "past_due" || entitlement.state === "grace") {
    return htmlDocument("Emulo account", status.environment, attentionSurface(entitlement));
  }
  if (entitlement.state === "ended" || entitlement.state === "refunded") {
    return htmlDocument("Emulo account", status.environment, endedSurface(entitlement));
  }
  return htmlDocument("Emulo account", status.environment, noneSurface(status.checkoutEnabled));
}

function paymentSurface(status: AccountStatus, options: AccountRenderOptions): string {
  if (!status.authenticated) {
    return `<article class="account-surface" data-payment-state="verifying" data-authenticated="false" aria-live="polite">
      <h2 data-status-title>Sign in to continue</h2>
      <p class="lede" data-status-copy>Use the same Emulo account you selected for your subscription.</p>
      ${providerActions(options)}
    </article>`;
  }
  if (status.entitlement.state === "active" || status.entitlement.state === "trialing") {
    return `<article class="account-surface" data-payment-state="active" data-authenticated="true" aria-live="polite">
      <h2 data-status-title>Emulo Pro activated</h2>
      <p class="lede" data-status-copy>Your ${productLabel(status.entitlement).toLowerCase()} Emulo Pro plan is active.</p>
      <div class="action-stack"><a class="primary-action" data-status-action href="/account">Open Emulo account</a></div>
    </article>`;
  }
  if (status.entitlement.state === "past_due" || status.entitlement.state === "grace") {
    return `<article class="account-surface" data-payment-state="${status.entitlement.state}" data-authenticated="true" aria-live="polite">
      <h2 data-status-title>Your subscription needs attention</h2>
      <p class="lede" data-status-copy>Open your Emulo account to review the subscription. Your local Emulo setup remains yours.</p>
      <div class="action-stack"><a class="primary-action" data-status-action href="/account">Open Emulo account</a></div>
    </article>`;
  }
  if (status.entitlement.state === "ended" || status.entitlement.state === "refunded") {
    return `<article class="account-surface" data-payment-state="${status.entitlement.state}" data-authenticated="true" aria-live="polite">
      <h2 data-status-title>Cloud continuity is paused</h2>
      <p class="lede" data-status-copy>Your local Emulo profiles and workflows remain yours.</p>
      <div class="action-stack"><a class="primary-action" data-status-action href="/account">Open Emulo account</a></div>
    </article>`;
  }
  return `<article class="account-surface" data-payment-state="verifying" data-authenticated="true" aria-live="polite">
    <h2 data-status-title>Confirming your subscription</h2>
    <span class="sr-only" data-status-badge>Confirming</span>
    <p class="lede" data-status-copy>This can take a few seconds. You can safely return to your account while Emulo finishes.</p>
    <div class="action-stack"><a class="primary-action" data-status-action href="/account">Return to account</a></div>
  </article>`;
}

export function renderPaymentPage(
  status: AccountStatus,
  options: AccountRenderOptions = DEFAULT_RENDER_OPTIONS,
): Response {
  return htmlDocument("Verify Emulo access", status.environment, paymentSurface(status, options));
}

export function unavailablePage(): Response {
  return htmlDocument(
    "Emulo account unavailable",
    "sandbox",
    `<article class="account-surface" data-account-state="unavailable">
      <div class="surface-kicker"><span>Emulo account</span><span class="state-badge" data-tone="attention">Unavailable</span></div>
      <h2>We could not load the account safely</h2>
      <p class="lede">No account or billing state was changed. Please retry in a moment.</p>
      <div class="action-stack"><a class="primary-action" href="/account">Retry account</a></div>
    </article>`,
  );
}

export function accountStyles(): Response {
  return new Response(professionalAccountStyles, {
    status: 200,
    headers: {
      "cache-control": "public, max-age=300",
      "content-type": "text/css; charset=utf-8",
      "referrer-policy": "no-referrer",
      "x-content-type-options": "nosniff",
    },
  });
}

export function accountScript(): Response {
  return new Response(ACCOUNT_SCRIPT, {
    status: 200,
    headers: {
      "cache-control": "public, max-age=300",
      "content-type": "text/javascript; charset=utf-8",
      "referrer-policy": "no-referrer",
      "x-content-type-options": "nosniff",
    },
  });
}
