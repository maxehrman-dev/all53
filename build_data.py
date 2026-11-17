#!/usr/bin/env python3
"""THE 53 roster builder.

Inputs
  teams_orig.json          the hand-built game data (franchise lists, curated fame tiers, fan favorites)
  nfl/roster_YYYY.csv      nflverse season rosters, 1920 to now
  nfl/draft_picks.csv      nflverse draft picks (Pro Bowls, All-Pro, Hall of Fame, approximate value)

Output
  rosters.js               `var TEAMS=[...]` for the game. Every player entry is
                           "Name|POS|rarity|alias~alias", rarity 1 (household name) to 99 (deepest cut),
                           ranked within that team's pool from real career data.

Refresh rosters any week:  download the new nflverse roster CSV, rerun this script, rebuild the page.
"""
import csv, glob, json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
NFL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "nfl")
CUR_SEASON = max(int(re.findall(r"\d{4}", os.path.basename(f))[0]) for f in glob.glob(os.path.join(NFL, "roster_*.csv")))

import unicodedata

def norm(s):
    """Match key. Accents, apostrophes, quotes, periods, hyphens and suffixes never matter.
    Mirrored exactly by norm() in the game."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r'"[^"]*"', " ", s)
    s = re.sub(r"['‘’ʻ`]", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", " ", s)
    return " ".join(s.split())

def clean_display(n):
    n = re.sub(r",\s*(Jr|Sr)\.?", r" \1.", n)
    return " ".join(n.split())

def nick_aliases(n):
    """'Ed "Too Tall" Jones' -> also accept 'Too Tall Jones'."""
    m = re.match(r'^(.*?)"([^"]+)"(.*)$', n)
    if not m:
        return set()
    return {(m.group(2) + " " + m.group(3).strip()).strip()}

JUNK = re.compile(r"(?i)^lists? of\b|\bplayers$")

# Nickname families. Mirrored in the game so typed guesses resolve the same way.
NICK_GROUPS = [
    "robert bob bobby rob robbie bert", "william bill billy will willie", "james jim jimmy jamie",
    "michael mike mikey", "thomas tom tommy", "richard dick rick ricky rich richie", "charles chuck charlie",
    "joseph joe joey", "daniel dan danny", "david dave davey", "edward ed eddie ted", "kenneth ken kenny",
    "lawrence larry", "ronald ron ronnie", "anthony tony", "steven steve stephen stevie",
    "christopher chris", "matthew matt", "nicholas nick nicky", "patrick pat", "samuel sam sammy",
    "timothy tim timmy", "andrew andy drew", "alexander alex", "gregory greg", "gerald jerry jerome",
    "donald don donnie", "frederick fred freddie", "henry hank", "john jack johnny jon", "jeffrey jeff",
    "raymond ray", "benjamin ben benny", "douglas doug", "eugene gene", "walter walt", "albert al",
    "joshua josh", "jacob jake", "zachary zach zack", "jonathan jon", "nathaniel nate nathan",
    "cameron cam", "maxwell max", "vincent vince", "leonard leo len lenny", "harold harry",
    "theodore teddy", "phillip phil philip", "gabriel gabe", "tobias toby", "mitchell mitch",
    "kristopher kris", "isaiah ike", "abraham abe", "frank franklin francis", "jerrod jared",
    "dwayne duane", "demarcus marcus", "lavon von", "terrence terry terrance", "clifford cliff",
    "russell russ", "stanley stan", "bradley brad", "gary garry", "deshawn shawn", "trenton trent",
]
NICK = {}
for g in NICK_GROUPS:
    names = g.split()
    for n in names:
        NICK.setdefault(n, names[0])

def canon(key):
    t = key.split(" ")
    if len(t) > 1 and t[0] in NICK:
        t[0] = NICK[t[0]]
    return " ".join(t)

POS_MAP = {"OL": "OL", "T": "OT", "G": "G", "C": "C", "OT": "OT", "OG": "G", "LT": "OT", "RT": "OT",
           "DL": "DL", "DE": "DE", "DT": "DT", "NT": "DT", "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
           "DB": "DB", "CB": "CB", "S": "S", "SS": "S", "FS": "S", "SAF": "S", "QB": "QB", "RB": "RB",
           "HB": "RB", "FB": "FB", "WR": "WR", "TE": "TE", "K": "K", "P": "P", "LS": "LS", "KR": "WR", "PR": "WR"}

teams = json.load(open(os.path.join(HERE, "teams_orig.json")))
team_ids = [t["id"] for t in teams]

# ---------- nflverse rosters ----------
rows = []
for f in sorted(glob.glob(os.path.join(NFL, "roster_*.csv"))):
    for r in csv.DictReader(open(f, encoding="utf-8")):
        if not r["full_name"].strip():
            continue
        rows.append(r)
print("nflverse rows", len(rows))

HEAD_RE = re.compile(r"^https://static\.www\.nfl\.com/image/(upload|private)/f_auto,q_auto/league/([A-Za-z0-9_]+)$")
def headshot_id(u):
    """NFL headshot -> compact id: 'u' or 'p' (upload/private) + the image id. Rebuilt into a URL in the game."""
    m = HEAD_RE.match((u or "").strip())
    return (m.group(1)[0] + m.group(2)) if m else ""

IMG_MIN_SEASON = 1990   # photos for players fans would recognise by face; older rows are mostly placeholders

def pid(r):
    return r["gsis_id"] or r["pfr_id"] or (norm(r["full_name"]) + "|" + (r["birth_date"] or r["team"]))

# draft fame by gsis / pfr id
fame_ext = {}
for d in csv.DictReader(open(os.path.join(NFL, "draft_picks.csv"), encoding="utf-8")):
    f = {"pb": int(d["probowls"] or 0), "ap": int(d["allpro"] or 0), "hof": d["hof"] == "TRUE",
         "av": int(float(d["w_av"] or d["car_av"] or 0)), "rd": int(d["round"] or 9)}
    for k in (d["gsis_id"], d["pfr_player_id"]):
        if k:
            fame_ext[k] = f

# ---------- map each (team code, season) bucket to franchises by name overlap ----------
known = {}
for t in teams:
    s = set()
    for e in t["a"] + t["c"]:
        s.add(norm(e.split("|")[0]))
    known[t["id"]] = s
buckets = collections.defaultdict(set)
for r in rows:
    buckets[(r["team"], int(r["season"]))].add(norm(r["full_name"]))
assign = collections.defaultdict(set)  # (code, season) -> {team ids}
CODE_HINT = {"BUF": "buf", "MIA": "mia", "NE": "ne", "NYJ": "nyj", "BAL": "bal", "CIN": "cin", "CLE": "cle",
             "PIT": "pit", "HOU": "hou", "IND": "ind", "JAX": "jax", "TEN": "ten", "DEN": "den", "KC": "kc",
             "LV": "lv", "LAC": "lac", "DAL": "dal", "NYG": "nyg", "PHI": "phi", "WAS": "was", "CHI": "chi",
             "DET": "det", "GB": "gb", "MIN": "min", "ATL": "atl", "CAR": "car", "NO": "no", "TB": "tb",
             "ARI": "ari", "LA": "lar", "SF": "sf", "SEA": "sea"}
for (code, season), names in buckets.items():
    if season == CUR_SEASON and code in CODE_HINT:
        assign[(code, season)].add(CODE_HINT[code]); continue
    for tid in team_ids:
        ov = len(names & known[tid]) / max(1, len(names))
        if ov >= 0.45:
            assign[(code, season)].add(tid)
# Hand fixes where roster overlap misleads: the 1995 Browns are Cleveland's history (the Ravens began in 1996),
# the 1925 Kansas City Cowboys are not the Giants, and the wartime merged teams count for both franchises.
assign[("CLE", 1995)].discard("bal")
assign[("BAL", 1996)].discard("cle")
assign[("KC", 1925)].discard("nyg")
assign[("P-P", 1943)] |= {"phi", "pit"}
assign[("C-P", 1944)] |= {"ari", "pit"}
spans = collections.defaultdict(lambda: collections.defaultdict(list))
for (code, season), tids in assign.items():
    for tid in tids:
        spans[tid][code].append(season)
with open(os.path.join(HERE, "franchise_map.txt"), "w") as fh:
    for tid in team_ids:
        fh.write(tid + ": " + ", ".join(f"{c} {min(v)}-{max(v)} ({len(v)})" for c, v in sorted(spans[tid].items(), key=lambda kv: min(kv[1]))) + "\n")

# ---------- per franchise player records from nflverse ----------
PLAYED = {"ACT", "RES", "INA", "", "TRD", "TRC", "TRT", "SUS", "RSN", "EXE", "RET", "CUT"}
recs = {tid: {} for tid in team_ids}
cur = {tid: {} for tid in team_ids}
maxweek = collections.defaultdict(int)
for r in rows:
    if int(r["season"]) == CUR_SEASON:
        maxweek[r["team"]] = max(maxweek[r["team"]], int(r["week"] or 0))
for r in rows:
    season = int(r["season"])
    tids = assign.get((r["team"], season))
    if not tids:
        continue
    k = pid(r)
    for tid in tids:
        rec = recs[tid].get(k)
        if not rec:
            rec = recs[tid][k] = {"name": r["full_name"].strip(), "alt": set(), "seasons": set(), "played": False,
                                  "pos": "", "last": 0, "ids": set(), "yexp": 0, "rd": 9, "dev_only": True, "img": ""}
        rec["alt"].add(r["full_name"].strip())
        fn = (r.get("football_name") or "").strip()
        if fn and r["last_name"] and fn.lower() != (r["first_name"] or "").lower():
            rec["alt"].add(fn + " " + r["last_name"].strip())
        if r["first_name"] and r["last_name"]:
            rec["alt"].add(r["first_name"].strip() + " " + r["last_name"].strip())
        rec["seasons"].add(season)
        if r["status"] != "DEV":
            rec["dev_only"] = False
        if r["status"] in PLAYED and r["status"] != "CUT":
            rec["played"] = True
        if season >= rec["last"]:
            rec["last"] = season
            rec["name"] = r["full_name"].strip()
            rec["img"] = headshot_id(r.get("headshot_url", "")) or rec["img"]
            p = POS_MAP.get(r["depth_chart_position"]) or POS_MAP.get(r["position"]) or rec["pos"]
            rec["pos"] = p or ""
        for idk in (r["gsis_id"], r["pfr_id"]):
            if idk:
                rec["ids"].add(idk)
        try:
            rec["yexp"] = max(rec["yexp"], int(r["years_exp"] or 0))
        except ValueError:
            pass
        if season == CUR_SEASON and int(r["week"] or 0) == maxweek[r["team"]] and r["status"] in ("ACT", "RES", "DEV", "INA") \
                and CODE_HINT.get(r["team"]) == tid:
            cur[tid][k] = rec
            rec["cur_status"] = r["status"]

GLOBAL = collections.defaultdict(dict)  # canon name -> {pid: rec-like}
for r in rows:
    k = pid(r)
    g = GLOBAL[canon(norm(r["full_name"]))].setdefault(k, {"name": r["full_name"], "alt": set(), "seasons": set(), "last": 0, "ids": set(), "pos": "", "yexp": 0})
    g["seasons"].add(int(r["season"])); g["last"] = max(g["last"], int(r["season"]))
    for idk in (r["gsis_id"], r["pfr_id"]):
        if idk: g["ids"].add(idk)
    g["pos"] = POS_MAP.get(r["depth_chart_position"]) or POS_MAP.get(r["position"]) or g["pos"]

def global_rec(name):
    """Mid-season trades leave no row for the team he left. Fall back to his career, counted as one season here."""
    cands = GLOBAL.get(canon(norm(name)), {})
    if len(cands) == 1:
        g = dict(next(iter(cands.values())))
        g["seasons"] = {g["last"]}
        return g
    return None

def ext(rec):
    for i in rec["ids"]:
        if i in fame_ext:
            return fame_ext[i]
    return None

# ---------- merge with the curated lists ----------
TIER_ALL = {"S": 150, "R": 80, "P": 40, "D": 0}

def recency_weight(last):
    if last >= CUR_SEASON - 1: return 1.0
    for yr, w in ((2018, 0.85), (2010, 0.7), (2000, 0.5), (1990, 0.35), (1980, 0.22), (1970, 0.14)):
        if last >= yr: return w
    return 0.08

def on_roster(tid, rec):
    return any(r is rec for r in cur[tid].values())
TIER_CUR = {"S": 100, "R": 55, "P": 25, "D": 8, "Q": 0}
POS_FAME = {"QB": 40, "RB": 18, "WR": 18, "TE": 12, "FB": -5, "DE": 8, "DL": 4, "DT": 4, "LB": 6, "CB": 6, "S": 4, "DB": 3,
            "OT": -4, "G": -8, "C": -6, "OL": -6, "K": 0, "P": -12, "LS": -30}
stats = collections.Counter()

def build(t, mode):
    src = t["c"] if mode == "c" else t["a"]
    entries = {}  # norm key -> entry
    idx = {}      # norm / canon key -> norm key
    cur_names = {norm(e.split("|")[0]) for e in t["c"]}
    if mode == "c":
        pool_recs = {k: r for k, r in recs[t["id"]].items() if CUR_SEASON in r["seasons"]}
    else:
        pool_recs = recs[t["id"]]
    # How many distinct real players share each nickname-folded name on this team.
    rc = collections.defaultdict(set)
    for pk, r in pool_recs.items():
        for a in r["alt"] | {r["name"]}:
            rc[canon(norm(a))].add(pk)
    RANK = {"S": 0, "R": 1, "P": 2, "D": 3, "Q": 4}
    for e in src:
        n, pos, tier = e.split("|")[:3]
        if JUNK.search(n):
            stats["junk_removed"] += 1
            continue
        extra = nick_aliases(n)
        n = clean_display(n)
        k = norm(n)
        if k in entries:
            entries[k]["alt"] |= extra
            continue
        ck = canon(k)
        if ck in idx and len(rc[ck]) <= 1:
            # Same person listed twice under a nickname (Josh / Joshua Palmer): one entry, both names accepted.
            ex = entries[idx[ck]]
            ex["alt"].add(n)
            if RANK.get(tier, 5) < RANK.get(ex["tier"], 5):
                ex["alt"].add(ex["name"]); ex["name"], ex["tier"] = n, tier
            ex["pos"] = ex["pos"] or pos
            stats[mode + "_merged_dupes"] += 1
            continue
        entries[k] = {"name": n, "pos": pos, "tier": tier, "alt": set(extra), "rec": None}
        idx.setdefault(k, k); idx.setdefault(ck, k)
    for k, rec in pool_recs.items():
        hit = None
        for nm in [rec["name"]] + sorted(rec["alt"]):
            nk = norm(nm)
            if nk in idx: hit = idx[nk]; break
            if canon(nk) in idx: hit = idx[canon(nk)]; break
        if hit and entries[hit]["rec"] is None:
            entries[hit]["rec"] = rec
            entries[hit]["alt"] |= rec["alt"]
            stats[mode + "_matched"] += 1
            continue
        if hit:
            continue  # same name already matched to another record (two different players, one name)
        on_roster_now = k in cur[t["id"]] or norm(rec["name"]) in cur_names
        if mode == "c" and k not in cur[t["id"]]:
            continue  # current = this week's roster only
        if mode == "a" and (not rec["played"] or rec["dev_only"]) and not on_roster_now:
            continue  # all-time = people who actually suited up, plus today's roster
        nk = norm(rec["name"])
        if nk in entries:
            continue
        entries[nk] = {"name": rec["name"], "pos": rec["pos"], "tier": None, "alt": set(rec["alt"]), "rec": rec}
        idx.setdefault(nk, nk); idx.setdefault(canon(nk), nk)
        stats[mode + "_added"] += 1
    # All-Time must contain everyone on today's roster.
    if mode == "a":
        for e in t["c"]:
            n, pos, tier = e.split("|")[:3]
            k = norm(n)
            if k not in idx and canon(k) not in idx:
                entries[k] = {"name": n, "pos": pos, "tier": "D", "alt": set(), "rec": None}
                idx[k] = k
                stats["a_from_current"] += 1
    # fame score
    out = []
    for k, e in entries.items():
        if e["rec"] is None and mode == "a":
            e["rec"] = global_rec(e["name"])
            if e["rec"]:
                stats["a_global_fallback"] += 1
        rec, f = e["rec"], 0.0
        x = ext(rec) if rec else None
        pos = e["pos"] or (rec["pos"] if rec else "")
        pw = POS_FAME.get(pos, 0)   # fans know quarterbacks and receivers; nobody knows the long snapper
        if mode == "a":
            # Fame TODAY, not fame in his era: how many fans would recognise the name now.
            # Curated legends and Hall of Famers stay famous forever; everything else fades with time.
            f += TIER_ALL.get(e["tier"], 0) if e["tier"] else 0
            last = rec["last"] if rec else 0
            rw = recency_weight(last)
            if norm(e["name"]) in cur_names or (rec and on_roster(t["id"], rec)):
                f += 12
            if rec:
                f += rw * 5 * min(len(rec["seasons"]), 12)
            f += 2 * pw * (0.3 + 0.7 * rw)
            if x:
                f += 140 if x["hof"] else 0
                f += (6 * x["pb"] + 9 * x["ap"] + 0.3 * min(x["av"], 160)) * (0.4 + 0.6 * rw)
                f += rw * {1: 12, 2: 6, 3: 2}.get(x["rd"], 0)
        else:
            f += TIER_CUR.get(e["tier"], 10) if e["tier"] else 10
            f += pw
            if rec:
                f += 1.5 * min(rec["yexp"], 10) + min(len(rec["seasons"]), 6)
                if rec.get("cur_status") == "DEV":
                    f -= 15
            if x:
                f += 8 * min(x["pb"], 8) + 12 * min(x["ap"], 5) + 0.15 * min(x["av"], 160) + {1: 12, 2: 5}.get(x["rd"], 0)
        pos = e["pos"] or (rec["pos"] if rec else "")
        aliases = sorted({a for a in e["alt"] if norm(a) != k and norm(a)})
        img = rec.get("img", "") if rec and (mode == "c" or rec.get("last", 0) >= IMG_MIN_SEASON) else ""
        out.append([e["name"], pos, f, aliases, (rec["last"] if rec else 0), img])
    # rarity = rank within this pool, 1 = most famous, 99 = deepest cut. Ties share a rank.
    out.sort(key=lambda p: -p[2])
    n = len(out)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(out[j + 1][2] - out[i][2]) < 1e-9:
            j += 1
        mid = (i + j) / 2
        r = 1 + round(98 * mid / max(1, n - 1))
        for q in range(i, j + 1):
            out[q].append(r)
        i = j + 1
    return out

result = []
IMAGES = {}   # team -> era -> headshot ids aligned with the roster arrays (written per team, loaded on demand)
for t in teams:
    c = build(t, "c")
    a = build(t, "a")
    def ser(p):
        s = f"{p[0]}|{p[1]}|{p[6]}"
        if p[3]:
            s += "|" + "~".join(p[3])
        return s
    nt = {k: t[k] for k in ("id", "city", "name", "div", "color", "ink", "ff", "cff")}
    nt["c"] = [ser(p) for p in c]
    nt["a"] = [ser(p) for p in a]
    IMAGES[t["id"]] = {"c": [p[5] for p in c], "a": [p[5] for p in a]}
    result.append(nt)
    print(t["id"], "current", len(c), "all-time", len(a))
print(dict(stats))
with open(os.path.join(HERE, "rosters.js"), "w", encoding="utf-8") as fh:
    fh.write("/* THE 53 rosters. Generated by build_data.py from nflverse rosters 1920-%d plus the curated franchise lists.\n" % CUR_SEASON)
    fh.write("   Entry: Name|POS|rarity(1 star..99 deepest cut)|aliases separated by ~ */\n")
    fh.write("var ROSTER_SEASON=%d;\nvar TEAMS=[\n" % CUR_SEASON)
    fh.write(",\n".join(json.dumps(t, separators=(",", ":"), ensure_ascii=False) for t in result))
    fh.write("\n];\n")
print("wrote rosters.js", os.path.getsize(os.path.join(HERE, "rosters.js")))
with open(os.path.join(HERE, "images.json"), "w") as fh:
    json.dump(IMAGES, fh, separators=(",", ":"))
