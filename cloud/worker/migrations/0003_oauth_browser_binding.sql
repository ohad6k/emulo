DROP INDEX oauth_flows_expiry_idx;
DROP TABLE oauth_flows;

CREATE TABLE oauth_flows (
  state_hash TEXT PRIMARY KEY CHECK (length(state_hash) = 64),
  browser_binding_hash TEXT NOT NULL CHECK (length(browser_binding_hash) = 64),
  code_verifier TEXT NOT NULL CHECK (length(code_verifier) BETWEEN 43 AND 128),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  CHECK (
    expires_at > created_at
    AND unixepoch(expires_at) - unixepoch(created_at) <= 600
  )
);

CREATE INDEX oauth_flows_expiry_idx ON oauth_flows(expires_at);
