# Developer Demo Soak Monitoring Guide

## Purpose

The bot runs as a Linux system service on the demo PC. Your job is to observe
and document it, not to operate its trading controls. This is a demo-only soak,
but the same discipline protects later live testing.

## Before you connect

Use only the remote-access method and connection address supplied by the
project owner. Do not place connection addresses, passwords, API credentials,
or `.env` values in a report or Git commit.

After connecting, go to the project directory:

```bash
cd ~/kalshi-bot
```

- `cd` means "change directory."
- `~` means the current Linux user's home directory.
- This command does not start, stop, or change the bot.

## Standard check: service status

Run:

```bash
sudo systemctl status kalshi-bot.service --no-pager
```

- `sudo` runs this read-only status command with the permission needed to view
  the system service.
- `systemctl` is Linux's service-management command.
- `status` displays whether the named service is running and its recent log
  lines.
- `kalshi-bot.service` is the demo-soak service.
- `--no-pager` prints output directly in the terminal rather than opening a
  scrollable viewer.

### Normal result

The important line is:

```text
Active: active (running)
```

Record the active state, start time, and process ID in your report. Memory and
CPU values are informational unless they grow dramatically between checks.

### Warning result

If the service is `activating`, `failed`, `inactive`, repeatedly restarting, or
missing, do **not** restart it yourself. Capture the status output and recent
logs, then escalate to the project owner.

## Standard check: recent bot logs

Run:

```bash
sudo journalctl -u kalshi-bot.service -n 100 -o cat --no-pager
```

- `journalctl` reads systemd's stored logs.
- `-u kalshi-bot.service` limits results to this bot service.
- `-n 100` requests the most recent 100 log lines.
- `-o cat` hides systemd's extra prefix so the bot's structured log fields are
  easier to read.
- `--no-pager` prints directly in the terminal.

The journal is persisted on the demo PC, so this command can also show events
from before a reboot.

## What normal lifecycle activity looks like

Healthy cycles normally contain these events in this order:

1. `demo_lifecycle_cycle_started`
2. Successful API calls (`200 OK` for reads)
3. `demo_api_data_retrieved`
4. `strategy_quotes_decided`
5. `quote_risk_evaluated`
6. `execution_plan_reconciled`
7. `demo_api_data_cycle_completed`

For the current demo soak, normal outcomes include either:

- `should_quote=True`, `risk_approved=True`, and matching resting orders, with
  `orders_to_cancel=0` and `orders_to_submit=0`; or
- a safe no-quote decision such as a wide, crossed, or incomplete book, with
  no new orders submitted.

An order-book condition can change naturally. A no-quote decision is not an
error when the bot explains it through its reason field.

## What requires escalation

Escalate promptly if you observe any of the following:

- `Active: failed`, repeated restarts, or no new cycle completion for more
  than two poll intervals.
- `demo_api_data_retrieval_failed`, `demo_lifecycle_recovery_failed`, cleanup
  failure, unhandled exception, or `ExceptionGroup`.
- Repeated HTTP failures, repeated retries, authentication failures, or rate
  limiting that does not recover.
- Unexpected positions, an unexpected balance change, or an order count that
  appears inconsistent with the logged execution plan.
- Any concern that the bot is acting outside its configured demo-only scope.

For an escalation, send the project owner:

1. The local time and timezone.
2. The exact service state.
3. The last successful `demo_api_data_cycle_completed` time and cycle number.
4. The exact error/event text and a small relevant log excerpt.
5. Confirmation that you made no settings, code, service, or order changes.

## Optional live log viewing

Use this only while actively watching the terminal:

```bash
sudo journalctl -u kalshi-bot.service -f -o cat
```

- `-f` means "follow" and continually prints new log entries.
- Press `Ctrl+C` to stop the *viewer only*; it does not stop the bot service.

## Reporting workflow

1. Copy `report-template.md` to `reports/YYYY-MM-DD-your-name-check.md`.
2. Complete the fields using your observations. Summarize logs; never paste
   secrets or a full `.env` file.
3. Create a branch named `monitoring/your-name-YYYY-MM-DD`.
4. Commit only your report and open a pull request.

If you cannot access the demo PC, document the access path attempted, the exact
error, the time, and whether the PC appears powered on. Do not troubleshoot
credentials or network configuration beyond owner-approved steps.
