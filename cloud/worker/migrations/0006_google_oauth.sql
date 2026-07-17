PRAGMA foreign_keys = OFF;

DROP INDEX oauth_flows_expiry_idx;
ALTER TABLE oauth_flows RENAME TO oauth_flows_v1;

CREATE TABLE oauth_flows (
  state_hash TEXT PRIMARY KEY CHECK (length(state_hash) = 64),
  provider TEXT NOT NULL CHECK (provider IN ('github', 'google')),
  browser_binding_hash TEXT NOT NULL CHECK (length(browser_binding_hash) = 64),
  code_verifier TEXT NOT NULL CHECK (length(code_verifier) BETWEEN 43 AND 128),
  nonce_hash TEXT,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  CHECK (
    (provider = 'github' AND nonce_hash IS NULL)
    OR (provider = 'google' AND length(nonce_hash) = 64)
  ),
  CHECK (
    expires_at > created_at
    AND unixepoch(expires_at) - unixepoch(created_at) <= 600
  )
);

INSERT INTO oauth_flows
  (state_hash, provider, browser_binding_hash, code_verifier, nonce_hash, created_at, expires_at)
SELECT state_hash, 'github', browser_binding_hash, code_verifier, NULL, created_at, expires_at
FROM oauth_flows_v1;

DROP TABLE oauth_flows_v1;
CREATE INDEX oauth_flows_expiry_idx ON oauth_flows(expires_at);

DROP INDEX oauth_identities_account_idx;
ALTER TABLE oauth_identities RENAME TO oauth_identities_v1;

CREATE TABLE oauth_identities (
  provider TEXT NOT NULL CHECK (provider IN ('github', 'google')),
  provider_user_id TEXT NOT NULL CHECK (
    (provider = 'github'
      AND length(provider_user_id) BETWEEN 1 AND 32
      AND provider_user_id NOT GLOB '*[^0-9]*')
    OR (provider = 'google' AND length(provider_user_id) BETWEEN 1 AND 255)
  ),
  account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  PRIMARY KEY (provider, provider_user_id),
  UNIQUE (provider, account_id)
);

INSERT INTO oauth_identities
  (provider, provider_user_id, account_id, created_at)
SELECT provider, provider_user_id, account_id, created_at
FROM oauth_identities_v1;

DROP TABLE oauth_identities_v1;
CREATE INDEX oauth_identities_account_idx ON oauth_identities(account_id);

DROP INDEX oauth_diagnostics_created_idx;
ALTER TABLE oauth_diagnostics RENAME TO oauth_diagnostics_v2;

CREATE TABLE oauth_diagnostics (
  diagnostic_id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL CHECK (provider IN ('github', 'google')),
  stage TEXT NOT NULL CHECK (
    stage IN (
      'token_exchange',
      'user_lookup',
      'id_token_verification',
      'identity_write',
      'session_write'
    )
  ),
  status_code INTEGER CHECK (status_code BETWEEN 100 AND 599),
  error_code TEXT,
  created_at TEXT NOT NULL
);

INSERT INTO oauth_diagnostics
  (diagnostic_id, provider, stage, status_code, error_code, created_at)
SELECT diagnostic_id, provider, stage, status_code, error_code, created_at
FROM oauth_diagnostics_v2;

DROP TABLE oauth_diagnostics_v2;
CREATE INDEX oauth_diagnostics_created_idx
  ON oauth_diagnostics(created_at DESC);

PRAGMA foreign_keys = ON;
