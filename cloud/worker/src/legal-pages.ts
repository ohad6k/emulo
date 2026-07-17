import legalStylesText from "../../../site/legal.css";
import privacyHtml from "../../../site/privacy.html";
import refundsHtml from "../../../site/refunds.html";
import termsHtml from "../../../site/terms.html";

const POLICY_HEADERS = {
  "cache-control": "public, max-age=300",
  "content-security-policy":
    "default-src 'self'; img-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
  "content-type": "text/html; charset=utf-8",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
};

const policies: Record<string, string> = {
  "/privacy.html": privacyHtml,
  "/refunds.html": refundsHtml,
  "/terms.html": termsHtml,
};

export function renderWorkerPolicy(path: string): Response {
  const body = policies[path];
  if (body === undefined) {
    return Response.json(
      { status: "not-found" },
      { status: 404, headers: { "cache-control": "no-store" } },
    );
  }
  return new Response(body, { status: 200, headers: POLICY_HEADERS });
}

export function legalStyles(): Response {
  return new Response(legalStylesText, {
    status: 200,
    headers: {
      "cache-control": "public, max-age=300",
      "content-type": "text/css; charset=utf-8",
      "referrer-policy": "no-referrer",
      "x-content-type-options": "nosniff",
    },
  });
}
