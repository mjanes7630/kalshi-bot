# Demo Soak Monitoring Report

> Copy this file to `docs/developer-monitoring/reports/YYYY-MM-DD-your-name-check.md`.
> Replace every bracketed placeholder. Do not commit secrets, `.env` content,
> private-key paths, passwords, API IDs, or remote-access details.

## Check details

- **Monitor:** [name]
- **Date and local time:** [YYYY-MM-DD, HH:MM, timezone]
- **Check type:** [routine / follow-up / incident]
- **Access method:** [approved method only; do not include credentials or IP]

## Service status

- **Observed state:** [active (running) / failed / inactive / other]
- **Service start time / uptime:** [value from `systemctl status`]
- **Main PID:** [value, if available]
- **Restarting observed:** [no / yes — describe]

## Lifecycle health

- **Last successful cycle:** [timestamp and cycle number]
- **API result summary:** [for example: all observed reads were 200 OK]
- **Strategy/risk result:** [for example: quote approved; two matching resting quotes retained]
- **Orders / positions / balance observation:** [summary only; no IDs or secrets]
- **Errors, retries, or warnings:** [none observed / details]

## Relevant log excerpt

Paste only the smallest non-sensitive excerpt needed to support the report.

```text
[Paste non-sensitive lines here, or write "None needed; routine healthy check."]
```

## Action and escalation

- **Action taken:** [none — read-only monitoring / described owner-approved action]
- **Owner notified:** [no / yes — time and communication channel]
- **Reason for escalation, if any:** [not applicable / details]
- **Confirmation:** I did not change settings, code, service configuration,
  credentials, or orders. [yes]

## Next recommended check

[date/time or condition]
