# n8n — Lead Enrich → Score → Outreach → Offer

`lead-enrich-score-outreach.json` is an importable n8n workflow.

**Flow:** Google Sheets trigger → Apollo enrich → Score Lead → Save to Sheet →
`IF intent_score > 70` → (HeyReach outreach → Gumroad email offer). Low-score
leads hit a No-Op. Save-to-Sheet runs for every lead; only outreach + the offer
are gated on the score.

## Import
In n8n: **Workflow menu → Import from File** (or *Import from clipboard*), select
`lead-enrich-score-outreach.json`.

## Placeholders to replace
| Placeholder | Where | What it is |
|---|---|---|
| `YOUR_SHEET_ID` | trigger + Save (2 places) | Google Sheet document ID |
| `Sheet1` | trigger + Save | Tab name, if different |
| `YOUR_HEYREACH_CAMPAIGN_ID` | HeyReach Send (numeric, no quotes) | Target campaign |
| `YOUR_GUMROAD_LINK` | Send Gumroad Offer body | Product link |
| `you@yourdomain.com` | Send Gumroad Offer | From address |

## Credentials to attach (each node shows `REPLACE_ME` until mapped)
- **Google Sheets Trigger** + **Save Enriched Data** → Google Sheets OAuth2.
- **Apollo Enrich** → HTTP Header Auth credential: header `X-Api-Key` = your Apollo key.
- **HeyReach Send** → HTTP Header Auth credential: header `X-API-KEY` = your HeyReach key.
- **Send Gumroad Offer** → SMTP credential.

Secrets live in n8n credentials, not in this JSON. Do not hardcode API keys here.

## Notes
- **Sheet columns:** the sheet needs a header row with `Name, Company, email,
  title, intent_score`. Rows are matched for update on `Name` — switch
  `matchingColumns` to `email` if that is more unique.
- **`intent_score`:** the `Score Lead` node computes a placeholder score from
  Apollo signals (title/seniority, verified email, company size). Replace that
  logic with your real intent source when available.
- **Caveats:** this workflow has not been run against a live n8n instance. The
  HeyReach endpoint/payload (`AddLeadsToCampaignV2`) is a best guess and may need
  adjustment for your HeyReach API version.
