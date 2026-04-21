# LinkedIn job search URL (quick reference)

The bot builds search URLs in **`applybot/__main__.py`** → `build_linkedin_jobs_search_url()`.  
Use **`use_url_filters_only = True`** in `config/settings.py` so you do not depend on LinkedIn’s filter UI.

## Parameters the bot sends

| Param | Meaning |
|-------|---------|
| `keywords` | Job title search (URL-encoded) |
| `f_EA=true` | **Easy Apply only** (not `f_AL` — that is “Actively hiring”) |
| `f_WT` | Workplace: `1` on-site, `2` remote, `3` hybrid (comma list URL-encoded) |
| `sortBy` | `DD` = most recent, `R` = most relevant |
| `f_TPR` | Date: `r86400` 24h, `r604800` week, `r2592000` month |
| `f_JT` | Job type: `F` full-time, `P` part-time, `C` contract, … |
| `f_E` | Experience: `1` … `6` (intern → executive) |

LinkedIn may **strip** params it does not recognise and **add** `currentJobId` after redirect. Some account toggles (e.g. “Under 10 applicants”) are **sticky in the UI** and are not reliable via URL alone — the bot can reset some of those once per run when URL-only mode is off.

## Sticky “Under 10 applicants”

If your account turned this **on** in LinkedIn’s UI before, LinkedIn may remember it and shrink results even when the URL does not request it. Toggle it off once in LinkedIn’s filters, or let the bot’s sticky-reset path run when `use_url_filters_only` is false.

---

Implementation details and encoding rules live in the Python function above; this file is the **cheat sheet** only.
