PRAGMA foreign_keys = ON;

CREATE TABLE oauth_flows (
  state_hash TEXT PRIMARY KEY CHECK (length(state_hash) = 64),
  code_verifier TEXT NOT NULL CHECK (length(code_verifier) BETWEEN 43 AND 128),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  CHECK (
    expires_at > created_at
    AND unixepoch(expires_at) - unixepoch(created_at) <= 600
  )
);

CREATE INDEX oauth_flows_expiry_idx ON oauth_flows(expires_at);

CREATE TABLE oauth_identities (
  provider TEXT NOT NULL CHECK (provider = 'github'),
  provider_user_id TEXT NOT NULL
    CHECK (length(provider_user_id) BETWEEN 1 AND 32),
  account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  PRIMARY KEY (provider, provider_user_id),
  UNIQUE (provider, account_id)
);

CREATE INDEX oauth_identities_account_idx ON oauth_identities(account_id);

CREATE TABLE browser_sessions (
  session_hash TEXT PRIMARY KEY CHECK (length(session_hash) = 64),
  account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  CHECK (expires_at > created_at)
);

CREATE INDEX browser_sessions_account_idx ON browser_sessions(account_id);
CREATE INDEX browser_sessions_expiry_idx ON browser_sessions(expires_at);
