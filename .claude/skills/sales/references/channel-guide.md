# Channel guide (match buyer + budget)

Pick the cheapest channel that reaches the buyer. Don't spread a small budget
across everything.

## By buyer

| Buyer                         | Best first channels                                  |
|-------------------------------|------------------------------------------------------|
| Local consumer                | Google Business Profile, local SEO, IG/FB local ads  |
| National consumer (visual)    | Instagram, Pinterest, TikTok creative + paid social  |
| Consumer (high intent search) | Google Search ads                                    |
| Small business (B2B)          | Cold email/LinkedIn outreach, referrals, niche groups|
| Mid-market B2B                 | Targeted outreach + retargeting + content            |

## Paid social heuristics (Meta / Instagram via `campaign_create`, ds_id `FA`)

- **Objective**: `OUTCOME_SALES` if there's a checkout/pixel; `OUTCOME_LEADS`
  for a form/booking; `OUTCOME_TRAFFIC` only to learn, not to sell.
- **Budget**: start with a daily budget you'd happily lose for ~5–7 days to
  gather signal. Smaller is fine; under-funding a test wastes more than it saves.
- **Targeting**: start tighter than feels comfortable (geo + 1–2 interests +
  age band). Broaden only once something works.
- **Creatives**: ship 2–3 variations testing different *hooks* (first 3
  seconds / first line), not just colors.
- Everything is created **PAUSED**. The user reviews and launches.

## Google Search heuristics (ds_id `AW`)

- Use when people are actively searching for the solution.
- Tight keyword themes, exact/phrase match, negative keywords from day one.
- Send to a page that matches the search intent, not a generic homepage.

## Creative (Canva / Adobe Express)

- Generate placement-correct sizes: IG feed 4:5, Stories/Reels 9:16,
  Pinterest pin 2:3.
- Lead with the offer and a single clear CTA. One idea per asset.
- These tools output a **file** — they do not post to the platform. Hand the
  asset to the user (or a connected scheduler) to publish.

## Organic / zero-budget

See `small-business-playbook.md` — for many small businesses this outperforms a
thin ad budget.
