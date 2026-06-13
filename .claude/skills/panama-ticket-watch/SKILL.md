---
name: panama-ticket-watch
description: >-
  Check ticket prices for the 2026 FIFA World Cup Group L match Panama vs.
  England at MetLife Stadium (East Rutherford, NJ), Sat June 27, 2026, 5:00 PM
  ET. Sweeps the major ticket marketplaces, finds the lowest get-in price per
  seating tier, compares against the running price log to surface the best deal
  seen so far, and records the result. Use whenever the user wants to check,
  monitor, or track tickets/prices for the Panama (vs England) World Cup game in
  New Jersey / MetLife — including recurring "every 3 hours" / daily checks.
---

# Panama vs. England — World Cup Ticket Watch

## The match (fixed facts — do not re-derive)

| Field | Value |
|-------|-------|
| Match | Panama vs. England — Match 67, Group L |
| Tournament | 2026 FIFA World Cup |
| Venue | MetLife Stadium, East Rutherford, New Jersey |
| Date / kickoff | Saturday, June 27, 2026 — 5:00 PM ET |

## What this skill does, every time it runs

1. **Sweep the marketplaces** (links in `references/marketplaces.md`). For each
   one, fetch the event page and pull:
   - the **lowest "get-in" price** (cheapest ticket available), and
   - if visible, the lowest price per seating tier (upper / mid / lower /
     premium-hospitality), and the **all-in price** (incl. fees) when shown.
   Use `WebSearch` for a fast price scan, then `WebFetch` on the specific
   marketplace event URLs to confirm a live number and note any fee disclosure.
2. **Normalize** every quote to *price per ticket, fees included where known*.
   Flag any quote that is face-value/pre-fee so it isn't compared unfairly
   against an all-in quote.
3. **Find the best current deal** — lowest normalized price across all sources,
   noting source, seating area, and quantity/together availability.
4. **Compare to history** — read `references/price-log.md`, state whether the
   current best is the lowest seen so far, and by how much it moved since the
   last check.
5. **Append a new row** to `references/price-log.md` (see format below).
6. **Report** a short summary: best deal now, where, how it compares to prior
   checks, and a recommendation (buy / wait) with one line of reasoning.

## Important guardrails

- **Prices are dynamic and these are mostly resale marketplaces.** Always state
  the timestamp of the check and that prices move. Never present a logged price
  as still-live without re-checking.
- **Always include FIFA's official resale** (`fifa.com/tickets`) in the sweep —
  it is the only source with face-value (non-marked-up) resale and is the
  safest channel. Call it out separately from third-party resellers.
- **Watch for fees.** A "from $X" headline often excludes service fees that can
  add 15–30%. Prefer all-in numbers; label when you couldn't get one.
- **Don't buy anything.** This skill only researches and reports. Purchasing is
  the user's decision — surface the link, don't transact.
- If a marketplace page can't be fetched (auth wall, bot block), note it as
  "unavailable this check" rather than dropping it silently.

## price-log.md row format

Append one row per check (newest at the bottom):

```
| 2026-06-13 16:05 ET | $815 | TickPick | Upper corner (300s) | from-price, +fees est. | — |
```

Columns: `datetime ET | best normalized price | source | seating area | notes (fees/quantity) | Δ vs previous check`.

## Running this on a schedule (every 3 hours / daily)

A skill does not run itself — something has to invoke it on a timer:

- **While a Claude Code session is open:** use the `/loop` skill, e.g.
  `/loop 3h /panama-ticket-watch`. It re-runs on the interval until the session
  ends. Note: this **stops when the session/container closes**, which in the
  cloud/web environment happens after inactivity — so it is not truly unattended.
- **For truly unattended 24/7 polling:** run it from a machine that stays on,
  via cron, e.g. every 3 hours:
  `0 */3 * * * claude -p "/panama-ticket-watch" >> ~/panama-watch.log 2>&1`
  (Wire up notifications — email/Slack/text — in that cron wrapper if you want
  to be alerted only when a new low is hit.)
- Either way, the `price-log.md` file is the durable record of every check, so
  "best deal so far" survives across runs.

Stop checking once the user has bought tickets or after kickoff (June 27, 2026).
