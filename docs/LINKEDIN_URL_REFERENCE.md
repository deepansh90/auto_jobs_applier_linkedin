# LinkedIn Jobs Search URL — Filter Parameter Reference

This is a **verified cheat sheet** for LinkedIn's public job-search URL
(`https://www.linkedin.com/jobs/search/?...`). It is used by
`build_linkedin_jobs_search_url()` in `runAiBot.py`.

Everything below has been cross-checked against:
1. LinkedIn's own UI (which writes these params when you toggle filters).
2. Multiple public third-party scrapers.
3. A reference JS snippet contributed by a user (see bottom of this doc).
4. Runtime logging in our bot (`[DEBUG] current_url_after_load=...`) showing
   which params LinkedIn preserves vs. strips after its redirect.

---

## ✅ Params LinkedIn accepts via URL (bot uses these)

| Param       | Meaning                       | Values                                                                        |
|-------------|-------------------------------|-------------------------------------------------------------------------------|
| `keywords`  | Search text                   | URL-encoded string                                                            |
| `location`  | Location text                 | URL-encoded string (LinkedIn may also redirect to `geoId=…`)                  |
| `f_TPR`     | Date posted                   | `r86400` = past 24 h, `r604800` = past week, `r2592000` = past month          |
| `f_JT`      | Job type                      | `F` Full-time · `P` Part-time · `C` Contract · `T` Temporary · `I` Internship · `V` Volunteer · `O` Other |
| `f_E`       | Experience level              | `1` Internship · `2` Entry · `3` Associate · `4` Mid-Senior · `5` Director · `6` Executive |
| `f_WT`      | Workplace type                | `1` On-site · `2` Remote · `3` Hybrid (comma-separated for multiple)          |
| `f_EA`      | **Easy Apply** only           | `true` (absent = off). **NOTE: `f_AL=true` is "Actively hiring", NOT Easy Apply.** |
| `sortBy`    | Sort order                    | `DD` = Most recent · `R` = Most relevant                                      |
| `f_F`       | In your network               | `true` / `false` — accepted by LinkedIn (preserved on redirect)               |
| `f_C`       | Company IDs                   | Comma-separated numeric LinkedIn company IDs                                  |
| `f_I`       | Industry codes                | Comma-separated numeric                                                       |
| `geoId`     | Numeric location ID           | e.g. `106187582` (India), `103644278` (US), `102713980` (India alt)           |

## ❌ Params LinkedIn does NOT accept via URL (confirmed empirically)

| Filter                    | Why it can't be set via URL                                                      |
|---------------------------|----------------------------------------------------------------------------------|
| **Under 10 applicants**   | Stored as a **sticky per-account preference**. `f_EBP=false` is silently dropped on redirect. Only way to turn it off: click the toggle once in the "All filters" modal; LinkedIn then remembers OFF for the session. |
| Has verifications         | Same story — sticky UI toggle.                                                   |
| Fair Chance Employer (US) | Sticky UI toggle.                                                                |

**Operational consequence for this bot:** if `under_10_applicants=False` in
`config/search.py` but the logged-in LinkedIn account has ever toggled it ON in
the UI, the sticky preference will silently shrink the result set (often to
single-digit results) regardless of URL params. The bot must click the toggle
off once per run in the filters UI.

---

## Contributed reference snippet (JavaScript)

Saved here for cross-reference. The **mappings** it uses (`f_E`, `f_WT`,
`f_JT`, `f_EA`, `f_TPR`) all match LinkedIn's contract and our Python
implementation. It is, however, **not suitable to copy-paste as-is** — see
"Bugs in the snippet" below.

```js
let url = "https://www.linkedin.com/jobs/search/?f_TPR=r86400"

const keyword = $input.first().json.Keyword
const location = $input.first().json.Location
const experienceLevel = $input.first().json['Experience Level']
const remote = $input.first().json.Remote
const jobType = $input.first().json['Job Type']
const easyApply = $input.first().json['Easy Apply']

if (keyword != "") {
  url += `&keywords=${keyword}`;
}

if (location != "") {
  url += `&location=${location}`;
}

if (experienceLevel !== "") {
  // Internship -> 1, Entry level -> 2, Associate -> 3
  // Mid-Senior level -> 4, Director -> 5, Executive -> 6
  const transformedExperiences = experienceLevel
    .split(",")
    .map((exp) => {
      switch (exp.trim()) {
        case "Internship": return "1";
        case "Entry level": return "2";
        case "Associate": return "3";
        case "Mid-Senior level": return "4";
        case "Director": return "5";
        case "Executive": return "6";
        default: return "";
      }
    })
    .filter(Boolean);
  url += `&f_E=${transformedExperiences.join(",")}`;
}

if (remote.length != "") {
  // On-Site -> 1, Remote -> 2, Hybrid -> 3
  const transformedRemote = remote
    .split(",")
    .map((e) => {
      switch (e.trim()) {
        case "Remote": return "2";
        case "Hybrid": return "3";
        case "On-Site": return "1";
        default: return "";
      }
    })
    .filter(Boolean);
  url += `&f_WT=${transformedRemote.join(",")}`;
}

if (jobType != "") {
  // Full-time -> F, Part-time -> P, Contract -> C, etc.
  const transformedJobType = jobType
    .split(",")
    .map((type) => type.trim().charAt(0).toUpperCase());
  url += `&f_JT=${transformedJobType.join(",")}`;
}

if (easyApply != "") {
  url += "&f_EA=true";
}

return {url}
```

### Bugs in the snippet

1. `if (remote.length != "")` compares a number to a string — always truthy. Should be `if (remote !== "")`.
2. `keyword` and `location` are concatenated raw, not `encodeURIComponent`'d. Spaces and `&`/`#` break the URL.
3. `.charAt(0).toUpperCase()` for `f_JT` is lossy: "Temporary"/"Temp" both collapse to `T`, but "Internship"/"Intern" also start with `I`, which is fine, whereas anything else ("Other") produces `O` which LinkedIn does treat as a valid code. Better to use an explicit map like our Python side does.
4. No URL-encoding of comma separators for `f_E`, `f_WT`, `f_JT` — LinkedIn accepts both `1,2,3` and `1%2C2%2C3`, but to be safe we always send the encoded form.
5. Does not handle the sticky "Under 10 applicants" / "Has verifications" / "Fair Chance Employer" toggles — because no public URL param exists for them.

### Our Python implementation (for comparison)

See `build_linkedin_jobs_search_url()` in `runAiBot.py`. It fixes all of the above:
- Uses `urllib.parse.quote_plus` for keyword and comma lists.
- Uses explicit dict maps (`_JOB_TYPE_CODE`, `_EXP_LEVEL_CODE`, `_WORKPLACE_CODE`).
- Only emits `f_EA=true` when `easy_apply_only=True`.
- Post-redirect runtime check that `f_EA=true` survived, logged as `[ERROR]` if stripped.

---

## How LinkedIn's redirect affects URL params (empirical, from our bot logs)

When we send:
```
?keywords=Lead+Engineer&f_WT=1%2C2%2C3&f_EA=true&sortBy=DD&f_TPR=r2592000&f_JT=F&f_EBP=false&f_F=false
```
LinkedIn redirects to (with a logged-in account):
```
?currentJobId=XXX&f_EA=true&f_F=false&f_JT=F&f_TPR=r2592000&f_WT=1%2C2%2C3&keywords=Lead%20Engineer&sortBy=DD
```

- **Preserved:** `f_EA`, `f_F`, `f_JT`, `f_TPR`, `f_WT`, `keywords`, `sortBy`.
- **Added:** `currentJobId` (LinkedIn auto-selects the first job card).
- **Dropped:** `f_EBP=false` (LinkedIn does not recognise this param).

This is the empirical basis for the conclusion that "Under 10 applicants" cannot be set via URL.
