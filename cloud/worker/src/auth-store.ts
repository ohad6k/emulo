const HASH_PATTERN = /^[a-f0-9]{64}$/;
const ACCOUNT_PATTERN = /^acct_[a-f0-9]{32}$/;
const GITHUB_USER_PATTERN = /^[0-9]{1,32}$/;
const VERIFIER_PATTERN = /^[A-Za-z0-9._~-]{43,128}$/;
const UTC_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;

interface OAuthFlowInput {
  stateHash: string;
  codeVerifier: string;
  createdAt: string;
  expiresAt: string;
}

interface IdentityInput {
  providerUserId: string;
  proposedAccountId: string;
  createdAt: string;
}

interface BrowserSessionInput {
  sessionHash: string;
  accountId: string;
  createdAt: string;
  expiresAt: string;
}

function assertTimestamp(value: string, label: string): void {
  if (!UTC_PATTERN.test(value) || !Number.isFinite(Date.parse(value))) {
    throw new Error(`${label} is invalid`);
  }
}

function assertWindow(
  createdAt: string,
  expiresAt: string,
  maximumMilliseconds?: number,
): void {
  assertTimestamp(createdAt, "created timestamp");
  assertTimestamp(expiresAt, "expiry timestamp");
  if (expiresAt <= createdAt) {
    throw new Error("expiry must follow creation");
  }
  if (
    maximumMilliseconds !== undefined &&
    Date.parse(expiresAt) - Date.parse(createdAt) > maximumMilliseconds
  ) {
    throw new Error("OAuth flow lifetime is too long");
  }
}

export async function createOAuthFlow(
  db: D1Database,
  input: OAuthFlowInput,
): Promise<void> {
  if (!HASH_PATTERN.test(input.stateHash)) {
    throw new Error("OAuth state hash is invalid");
  }
  if (!VERIFIER_PATTERN.test(input.codeVerifier)) {
    throw new Error("OAuth code verifier is invalid");
  }
  assertWindow(input.createdAt, input.expiresAt, 10 * 60 * 1000);
  await db
    .prepare(
      `INSERT INTO oauth_flows
       (state_hash, code_verifier, created_at, expires_at)
       VALUES (?, ?, ?, ?)`,
    )
    .bind(input.stateHash, input.codeVerifier, input.createdAt, input.expiresAt)
    .run();
}

export async function consumeOAuthFlow(
  db: D1Database,
  stateHash: string,
  now: string,
): Promise<{ codeVerifier: string } | null> {
  if (!HASH_PATTERN.test(stateHash)) {
    return null;
  }
  assertTimestamp(now, "current timestamp");
  const consumed = await db
    .prepare(
      `DELETE FROM oauth_flows
       WHERE state_hash = ? AND expires_at > ?
       RETURNING code_verifier`,
    )
    .bind(stateHash, now)
    .first<{ code_verifier: string }>();
  if (consumed !== null) {
    return { codeVerifier: consumed.code_verifier };
  }
  await db
    .prepare("DELETE FROM oauth_flows WHERE state_hash = ? AND expires_at <= ?")
    .bind(stateHash, now)
    .run();
  return null;
}

export async function resolveOrCreateGitHubIdentity(
  db: D1Database,
  input: IdentityInput,
): Promise<string> {
  if (!GITHUB_USER_PATTERN.test(input.providerUserId)) {
    throw new Error("GitHub user ID is invalid");
  }
  if (!ACCOUNT_PATTERN.test(input.proposedAccountId)) {
    throw new Error("proposed account ID is invalid");
  }
  assertTimestamp(input.createdAt, "created timestamp");
  const existing = await db
    .prepare(
      `SELECT account_id FROM oauth_identities
       WHERE provider = 'github' AND provider_user_id = ?`,
    )
    .bind(input.providerUserId)
    .first<{ account_id: string }>();
  if (existing !== null) {
    return existing.account_id;
  }

  await db.batch([
    db
      .prepare("INSERT OR IGNORE INTO accounts (account_id, created_at) VALUES (?, ?)")
      .bind(input.proposedAccountId, input.createdAt),
    db
      .prepare(
        `INSERT OR IGNORE INTO oauth_identities
         (provider, provider_user_id, account_id, created_at)
         VALUES ('github', ?, ?, ?)`,
      )
      .bind(input.providerUserId, input.proposedAccountId, input.createdAt),
  ]);
  const resolved = await db
    .prepare(
      `SELECT account_id FROM oauth_identities
       WHERE provider = 'github' AND provider_user_id = ?`,
    )
    .bind(input.providerUserId)
    .first<{ account_id: string }>();
  if (resolved === null) {
    throw new Error("GitHub identity could not be created");
  }
  if (resolved.account_id !== input.proposedAccountId) {
    await db
      .prepare(
        `DELETE FROM accounts
         WHERE account_id = ?
           AND NOT EXISTS (
             SELECT 1 FROM oauth_identities WHERE account_id = ?
           )`,
      )
      .bind(input.proposedAccountId, input.proposedAccountId)
      .run();
  }
  return resolved.account_id;
}

export async function createBrowserSession(
  db: D1Database,
  input: BrowserSessionInput,
): Promise<void> {
  if (!HASH_PATTERN.test(input.sessionHash)) {
    throw new Error("session hash is invalid");
  }
  if (!ACCOUNT_PATTERN.test(input.accountId)) {
    throw new Error("account ID is invalid");
  }
  assertWindow(input.createdAt, input.expiresAt);
  await db
    .prepare(
      `INSERT INTO browser_sessions
       (session_hash, account_id, created_at, expires_at, revoked_at)
       VALUES (?, ?, ?, ?, NULL)`,
    )
    .bind(input.sessionHash, input.accountId, input.createdAt, input.expiresAt)
    .run();
}

export async function resolveBrowserSession(
  db: D1Database,
  sessionHash: string,
  now: string,
): Promise<{ accountId: string } | null> {
  if (!HASH_PATTERN.test(sessionHash)) {
    return null;
  }
  assertTimestamp(now, "current timestamp");
  const session = await db
    .prepare(
      `SELECT account_id FROM browser_sessions
       WHERE session_hash = ? AND revoked_at IS NULL AND expires_at > ?`,
    )
    .bind(sessionHash, now)
    .first<{ account_id: string }>();
  return session === null ? null : { accountId: session.account_id };
}

export async function revokeBrowserSession(
  db: D1Database,
  sessionHash: string,
  revokedAt: string,
): Promise<void> {
  if (!HASH_PATTERN.test(sessionHash)) {
    return;
  }
  assertTimestamp(revokedAt, "revocation timestamp");
  await db
    .prepare(
      `UPDATE browser_sessions
       SET revoked_at = COALESCE(revoked_at, ?)
       WHERE session_hash = ?`,
    )
    .bind(revokedAt, sessionHash)
    .run();
}
