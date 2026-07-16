import type { Env } from "./contracts";
import { beginGitHubOAuth, completeGitHubOAuth } from "./github-auth";
import { handlePolarWebhook } from "./polar";
import { handlePolarCheckout, handlePolarPortal } from "./polar-client";

function json(status: number, body: Record<string, string>): Response {
  return Response.json(body, {
    status,
    headers: {
      "cache-control": "no-store",
    },
  });
}

function page(title: string, message: string): Response {
  return new Response(
    `<!doctype html><meta charset="utf-8"><title>${title}</title><main><h1>${title}</h1><p>${message}</p></main>`,
    {
      status: 200,
      headers: {
        "cache-control": "no-store",
        "content-security-policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        "content-type": "text/html; charset=utf-8",
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
      },
    },
  );
}

const ACCOUNT_SCRIPT = `for (const form of document.querySelectorAll("[data-checkout-form]")) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[data-plan]");
    const status = document.querySelector("#checkout-status");
    const plan = button?.dataset.plan;
    if (!(button instanceof HTMLButtonElement) || !(status instanceof HTMLElement) || (plan !== "monthly" && plan !== "yearly")) return;
    button.disabled = true;
    status.textContent = "Creating secure Polar Sandbox checkout...";
    try {
      const response = await fetch("/v1/billing/checkout", {
        method: "POST",
        credentials: "same-origin",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ plan }),
      });
      const payload = await response.json();
      if (!response.ok || typeof payload.url !== "string") {
        status.textContent = "Checkout unavailable (" + response.status + ").";
        button.disabled = false;
        return;
      }
      window.location.assign(payload.url);
    } catch {
      status.textContent = "Checkout unavailable. Please retry.";
      button.disabled = false;
    }
  });
}`;

function accountPage(checkoutEnabled: boolean): Response {
  const disabled = checkoutEnabled ? "" : " disabled aria-disabled=\"true\"";
  const status = checkoutEnabled
    ? "Sandbox checkout is enabled for the private lifecycle test."
    : "Sandbox checkout is disabled.";
  return new Response(
    `<!doctype html><meta charset="utf-8"><title>Emulo account</title><main><h1>Emulo account</h1><p>Your browser account is connected. Billing and Autopilot controls remain in the local Emulo control center.</p><h2>Founding beta sandbox</h2><form data-checkout-form><button type="submit" data-plan="monthly"${disabled}>Test $9/month</button></form><form data-checkout-form><button type="submit" data-plan="yearly"${disabled}>Test $79/year</button></form><p id="checkout-status" aria-live="polite">${status}</p></main><script src="/account.js" defer></script>`,
    {
      status: 200,
      headers: {
        "cache-control": "no-store",
        "content-security-policy": "default-src 'none'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        "content-type": "text/html; charset=utf-8",
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
      },
    },
  );
}

function accountScript(): Response {
  return new Response(ACCOUNT_SCRIPT, {
    status: 200,
    headers: {
      "cache-control": "public, max-age=300",
      "content-security-policy": "default-src 'none'",
      "content-type": "text/javascript; charset=utf-8",
      "referrer-policy": "no-referrer",
      "x-content-type-options": "nosniff",
    },
  });
}

export default {
  async fetch(request, env, _context?): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/healthz") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return json(200, {
        service: "emulo-autopilot-api",
        status: "ok",
      });
    }
    if (url.pathname === "/account") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return accountPage(
        env.PAID_CHECKOUT_ENABLED === "true" && env.POLAR_SERVER === "sandbox",
      );
    }
    if (url.pathname === "/account.js") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return accountScript();
    }
    if (url.pathname === "/v1/billing/complete") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return page(
        "Payment submitted",
        "Emulo enables cloud access only after a verified Polar confirmation. You can return to the local control center.",
      );
    }
    if (url.pathname === "/v1/billing/webhooks/polar") {
      if (request.method !== "POST") {
        return json(405, { status: "method-not-allowed" });
      }
      return handlePolarWebhook(request, env);
    }
    if (url.pathname === "/v1/auth/github/start") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return beginGitHubOAuth(env);
    }
    if (url.pathname === "/v1/auth/github/callback") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return completeGitHubOAuth(request, env);
    }
    if (url.pathname === "/v1/billing/checkout") {
      if (request.method !== "POST") {
        return json(405, { status: "method-not-allowed" });
      }
      return handlePolarCheckout(request, env);
    }
    if (url.pathname === "/v1/billing/portal") {
      if (request.method !== "POST") {
        return json(405, { status: "method-not-allowed" });
      }
      return handlePolarPortal(request, env);
    }
    return json(404, { status: "not-found" });
  },
} satisfies ExportedHandler<Env>;
