import os
import re
import requests
import time
import random
from google_play_scraper import search, app as gp_app

# ================== CONFIGURATION ==================

TARGET_COUNTRIES = ["us", "in"]

SEARCH_KEYWORDS = [
    "random video chat", "random chat app", "stranger video chat",
    "stranger chat", "live video chat", "live video call",
    "live girls chat", "adult video chat", "18+ chat",
    "dating video chat", "meet new people video chat",
    "cam chat", "cam live chat", "roulette video chat",
    "desi video chat", "bhabhi video chat"
]

ALWAYS_BLOCK = [
    "com.sgiggle.production", "com.azarlive.android", "com.hkfuliao.chamet",
    "com.videochat.livu", "sg.bigo.live", "com.mumu.videochat",
    "com.mumu.videochat.india", "com.live.streamer.online.app.video",
    "ly.omegle.android", "cool.monkey.android", "vixr.bermuda",
    "com.tumile.videochat", "com.exutech.chacha", "omegle.tv",
    "co.yellw.yellowapp", "com.chatous.chatous", "camsurf.com",
    "com.chatrandom", "com.unearby.sayhi", "com.skout.android",
    "com.myyearbook.m", "com.parau.videochat", "com.hay.android",
    "com.mico.world"
]

SAFE_WHITELIST = {
    "com.whatsapp", "com.whatsapp.w4b", "org.telegram.messenger",
    "com.facebook.orca", "com.snapchat.android", "com.instagram.android",
    "com.twitter.android", "com.discord", "com.skype.raider",
    "com.viber.voip", "jp.naver.line.android", "com.kakao.talk",
    "com.signal.messenger", "us.zoom.videomeetings",
    "com.google.android.apps.meetings", "com.microsoft.teams", "com.slack",
    "com.cisco.webex.meetings", "com.google.android.talk",
    "com.google.android.gm", "com.google.android.youtube",
    "com.tinder", "com.bumble.app", "co.hinge.app", "com.okcupid.okcupid",
    "tv.twitch.android.app", "com.linkedin.android", 
    "in.startv.hotstar", "com.jio.jioplay.tv", "com.graymatrix.did"
}

RISKY_PHRASES = [
    r"\brandom\b", r"\bstranger(s)?\b", r"\bvideo chat\b",
    r"\bvideo call\b", r"\blive chat\b", r"\blive video\b",
    r"\bmeet (new )?people\b", r"\bgirls chat\b", r"\badult chat\b",
    r"\b18\+\b", r"\bdating\b", r"\bflirt\b", r"\bcam chat\b",
    r"\broulette\b", r"\bdesi\b", r"\bbhabhi\b"
]

SAFE_CONTEXT_WORDS = [
    "business", "team", "workspace", "meeting", "office", "education",
    "classroom", "teacher", "editor", "downloader", "wallpaper", "cricket", "news"
]

APPBRAIN_URL = "https://www.appbrain.com/apps/trending/social"

# ================== HELPERS ==================

def looks_risky(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    for w in SAFE_CONTEXT_WORDS:
        if w in text: return False
    for pattern in RISKY_PHRASES:
        if re.search(pattern, text): return True
    return False

def load_existing_blocklist(path="blocklist.txt"):
    existing = set()
    if not os.path.exists(path):
        return existing
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                existing.add(line)
    return existing

def fetch_app_details_robust(pkg_id):
    for country in TARGET_COUNTRIES:
        try:
            return gp_app(pkg_id, lang="en", country=country)
        except:
            continue
    return None

def fetch_appbrain_candidates():
    pkgs = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        print(f"[+] Fetching AppBrain...")
        resp = requests.get(APPBRAIN_URL, headers=headers, timeout=15)
        if resp.status_code == 200:
            matches = re.findall(r"/app/[^/]+/([a-zA-Z0-9_\.]+)", resp.text)
            pkgs.update(matches)
        else:
            print(f"    AppBrain Status: {resp.status_code}")
    except Exception as e:
        print(f"    AppBrain Error: {e}")
    return pkgs

# ================== MAIN ==================

def main():
    final_blocklist = load_existing_blocklist()
    final_blocklist.update(ALWAYS_BLOCK)
    initial_count = len(final_blocklist)
    print(f"[+] Loaded {initial_count} existing apps.")

    for country in TARGET_COUNTRIES:
        print(f"--- Scanning Region: {country.upper()} ---")
        for query in SEARCH_KEYWORDS:
            print(f"Searching: '{query}' in {country.upper()}")
            try:
                time.sleep(random.uniform(2, 4)) 
                results = search(query, lang="en", country=country, n_hits=50)
                for app in results:
                    pkg = app.get("appId")
                    if pkg in SAFE_WHITELIST or pkg in final_blocklist: continue
                    if looks_risky(app.get("title", ""), app.get("summary", "")):
                        print(f"    [BLOCK] {pkg}")
                        final_blocklist.add(pkg)
            except Exception as e:
                print(f"    Error: {e}")

    candidates = fetch_appbrain_candidates()
    print(f"--- Validating AppBrain Candidates ---")
    for pkg in candidates:
        if pkg in final_blocklist or pkg in SAFE_WHITELIST: continue
        try:
            time.sleep(random.uniform(1, 2))
            info = fetch_app_details_robust(pkg)
            if info and looks_risky(info.get("title", ""), info.get("summary", "")):
                 print(f"    [AppBrain BLOCK] {pkg}")
                 final_blocklist.add(pkg)
        except:
            pass 

    if len(final_blocklist) > initial_count:
        print(f"[+] Saving {len(final_blocklist)} apps.")
        with open("blocklist.txt", "w") as f:
            f.write("# Auto-generated Blocklist\n")
            for pkg in sorted(final_blocklist):
                f.write(f"{pkg}\n")
    else:
        print("[+] No new apps found.")

if __name__ == "__main__":
    main()
