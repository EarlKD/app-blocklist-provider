# app-blocklist-provider
# Android Junk Video Chat Blocklist (Experimental)

⚠️ **Status: Highly Experimental / Use at Your Own Risk**  
This project tries to **auto-generate a package-name blocklist** of:

- random video chat apps  
- stranger chat / roulette-style apps  
- adult-ish or low-quality social live video apps

It does this by scraping **Google Play search results** and the **AppBrain Trending Social** list, then applying some simple text-based rules.

Because this is all heuristic and automated, **the blocklist will absolutely contain mistakes**:

- Some apps that *should* be blocked may be missed (**false negatives**).
- Some apps that *should NOT* be blocked may be included (**false positives**).

This repo is meant as a personal experiment / helper, **not a polished or trustworthy security product**.

---

## How It Works (High Level)

The `scraper.py` script:

1. Loads an existing `blocklist.txt` (if present).
2. Adds a hard-coded list of known bad apps (`ALWAYS_BLOCK`).
3. Searches Google Play for a set of **high-risk** and **normal** keywords in multiple regions:
   - Currently: **US (`us`)** and **India (`in`)**.
4. For each search result:
   - Skips anything in a **whitelist** (`SAFE_WHITELIST`) of known good apps (WhatsApp, Meet, Zoom, Jio apps, etc.).
   - Reads the app’s `title` and `summary`.
   - Runs a simple **heuristic**: if the text looks like random/stranger/video chat / adult / roulette content and does *not* look like work/education/media, it gets added to the blocklist.
5. Scrapes **AppBrain’s "Trending Social"** page for extra candidate package IDs, and then:
   - For each candidate, tries to fetch its Play Store details from `us` or `in`.
   - Runs the same heuristic and adds suspicious apps to the blocklist.
6. If **any new apps** were added, it rewrites `blocklist.txt` with the updated set.

Over time, as this runs on a schedule (e.g. via GitHub Actions), the blocklist will grow as new junky apps appear in search/trending.

---

## Important Files

- `scraper.py`  
  Main script that generates/updates `blocklist.txt`.

- `blocklist.txt`  
  The auto-generated list of **package names**.  
  This is what you’d consume on your device/OS side.

- `.github/workflows/updater.yml`  
  GitHub Actions workflow (if present) that runs `scraper.py` on a schedule and commits updated `blocklist.txt` back into the repo.

---

## Why "Experimental"?

A few reasons:

- The detection is **heuristic**, based on keywords like `"random"`, `"stranger"`, `"video chat"`, `"18+"`, `"desi"`, `"bhabhi"`, etc., and **context words** like `"business"`, `"classroom"`, `"news"`, etc.
- App descriptions change over time. An app that looked innocent yesterday might later become spammy (or vice versa).
- The script doesn’t really “understand” the app; it just pattern-matches on text.
- Some apps are **general social / dating / community** platforms that may or may not match *your* definition of “junk”.

Because of this, **manual review is strongly recommended** before you enforce the blocklist aggressively (for example, at the OS level).

---

## False Positives & False Negatives

- **False Positives** (good apps that get blocked):  
  These can appear if:
  - The app’s marketing text tries to sound “fun” or “flirty”.
  - The app’s description contains risky keywords (like “random chat”) but is actually used in a harmless context.
  
  If you find such an app:
  - Add its package name to `SAFE_WHITELIST` in `scraper.py`.
  - Remove it from `blocklist.txt` once.  
  Future runs will skip it because whitelist takes priority.

- **False Negatives** (bad apps missed):  
  These happen if:
  - The app uses very generic or vague descriptions.
  - It doesn’t show up in the keywords we search.
  - It hasn’t hit trending / social lists yet.

  If you spot one:
  - Add its package name to `ALWAYS_BLOCK` in `scraper.py`.
  - Run the script; it will be permanently included going forward.

---

## How to Run Locally

### 1. Requirements

- Python 3.8+ recommended
- Pip packages:
  - `google-play-scraper`
  - `requests`

Install dependencies:

```bash
pip install google-play-scraper requests
