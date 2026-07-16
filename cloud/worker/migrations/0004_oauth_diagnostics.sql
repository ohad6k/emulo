CREATE TABLE oauth_diagnostics (
  diagnostic_id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL CHECK (provider = 'github'),
  stage TEXT NOT NULL CHECK (stage IN ('token_exchange', 'user_lookup')),
  status_code INTEGER CHECK (status_code BETWEEN 100 AND 599),
  error_code TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX oauth_diagnostics_created_idx
  ON oauth_diagnostics(created_at DESC);
