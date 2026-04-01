"""
2024~2026 K리그 홈/원정 승률 통계 크롤러
kleague_team_stats.json 을 최근 3년 데이터로 갱신한다.
"""
import json
import urllib.request
import urllib.error
import time

# K리그 공식 팀 코드 → 내부 ID
TEAM_CODE_MAP = {
    "K01": "ulsan",
    "K02": "suwon",
    "K03": "pohang",
    "K04": "jeju",
    "K05": "jeonbuk",
    "K06": "busan",
    "K07": "jeonnam",
    "K08": "seongnam",
    "K09": "fcseoul",
    "K10": "daejeon",
    "K17": "daegu",
    "K18": "incheon",
    "K20": "gyeongnam",
    "K21": "gangwon",
    "K22": "gwangju",
    "K26": "bucheon",
    "K27": "anyang",
    "K29": "suwon_fc",
    "K31": "seouland",
    "K32": "ansan",
    "K34": "asan",
    "K35": "gimcheon",
    "K36": "gimpo",
    "K37": "cheongju",
    "K38": "cheonan",
    "K39": "hwaseong",
    "K40": "paju",
    "K41": "gimhae",
    "K42": "yongin",
}

def fetch_schedule(league_id, year, month):
    url = "https://www.kleague.com/getScheduleList.do"
    payload = json.dumps({"leagueId": str(league_id), "year": str(year), "month": str(month).zfill(2)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json; charset=UTF-8", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            return data.get("data", {}).get("scheduleList", [])
    except Exception as e:
        print(f"  Error {league_id}/{year}/{month}: {e}")
        return []

stats = {}

def add(team_id, is_home, result):
    if team_id not in stats:
        stats[team_id] = {
            "home": {"w":0,"d":0,"l":0,"games":0},
            "away": {"w":0,"d":0,"l":0,"games":0},
        }
    slot = "home" if is_home else "away"
    stats[team_id][slot]["games"] += 1
    if result == "W":
        stats[team_id][slot]["w"] += 1
    elif result == "D":
        stats[team_id][slot]["d"] += 1
    else:
        stats[team_id][slot]["l"] += 1

YEARS = [2024, 2025, 2026]
LEAGUES = [("1", "K1"), ("2", "K2")]

for year in YEARS:
    months = range(1, 13) if year < 2026 else range(1, 5)
    for league_id, league_name in LEAGUES:
        for month in months:
            games = fetch_schedule(league_id, year, month)
            for g in games:
                # 완료된 경기만 (endYn == 'Y' 또는 gameStatus == 'FE')
                if g.get("endYn") != "Y" and g.get("gameStatus") != "FE":
                    continue
                hs = g.get("homeGoal")
                aws = g.get("awayGoal")
                if hs is None or aws is None:
                    continue
                try:
                    hs = int(hs)
                    aws = int(aws)
                except:
                    continue

                home_code = g.get("homeTeam", "")
                away_code = g.get("awayTeam", "")
                home_id = TEAM_CODE_MAP.get(home_code)
                away_id = TEAM_CODE_MAP.get(away_code)

                if hs > aws:
                    hr, ar = "W", "L"
                elif hs < aws:
                    hr, ar = "L", "W"
                else:
                    hr, ar = "D", "D"

                if home_id:
                    add(home_id, True, hr)
                else:
                    print(f"  Unknown home team code: {home_code!r}")
                if away_id:
                    add(away_id, False, ar)
                else:
                    print(f"  Unknown away team code: {away_code!r}")

            time.sleep(0.1)
        print(f"  {year} {league_name} done")

out_path = "kleague_team_stats.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print(f"\n저장 완료: {out_path}  ({len(stats)} teams)")
for tid, s in sorted(stats.items()):
    print(f"  {tid}: home {s['home']['w']}W{s['home']['d']}D{s['home']['l']}L ({s['home']['games']}g)  away {s['away']['w']}W{s['away']['d']}D{s['away']['l']}L ({s['away']['games']}g)")
