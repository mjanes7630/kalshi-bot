# Developer Demo Soak Monitoring Kit

This kit is for a developer monitoring the **demo-only** Kalshi Bot soak.
It gives you a safe, repeatable way to observe the service and publish a short
report without changing the bot or exposing credentials.

## What you are responsible for

- Confirm that the `kalshi-bot.service` systemd service is running.
- Review recent lifecycle logs for normal behavior, warnings, and errors.
- Record what you observed in a Markdown report.
- Escalate problems to the project owner with the time, exact event, and
  relevant log excerpt.

## What you must not do

- Do not open, copy, commit, or share `.env`, private-key files, API key IDs,
  passwords, SSH credentials, or remote-access credentials.
- Do not change settings, market tickers, risk limits, execution flags, source
  code, Git configuration, or systemd service files.
- Do not start, stop, restart, or reload the service unless the project owner
  explicitly instructs you to do so.
- Do not manually cancel orders unless the project owner explicitly instructs
  you to do so.

When uncertain: **do not change anything. Preserve the logs and contact the
project owner.**

## How to use this kit

1. Read [the monitoring guide](monitoring-guide.md) before your first check.
2. Copy [the report template](report-template.md) into `reports/` using the
   required filename format.
3. Commit only your completed report on your own monitoring branch and open a
   pull request for review.

The companion `monitoring/example-report` branch contains a fictional finished
report that demonstrates the expected format. Do not edit that branch; create
your own branch from the approved monitoring-kit branch.
