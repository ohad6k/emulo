"""Every redaction pattern SECURITY.md names, one realistic fake sample each.

Shared by tests/test_redaction_table.py and site/scan.test.cjs (which asks
Python for these rows), so the browser port is held to the same samples.

`doc` is the phrase SECURITY.md uses for the pattern; the tests require it to
appear there, and require every backticked token in that section to be claimed
here, so the doc and the table cannot drift apart silently.

Keys are assembled from parts so no secret scanner reads a fixture as a live
credential.
"""

_BODY = "Ab3_dE-fGh" * 5
_ALNUM = "T3stF4keKeyAbCdEfGh1234567890abcd"
_JWT = ".".join(("eyJ" + "hbGciOiJIUzI1NiJ9", "eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0",
                 "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"))


def _row(doc, text, expected):
    return {"doc": doc, "input": text, "expected": expected}


ROWS = [
    # OpenAI
    _row("`sk-`", "key " + "sk-" + _ALNUM, "key [OPENAI_KEY]"),
    _row("`sk-proj-`", "key " + "sk-" + "proj-" + _BODY, "key [OPENAI_KEY]"),
    _row("`sk-svcacct-`", "key " + "sk-" + "svcacct-" + _BODY, "key [OPENAI_KEY]"),
    _row("`sk-admin-`", "key " + "sk-" + "admin-" + _BODY, "key [OPENAI_KEY]"),
    # Anthropic, Google
    _row("`sk-ant-`", "key " + "sk-" + "ant-api03-" + _BODY + "AA", "key [ANTHROPIC_KEY]"),
    _row("`AIza`", "key " + "AI" + "za" + "SyD3_x-9QwErTyUiOpAsDfGhJkLzXcVbN12", "key [GOOGLE_API_KEY]"),
    # Stripe, webhooks, Supabase
    _row("`sk_live_`", "key " + "sk_" + "live_" + _ALNUM, "key [STRIPE_KEY]"),
    _row("`whsec_`", "key " + "whsec" + "_" + _ALNUM, "key [WEBHOOK_SECRET]"),
    _row("`sbp_`", "key " + "sbp" + "_" + _ALNUM, "key [SUPABASE_TOKEN]"),
    # GitHub, one row per prefix
    *[_row(f"`gh{c}_`", "key " + "gh" + c + "_" + _ALNUM, "key [GITHUB_TOKEN]") for c in "pousr"],
    # JWT, AWS access key id
    _row("`eyJ`", "bearer " + _JWT, "bearer [JWT]"),
    _row("`AKIA`", "id " + "AK" + "IA" + "Q3EGT7XKZ2M4B6NP", "id [AWS_KEY]"),
    # Slack, one row per prefix
    *[_row(f"`xox{c}-`", "tok " + "xo" + "x" + c + "-" + "1234567890-abcdef", "tok [SLACK_TOKEN]")
      for c in "baprs"],
    # the password in a connection URL, across schemes
    *[_row("`scheme://user:password@host`", f"{scheme}://app:S3cretPw9@db.internal:5432/app",
           f"{scheme}://app:[REDACTED]@db.internal:5432/app")
      for scheme in ("postgres", "postgresql", "mysql", "mongodb+srv", "redis", "amqp", "https")],
    _row("`scheme://user:password@host`", "redis://:Sup3rPw@localhost:6379/0",
         "redis://:[REDACTED]@localhost:6379/0"),
    _row("`%23`", "postgres://u:p%23ss@db.internal/app", "postgres://u:[REDACTED]@db.internal/app"),
    # personal information
    _row("email addresses", "mail dev@example.com today", "mail [EMAIL] today"),
    _row("phone numbers with an international or trunk prefix", "call +972 52-123-4567.", "call [PHONE]."),
    _row("phone numbers with an international or trunk prefix", "call 052-1234567", "call [PHONE]"),
    _row("IPv4 addresses", "host 10.20.30.40 is down", "host [IP] is down"),
    # assignments to a name ending in a keyword, any case
    _row("`api_key`", "API_KEY=abc123xyz", "API_KEY=[REDACTED]"),
    _row("`apikey`", "apikey: abc123xyz", "apikey=[REDACTED]"),
    _row("`api-key`", "x-api-key=abc123xyz", "x-api-key=[REDACTED]"),
    _row("`secret`", "secret = abc123xyz", "secret=[REDACTED]"),
    _row("`client_secret=`", "client_secret=abc123xyz", "client_secret=[REDACTED]"),
    _row("`token`", "token: abc123xyz", "token=[REDACTED]"),
    _row("`GITHUB_TOKEN=`", "GITHUB_TOKEN=abc123xyz", "GITHUB_TOKEN=[REDACTED]"),
    _row("`password`", "password=abc123xyz", "password=[REDACTED]"),
    _row("`passwd`", "passwd: abc123xyz", "passwd=[REDACTED]"),
    # spoken forms, which the assignment rule cannot see
    _row("`password is`", "the wifi password is Hunter2!x", "the wifi password=[REDACTED]"),
    _row("`passwd`", "passwd hunter2x9", "passwd=[REDACTED]"),
    _row("`passphrase`", "passphrase correct-horse-9", "passphrase=[REDACTED]"),
    _row("`passkey`", "passkey Zx81kQ7", "passkey=[REDACTED]"),
    _row("`psk`", "psk Tr0ub4dor3", "psk=[REDACTED]"),
    _row("`wifi key`", "wifi key abc12345", "wifi key=[REDACTED]"),
]

# What SECURITY.md says is NOT redacted. Pinned so a fix updates the doc too.
MISSES = [
    _row("`AWS_SECRET_ACCESS_KEY=...`",
         "AWS_SECRET_ACCESS_KEY=" + "wJalrXUtnFEMI" + "K7MDENGbPxRfiCYEXAMPLEKEY",
         "AWS_SECRET_ACCESS_KEY=" + "wJalrXUtnFEMI" + "K7MDENGbPxRfiCYEXAMPLEKEY"),
]

# URL passwords SECURITY.md lists as misses: none is valid unencoded, and the
# encoded form (%23 above) is redacted.
MISSES += [
    _row("`#`", "postgres://u:p#ss@host/db", "postgres://u:p#ss@host/db"),
    _row("`/`", "postgres://u:p/ss@host/db", "postgres://u:p/ss@host/db"),
    _row("`?`", "postgres://u:p?ss@host/db", "postgres://u:p?ss@host/db"),
    _row("a space", "postgres://u:p ss@host/db", "postgres://u:p ss@host/db"),
    _row("`postgres://user@corp.com:pw@host`", "postgres://user@corp.com:pw@host/db",
         "postgres://[EMAIL]:pw@host/db"),
]

# Text no rule may touch. Kebab-case words that contain a key prefix mid-word
# came up in real logs (branch names, tool names) and were eaten as keys.
NEGATIVES = [
    _row("", text, text) for text in (
        # Split literals so secret scanners do not read these as keys.
        "feature/tas" "k-admin-bulk-actions-endpoint",
        "ris" "k-admin-tool-configuration-panel-v2",
        "tas" "k-proj-migration-2026-planning-doc",
        "des" "k-ant-colony-simulation-renderer",
        "whis" "k-svcacct-rotation-runbook-for-ops",
        "git checkout feature/tas" "k-admin-bulk-actions-endpoint && npm test",
    )
]

# Backticked tokens in that SECURITY.md section that name syntax, not a pattern.
STRUCTURAL_TOKENS = {"`=`", "`:`", "`ACCESS_KEY`", "`tests/test_redaction_table.py`",
                     "`--no-redact`"}
