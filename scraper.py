import os
import re
import requests
import time
import random
from google_play_scraper import search, app as gp_app

# ================== CONFIGURATION ==================

# Play Store regions to scan
TARGET_COUNTRIES = ["us", "in"]

# High-risk queries
HIGH_RISK_KEYWORDS = [
    "random video chat", "stranger video chat", "live girls chat",
    "adult video chat", "18+ chat", "roulette video chat",
    "desi video chat", "bhabhi video chat", "dost",
]

# Normal-risk queries
NORMAL_KEYWORDS = [
    "random chat app", "stranger chat", "live video chat",
    "live video call", "dating video chat", "meet new people video chat",
    "cam chat", "cam live chat", "chat", "voice chat", "voice call",
]

# Hard-coded apps that should ALWAYS be blocked
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
    "cc.hitto.otzt.lite", "cn.neoclub.uki", "cn.upuppro.app", "com.ahchat.app",
    "com.baatlive.sgvie", "com.bestsiv.xmiga", "com.bombang.terra", "com.callingme.chat",
    "com.chaloji.link", "com.cherru.video.live.chat", "com.comhub.onlinechat.android.video",
    "com.crroyq.kaya", "com.crroyq.papa", "com.curlytales.android", "com.elive.joy.android",
    "com.esl.matchup", "com.fachat.freechat", "com.gijoy.yah.live",
    "com.google.android.contactkeys", "com.google.android.safetycore", "com.google.ar.core",
    "com.gy.ad.pro", "com.happychat.fita", "com.hoogo.hoogo", "com.hpcnt.vividi",
    "com.huya.nimo", "com.joyreels.video", "com.meeya.app", "com.melot.sktv",
    "com.metokj.meto", "com.mikaapp.android", "com.modocommunity.android",
    "com.polaris.fun", "com.qhqc.starvoice", "com.quyue.ttchat",
    "com.sec.android.easyMover", "com.shujiu.Zaky", "com.sjanmol.koshalisambalpuricalendar",
    "com.ti.live.stream", "com.wakie.android", "com.xv.joychat.india", "com.zen.dodoll",
    "io.chingari.app", "live.hala", "melodytalk.camvideo.live", "org.dico.dream.android",
    "sg.bigo.hellotalk", "xyz.chefdice.boldhub", "xyz.copiee.android"
]

# Apps that should NEVER be blocked
SAFE_WHITELIST = {
    "com.whatsapp", "com.whatsapp.w4b", "org.telegram.messenger",
    "com.facebook.orca", "com.snapchat.android", "com.instagram.android",
    "com.twitter.android", "com.discord", "com.skype.raider",
    "com.viber.voip", "jp.naver.line.android", "com.kakao.talk",
    "com.signal.messenger", "com.linkedin.android",
    "com.jiochat.jiochatapp", "com.turkcell.bip", "com.nandbox.nandbox",
    "us.zoom.videomeetings", "com.google.android.apps.meetings",
    "com.microsoft.teams", "com.slack", "com.cisco.webex.meetings",
    "com.google.android.talk", "com.google.android.gm", "com.google.android.youtube",
    "in.startv.hotstar", "com.jio.jioplay.tv", "com.graymatrix.did",
    "com.tinder", "com.bumble.app", "co.hinge.app", "com.okcupid.okcupid",
    "com.badoo.mobile", "com.eharmony", "com.ftw_and_co.happn",
    "com.pof.android", "net.lovoo.android", "ru.loveplanet.app",
    "ru.mamba.client", "ru.fotostrana.sweetmeet", "com.taggedapp",
    "tv.twitch.android.app", "com.google.android.contactkeys", "com.google.ar.core" 
}

# Text patterns that indicate "risky" / junky apps
RISKY_PHRASES = [
    r"\brandom\b", r"\bstranger(s)?\b", r"\bvideo chat\b",
    r"\bvideo call\b", r"\blive chat\b", r"\blive video\b",
    r"\bmeet (new )?people\b", r"\bgirls chat\b", r"\badult chat\b",
    r"\b18\+\b", r"\bdating\b", r"\bflirt\b", r"\bcam chat\b",
    r"\broulette\b", r"\bdesi\b", r"\bbhabhi\b",
]

SAFE_CONTEXT_WORDS = [
    "business", "team", "workspace", "meeting", "office", "education",
    "classroom", "teacher", "editor", "downloader", "wallpaper",
    "cricket", "news",
]

APPBRAIN_URL = "https://www.appbrain.com/apps/trending/social"
PKG_ID_RE = re.compile(r"^[a-zA-Z0-9_]+\.[a-zA-Z0-9_.]+$")


# ================== HELPERS ==================

def is_valid_package_name(pkg_id: str) -> bool:
    if not pkg_id: return False
    return PKG_ID_RE.match(pkg_id) is not None

def looks_risky(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    for w in SAFE_CONTEXT_WORDS:
        if w in text: return False
    for pattern in RISKY_PHRASES:
        if re.search(pattern, text): return True
    return False

def load_existing_blocklist(path: str = "blocklist.txt") -> set:
    existing = set()
    if not os.path.exists(path): return existing
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if is_valid_package_name(line): existing.add(line)
    return existing

def fetch_app_details_robust(pkg_id: str):
    # Try fetching details. If it fails in one region, try others.
    for country in TARGET_COUNTRIES:
        try:
            return gp_app(pkg_id, lang="en", country=country)
        except Exception:
            continue
    return None

def fetch_appbrain_candidates() -> set:
    pkgs = set()
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        print("[+] Fetching AppBrain...")
        resp = requests.get(APPBRAIN_URL, headers=headers, timeout=15)
        if resp.status_code == 200:
            matches = re.findall(r"/app/[^/]+/([a-zA-Z0-9_\.]+)", resp.text)
            for pkg in matches:
                if is_valid_package_name(pkg): pkgs.add(pkg)
            print(f"    AppBrain candidates found: {len(pkgs)}")
    except Exception as e:
        print(f"    AppBrain Error: {e}")
    return pkgs

def spider_crawl(seed_pkg: str, current_blocklist: set) -> set:
    """
    The 'Trash Spider' strategy:
    1. Find 'Similar Apps' for the seed (via details['similarApps']).
    2. Find apps by the same Developer.
    3. Check if they look risky.
    """
    new_finds = set()
    try:
        # Fetch details (this returns a dict which often includes 'similarApps')
        details = fetch_app_details_robust(seed_pkg)
        if not details: return new_finds

        developer_id = details.get('developerId')
        
        # 1. Developer Cluster Search
        if developer_id:
            try:
                # Search using pub:DeveloperName or just developerId
                # Note: google-play-scraper search handles "pub:" automatically or implies it
                dev_results = search(f"pub:{developer_id}", lang="en", country="us")
                for app in dev_results:
                    pkg = app.get("appId")
                    if pkg and pkg not in current_blocklist and pkg not in SAFE_WHITELIST:
                        if looks_risky(app.get("title", ""), app.get("summary", "")):
                            print(f"    [SPIDER-DEV] Found clone by same dev: {pkg}")
                            new_finds.add(pkg)
            except:
                pass

        # 2. Similar Apps (Using the list returned in details)
        # google-play-scraper details often has a 'similarApps' key which is a list of IDs or URLs
        similar_list = details.get('similarApps', [])
        for sim_app_data in similar_list:
            # It might be a dict or a string depending on version, 
            # usually it's a dict with 'appId' if detailed, or just check format.
            pkg = None
            if isinstance(sim_app_data, dict):
                pkg = sim_app_data.get('appId')
            elif isinstance(sim_app_data, str):
                # Sometimes it returns full URLs, extract ID
                if "id=" in sim_app_data:
                    pkg = sim_app_data.split("id=")[-1].split("&")[0]
                else:
                    pkg = sim_app_data # Assume it's the ID
            
            if pkg and pkg not in current_blocklist and pkg not in SAFE_WHITELIST:
                # We need to quickly verify if it's risky. 
                # We can't fetch details for ALL similar apps (too slow), 
                # but we can assume if it's in "Similar" to a blocked app, it's suspect.
                # Let's fetch basic details to check keywords.
                try:
                    sim_details = fetch_app_details_robust(pkg)
                    if sim_details and looks_risky(sim_details.get("title", ""), sim_details.get("summary", "")):
                        print(f"    [SPIDER-SIM] Found similar trash app: {pkg}")
                        new_finds.add(pkg)
                except:
                    pass

    except Exception:
        pass
    
    return new_finds

# ================== MAIN ==================

def main():
    previous_blocklist = load_existing_blocklist()
    final_blocklist = set(previous_blocklist)
    final_blocklist.update(ALWAYS_BLOCK)

    print(f"[+] Loaded {len(previous_blocklist)} existing apps.")
    print(f"[+] After ALWAYS_BLOCK merge: {len(final_blocklist)} apps.")

    # -------- 1. Google Play Search Scanning --------
    for country in TARGET_COUNTRIES:
        print(f"\n--- Scanning Region: {country.upper()} ---")
        
        all_keywords = list(zip(HIGH_RISK_KEYWORDS, [100]*len(HIGH_RISK_KEYWORDS))) + \
                       list(zip(NORMAL_KEYWORDS, [60]*len(NORMAL_KEYWORDS)))

        for query, n_hits in all_keywords:
            print(f"Searching: '{query}' in {country.upper()}")
            try:
                time.sleep(random.uniform(1, 3))
                results = search(query, lang="en", country=country, n_hits=n_hits)

                for app in results:
                    pkg = app.get("appId")
                    if not pkg or not is_valid_package_name(pkg): continue
                    if pkg in SAFE_WHITELIST or pkg in final_blocklist: continue

                    if looks_risky(app.get("title", ""), app.get("summary", "")):
                        print(f"    [BLOCK] {pkg} ({app.get('title')})")
                        final_blocklist.add(pkg)

            except Exception as e:
                print(f"    Error searching '{query}': {e}")

    # -------- 2. AppBrain Candidate Validation --------
    candidates = fetch_appbrain_candidates()
    print("\n--- Validating AppBrain Candidates ---")
    for pkg in candidates:
        if pkg in final_blocklist or pkg in SAFE_WHITELIST: continue
        try:
            info = fetch_app_details_robust(pkg)
            if not info: continue
            if looks_risky(info.get("title", ""), info.get("summary", "")):
                print(f"    [AppBrain BLOCK] {pkg}")
                final_blocklist.add(pkg)
        except: continue

    # -------- 3. Trash Spider Strategy --------
    print("\n--- Running Trash Spider (Recursion) ---")
    spider_seeds = list(ALWAYS_BLOCK)
    # Add some randoms from the final blocklist to spider too
    if len(final_blocklist) > 20:
        spider_seeds.extend(random.sample(list(final_blocklist), 20))
    else:
        spider_seeds.extend(list(final_blocklist))
    
    # Dedup seeds
    spider_seeds = list(set(spider_seeds))

    print(f"Spidering {len(spider_seeds)} seed apps for clones...")
    
    spider_new_finds = set()
    for i, seed_pkg in enumerate(spider_seeds):
        if i % 5 == 0: print(f"Spider progress: {i}/{len(spider_seeds)}")
        
        # Be gentle with the API
        time.sleep(random.uniform(0.5, 1.5))
        
        found = spider_crawl(seed_pkg, final_blocklist)
        spider_new_finds.update(found)
        final_blocklist.update(found)

    print(f"[+] Spider found {len(spider_new_finds)} extra apps.")

    # -------- 4. Apply whitelist and save --------
    before_whitelist = len(final_blocklist)
    final_blocklist.difference_update(SAFE_WHITELIST)
    
    print(f"[+] Writing blocklist.txt with {len(final_blocklist)} apps.")
    with open("blocklist.txt", "w") as f:
        f.write("# Auto-generated Blocklist\n")
        for pkg in sorted(final_blocklist):
            f.write(f"{pkg}\n")

if __name__ == "__main__":
    main()
