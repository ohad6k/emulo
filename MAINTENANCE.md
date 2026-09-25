# Maintenance

Emulo is finished software. It does what the README and the [profile flow guide](docs/PROFILE-FLOW.md) describe, and from here it is maintained rather than developed.

## What gets fixed

- **Security and redaction defects.** A secret format that should be redacted and is not, a redaction rule that mangles ordinary text, or anything that sends your data somewhere the docs say it does not go. Report these privately: use GitHub's "Report a vulnerability" button on the Security tab, not a public issue.
- **The advertised path breaking.** If installing, mining, installing a profile or loading it in a host listed as verified stops working as documented, that is a bug.
- **Reproducible bugs.** A crash or a wrong result that you can show with steps, a version and, where it matters, a sanitised example. Never paste real session logs.

## What does not, by default

- New session sources or install targets
- New features or modes
- Redesigns of the site or the output
- Research into whether the profile improves agent output. What has been measured is published on [the placebo page](https://emulo.vercel.app/placebo) and is not being extended.

Pull requests in these areas may still be read, but there is no commitment to review or merge them.

## How to report

Open an issue with the steps, `emulo --version`, your OS and Python version, and what you expected. Security issues go through the Security tab's private report, never a public issue.

## What to expect

Fixes ship as patch releases on PyPI. This is maintained by one person alongside other work, so there is no response-time promise.
