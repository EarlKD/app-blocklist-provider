import os
import re
import requests
import time
import random
from google_play_scraper import search, app as gp_app

# ================== CONFIGURATION ==================

# Play Store regions to scan
TARGET_COUNTRIES = ["us", "in"]

# High-risk queries: we scan deeper (n_hits = 100)
HIGH_RISK_KEYWORDS = [
    "random video chat",
    "stranger video chat",
    "live girls chat",
    "adult video chat",
    "18+ chat",
    "roulette video chat",
    "desi video chat",
    "bhabhi video chat",
]

# Normal-risk queries: decent depth (n_hits = 60)
NORMAL_KEYWORDS = [
    "random chat app",
    "stranger chat",
    "live video chat",
    "live video call",
    "dating video chat",
    "meet new people video chat",
    "cam chat",
    "cam live chat",
]

# Hard-coded apps that should ALWAYS be blocked (even if keywords/heuristics change)
ALWAYS_BLOCK = [
    "com.sgiggle.production", "com.azarlive.android", "com.hkfuliao.chamet",
    "com.videochat.livu", "sg.bigo.live", "com.mumu.videochat",
    "com.mumu.videochat.india", "com.live.streamer.online.app.video",
    "ly.omegle.android", "cool.monkey.android", "vixr.bermuda",
    "com.tumile.videochat", "com.exutech.chacha", "omegle.tv",
    "co.yellw.yellowapp", "com.chatous.chatous", "camsurf.com",
    "com.chatrandom", "com.unearby.sayhi", "com.skout.android",
    "com.myyearbook.m", "com.parau.videochat", "com.hay.android",
    "com.mico.world", "com.comhub.onlinechat.android.video",
    "land.lifeoasis.maum", "com.live.soulchill",
]

# Apps that should NEVER be blocked (even if keywords look risky)
SAFE_WHITELIST = {
    # General messengers / social
    "com.whatsapp", "com.whatsapp.w4b", "org.telegram.messenger",
    "com.facebook.orca", "com.snapchat.android", "com.instagram.android",
    "com.twitter.android", "com.discord", "com.skype.raider",
    "com.viber.voip", "jp.naver.line.android", "com.kakao.talk",
    "com.signal.messenger", "com.linkedin.android",
    "com.jiochat.jiochatapp",   # JioChat
    "com.turkcell.bip",         # BiP messenger
    "com.nandbox.nandbox",      # nandbox messenger

    # Video meeting / work apps
    "us.zoom.videomeetings",
    "com.google.android.apps.meetings",
    "com.microsoft.teams", "com.slack",
    "com.cisco.webex.meetings",
    "com.google.android.talk",

    # Google & media
    "com.google.android.gm", "com.google.android.youtube",

    # OTT / Indian TV apps
    "in.startv.hotstar", "com.jio.jioplay.tv", "com.graymatrix.did",

    # Mainstream dating (similar policy level as Tinder/Bumble)
    "com.tinder", "com.bumble.app", "co.hinge.app", "com.okcupid.okcupid",
    "com.badoo.mobile", "com.eharmony", "com.ftw_and_co.happn",
    "com.pof.android", "net.lovoo.android", "ru.loveplanet.app",
    "ru.mamba.client", "ru.fotostrana.sweetmeet",

    # Community / meet-people type
    "com.taggedapp",

    # Streaming / general social
    "tv.twitch.android.app",
}

# Text patterns that indicate "risky" / junky apps
RISKY_PHRASES = [
    r"\brandom\b", r"\bstranger(s)?\b", r"\bvideo chat\b",
    r"\bvideo call\b", r"\blive chat\b", r"\blive video\b",
    r"\bmeet (new )?people\b", r"\bgirls chat\b", r"\badult chat\b",
    r"\b18\+\b", r"\bdating\b", r"\bflirt\b", r"\bcam chat\b",
    r"\broulette\b", r"\bdesi\b", r"\bbhabhi\b",
]

# Words that strongly suggest the app is harmless (work, edu, media, utility)
SAFE_CONTEXT_WORDS = [
    "business", "team", "workspace", "meeting", "office", "education",
    "classroom", "teacher", "editor", "downloader", "wallpaper",
    "cricket", "news",
]

# Secondary source of candidates
APPBRAIN_URL = "https://www.appbrain.com/apps/trending/social"


# ================== HELPERS ==================

def looks_risky(title: str, summary: str) -> bool:
    """
    True if an app *looks* like random/stranger/adult video chat
    based on title + summary text.
    """
    text = f"{title} {summary}".lower()

    # First, try to rule out obviously safe context
    for w in SAFE_CONTEXT_WORDS:
        if w in text:
            return False

    # Then look for risky patterns
    for pattern in RISKY_PHRASES:
        if re.search(pattern, text):
            return True

    return False


def load_existing_blocklist(path: str = "blocklist.txt") -> set:
    """
    Load existing blocklist.txt into a set (ignores comments and blanks).
    """
    existing = set()
    if not os.path.exists(path):
        return existing

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                existing.add(line)
    return existing


def fetch_app_details_robust(pkg_id: str):
    """
    Try to fetch app details from multiple Play Store regions.
    """
    for country in TARGET_COUNTRIES:
        try:
            return gp_app(pkg_id, lang="en", country=country)
        except Exception:
            continue
    return None


def fetch_appbrain_candidates() -> set:
    """
    Scrape AppBrain trending social page for package IDs.
    """
    pkgs = set()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    try:
        print("[+] Fetching AppBrain...")
        resp = requests.get(APPBRAIN_URL, headers=headers, timeout=15)
        if resp.status_code == 200:
            matches = re.findall(r"/app/[^/]+/([a-zA-Z0-9_\.]+)", resp.text)
            pkgs.update(matches)
            print(f"    AppBrain candidates found: {len(pkgs)}")
        else:
            print(f"    AppBrain Status: {resp.status_code}")
    except Exception as e:
        print(f"    AppBrain Error: {e}")
    return pkgs


# ================== MAIN ==================

def main():
    # Load previous results + always-block baseline
    final_blocklist = load_existing_blocklist()
    final_blocklist.update(ALWAYS_BLOCK)

    initial_count = len(final_blocklist)
    print(f"[+] Loaded {initial_count} existing apps (including ALWAYS_BLOCK).")

    # -------- 1. Google Play Search Scanning --------
    for country in TARGET_COUNTRIES:
        print(f"\n--- Scanning Region: {country.upper()} ---")

        # High-risk keywords (deeper scan: n_hits = 100)
        for query in HIGH_RISK_KEYWORDS:
            print(f"Searching (HIGH): '{query}' in {country.upper()}")
            try:
                time.sleep(random.uniform(2, 4))  # be gentle with Play Store
                results = search(query, lang="en", country=country, n_hits=100)

                for app in results:
                    pkg = app.get("appId")
                    if not pkg:
                        continue

                    if pkg in SAFE_WHITELIST or pkg in final_blocklist:
                        continue

                    title = app.get("title", "") or ""
                    summary = app.get("summary", "") or ""

                    if looks_risky(title, summary):
                        print(f"    [BLOCK] {pkg} ({title})")
                        final_blocklist.add(pkg)

            except Exception as e:
                print(f"    Error while searching (HIGH) '{query}' in {country}: {e}")

        # Normal keywords (shallower scan: n_hits = 60)
        for query in NORMAL_KEYWORDS:
            print(f"Searching (NORMAL): '{query}' in {country.upper()}")
            try:
                time.sleep(random.uniform(2, 4))
                results = search(query, lang="en", country=country, n_hits=60)

                for app in results:
                    pkg = app.get("appId")
                    if not pkg:
                        continue

                    if pkg in SAFE_WHITELIST or pkg in final_blocklist:
                        continue

                    title = app.get("title", "") or ""
                    summary = app.get("summary", "") or ""

                    if looks_risky(title, summary):
                        print(f"    [BLOCK] {pkg} ({title})")
                        final_blocklist.add(pkg)

            except Exception as e:
                print(f"    Error while searching (NORMAL) '{query}' in {country}: {e}")

    # -------- 2. AppBrain Candidate Validation --------
    candidates = fetch_appbrain_candidates()
    print("\n--- Validating AppBrain Candidates ---")
    for pkg in candidates:
        if pkg in final_blocklist or pkg in SAFE_WHITELIST:
            continue

        try:
            time.sleep(random.uniform(1, 2))  # per-app delay
            info = fetch_app_details_robust(pkg)
            if not info:
                continue

            title = info.get("title", "") or ""
            summary = (
                info.get("summary")
                or info.get("description")
                or ""
            )

            if looks_risky(title, summary):
                print(f"    [AppBrain BLOCK] {pkg} ({title})")
                final_blocklist.add(pkg)

        except Exception:
            # App might not exist in US/IN store or scraper failed; skip quietly
            continue

    # -------- 3. Save Updated Blocklist --------
    if len(final_blocklist) > initial_count:
        added = len(final_blocklist) - initial_count
        print(f"\n[+] Saving blocklist.txt with {len(final_blocklist)} apps "
              f"(+{added} new).")
        with open("blocklist.txt", "w") as f:
            f.write("# Auto-generated Blocklist\n")
            for pkg in sorted(final_blocklist):
                f.write(f"{pkg}\n")
    else:
        print("\n[+] No new apps found. blocklist.txt unchanged.")


if __name__ == "__main__":
    main()
