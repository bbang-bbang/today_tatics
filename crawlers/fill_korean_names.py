#!/usr/bin/env python3
"""
kleague_players_2026.json 의 한글 이름을 players 테이블에 채운다.
매칭 기준: sofascore_id(team) + shirt_number
"""
import json, sqlite3, sys, os

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.path.join(BASE_DIR, "players.db")
JSON_PATH = os.path.join(BASE_DIR, "data", "kleague_players_2026.json")

# ── TEAMS 매핑 (id → sofascore_id) ──────────────────────────────
TEAMS = [
    {"id": "ulsan",    "sofascore_id": 7653},
    {"id": "pohang",   "sofascore_id": 7650},
    {"id": "jeju",     "sofascore_id": 7649},
    {"id": "jeonbuk",  "sofascore_id": 6908},
    {"id": "fcseoul",  "sofascore_id": 7646},
    {"id": "daejeon",  "sofascore_id": 7645},
    {"id": "incheon",  "sofascore_id": 7648},
    {"id": "gangwon",  "sofascore_id": 34220},
    {"id": "gwangju",  "sofascore_id": 48912},
    {"id": "bucheon",  "sofascore_id": 92539},
    {"id": "anyang",   "sofascore_id": 32675},
    {"id": "gimcheon", "sofascore_id": 7647},
    {"id": "suwon",    "sofascore_id": 7652},
    {"id": "busan",    "sofascore_id": 7642},
    {"id": "jeonnam",  "sofascore_id": 7643},
    {"id": "seongnam", "sofascore_id": 7651},
    {"id": "daegu",    "sofascore_id": 7644},
    {"id": "gyeongnam","sofascore_id": 7641},
    {"id": "suwon_fc", "sofascore_id": 41261},
    {"id": "seouland", "sofascore_id": 189422},
    {"id": "ansan",    "sofascore_id": 248375},
    {"id": "asan",     "sofascore_id": 339827},
    {"id": "gimpo",    "sofascore_id": 195172},
    {"id": "cheongju", "sofascore_id": 314293},
    {"id": "cheonan",  "sofascore_id": 41263},
    {"id": "hwaseong", "sofascore_id": 195174},
    {"id": "paju",     "sofascore_id": 314294},
    {"id": "gimhae",   "sofascore_id": 41260},
    {"id": "yongin",   "sofascore_id": 41266},
]

ss_id_map = {t["id"]: t["sofascore_id"] for t in TEAMS}

with open(JSON_PATH, encoding="utf-8") as f:
    all_players = json.load(f)

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

total_inserted = 0
total_updated  = 0

for team_slug, tdata in all_players.items():
    ss_id = ss_id_map.get(team_slug)
    if not ss_id:
        print(f"[SKIP] {team_slug} → sofascore_id 없음")
        continue

    players_json = tdata.get("players", [])
    # number → 풀 메타 매핑 (name_ko, height, weight, dob, position)
    def parse_dob(s):
        # "2007/01/24" → ts로 저장 (기존 dob 컬럼은 TEXT 형식이라 그대로)
        return s if s else None
    num_to_meta = {
        p["number"]: {
            "name_ko": p.get("name"),
            "height":  p.get("height"),
            "weight":  p.get("weight"),
            "dob":     parse_dob(p.get("dob")),
            "position":p.get("position"),
        }
        for p in players_json if p.get("number") and p.get("name")
    }

    # match_player_stats에서 해당 팀 선수 목록
    cur.execute("""
        SELECT DISTINCT player_id, player_name, shirt_number
        FROM match_player_stats
        WHERE team_id = ?
    """, (ss_id,))
    mps_players = cur.fetchall()

    inserted = updated_ko = updated_phys = 0
    for pid, pname, shirt_num in mps_players:
        meta = num_to_meta.get(shirt_num)
        if not meta:
            continue
        name_ko = meta["name_ko"]
        height  = meta["height"]
        weight  = meta["weight"]
        dob     = meta["dob"]

        # players 테이블에 이미 있는지 확인
        cur.execute("SELECT id, name_ko, height, weight, dob FROM players WHERE id = ?", (pid,))
        existing = cur.fetchone()

        if existing is None:
            cur.execute("""
                INSERT INTO players (id, team_id, name, shirt_number, name_ko, height, weight, dob)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (pid, ss_id, pname, shirt_num, name_ko, height, weight, dob))
            inserted += 1
            continue

        # COALESCE 패턴: 기존 값 비어있을 때만 채움 (덮어쓰지 않음)
        new_ko     = name_ko if (not existing[1] or existing[1] == "") else existing[1]
        new_height = height  if (not existing[2] or existing[2] == 0)  else existing[2]
        new_weight = weight  if (not existing[3] or existing[3] == 0)  else existing[3]
        new_dob    = dob     if (not existing[4])                       else existing[4]

        ko_change   = (new_ko != existing[1] and name_ko)
        phys_change = (new_height != existing[2] or new_weight != existing[3] or new_dob != existing[4])

        if ko_change or phys_change:
            cur.execute("""
                UPDATE players
                SET name_ko=?, height=?, weight=?, dob=?
                WHERE id=?
            """, (new_ko, new_height, new_weight, new_dob, pid))
            if ko_change:   updated_ko += 1
            if phys_change: updated_phys += 1

    conn.commit()
    team_name = tdata.get("team_name", team_slug)
    matched = sum(1 for _, _, sn in mps_players if num_to_meta.get(sn))
    print(f"[{team_name}] 선수 {len(mps_players)}명 매칭 {matched}명 / 신규 {inserted} / name_ko {updated_ko} / 신체정보 {updated_phys}")
    total_inserted += inserted
    total_updated  += updated_ko + updated_phys

print(f"\n완료(phase1): 총 신규 {total_inserted}건, 업데이트 {total_updated}건")


# ── Phase 2a: players.team_id 기반 매핑 ──────────────────────
# player의 master team_id가 K1/K2 SS_ID인 경우(=정상 등록 외국인 포함) 그 팀 portal의
# #shirt_number 매칭 우선. lineup historic(2b)보다 정확 — 예: Leonard Pllana
# (team_id=hwaseong, shirt=11)는 historic으로는 gimpo #11(35경기)이 빈도 최다라
# 잘못된 "이시헌"이 매핑될 위험. master team_id 기준이면 hwaseong #11 = "플라나" 정답.

ss_id_to_slug = {v: k for k, v in ss_id_map.items()}
ss_ids_csv = ",".join(str(v) for v in ss_id_map.values())

cur.execute(f"""
    SELECT id, team_id, shirt_number, name, name_ko
    FROM players
    WHERE team_id IN ({ss_ids_csv})
      AND shirt_number IS NOT NULL
      AND (name_ko IS NULL OR name_ko='' OR name_ko GLOB '*[a-zA-Z]*')
""")
phase2a_targets = cur.fetchall()
phase2a_updated = 0
for pid, tid, shirt, name, name_ko in phase2a_targets:
    slug = ss_id_to_slug.get(tid)
    if not slug:
        continue
    portal = all_players.get(slug, {}).get("players", [])
    match = next((p for p in portal if p.get("number") == shirt and p.get("name")), None)
    if not match:
        continue
    cur.execute(
        "UPDATE players SET name_ko=? WHERE id=? AND ("
        " name_ko IS NULL OR name_ko='' OR name_ko GLOB '*[a-zA-Z]*')",
        (match["name"], pid)
    )
    if cur.rowcount:
        phase2a_updated += 1
conn.commit()
print(f"완료(phase2a master team_id 기반): name_ko {phase2a_updated}건")


# ── Phase 2b: lineup 기반 fallback ───────────────────────────
# phase2a로도 못 잡은 케이스 — player.team_id가 외부(2군/유스/K3) 또는 NULL.
# 예: Ann Juwan(player.team_id=241802=Seoul E-Land 2군 추정)이지만 K2 매치엔
# #70 등번호로 seouland 소속처럼 출장.
#
# lineup에서 실제 출장한 매치 정보를 통해 K1/K2 소속 팀을 역추적:
#   - is_home=1 → events.home_team_id (K1/K2 SS_ID)
#   - is_home=0 → events.away_team_id
# 같은 선수가 여러 매치 출장 시 빈도 최다 팀 사용.

cur.execute(f"""
    SELECT
        ml.player_id,
        ml.shirt_number,
        CASE WHEN ml.is_home=1 THEN e.home_team_id ELSE e.away_team_id END AS k_team_ss,
        COUNT(*) AS cnt
    FROM match_lineups ml
    JOIN events e ON e.id = ml.event_id
    LEFT JOIN players p ON p.id = ml.player_id
    WHERE (p.name_ko IS NULL OR p.name_ko = '' OR p.name_ko GLOB '*[a-zA-Z]*')
      AND ml.shirt_number IS NOT NULL
      AND (p.team_id IS NULL OR p.team_id NOT IN ({ss_ids_csv}))
      AND (CASE WHEN ml.is_home=1 THEN e.home_team_id ELSE e.away_team_id END)
          IN ({ss_ids_csv})
    GROUP BY ml.player_id, ml.shirt_number, k_team_ss
    ORDER BY ml.player_id, cnt DESC
""")
rows = cur.fetchall()

# player_id별로 빈도 최다 (팀, shirt_number) 선택
best_for_pid = {}
for pid, shirt, k_team_ss, cnt in rows:
    if pid not in best_for_pid:
        best_for_pid[pid] = (k_team_ss, shirt, cnt)

phase2b_updated = 0
for pid, (k_team_ss, shirt, _) in best_for_pid.items():
    slug = ss_id_to_slug.get(k_team_ss)
    if not slug:
        continue
    team_data = all_players.get(slug, {})
    players_json = team_data.get("players", [])
    match = next((p for p in players_json if p.get("number") == shirt and p.get("name")), None)
    if not match:
        continue
    # ASCII-only(영문) name_ko도 한글로 덮어쓰기 — phase1/이전 단계에서 영문이
    # 들어간 케이스(예: 배서준→Seo-Joon Bae) 해소. 외국인은 portal name도 영문
    # 이라 변화 없음(영문→영문).
    cur.execute(
        "UPDATE players SET name_ko=? WHERE id=? AND ("
        " name_ko IS NULL OR name_ko='' OR name_ko GLOB '*[a-zA-Z]*')",
        (match["name"], pid)
    )
    if cur.rowcount:
        phase2b_updated += 1

conn.commit()
print(f"완료(phase2b lineup historic fallback): name_ko {phase2b_updated}건")


# ── Phase 2c: portal 우선 덮어쓰기 (잘못된 한글 stale 교정) ─────
# phase2a/2b는 name_ko가 비어있거나 ASCII인 경우만 채움. 한글이 이미 있으면
# 손대지 않음 — 그래서 이적·임대로 새 팀 등번호에 옛 시즌 다른 선수 이름이
# 남는 stale 케이스 발생(예: hwaseong #5 "유선" → 실제 "양시후").
#
# 매칭 기준: master players.shirt_number는 옛 시즌 값일 수 있어 부정확.
# match_lineups의 (player_id, k_team_ss, shirt_number) best 쌍을 사용 —
# verify_player_mapping.py와 동일 알고리즘.
#
# 안전 조건:
#   1) 현 시즌(2026) lineup만 (옛 시즌 stale 회피)
#   2) lineup cnt ≥ 2 (한 번뿐인 일회성 매칭 신뢰도 부족)
#   3) k_team_ss가 K1/K2 SS_ID 중 하나 (K3·미등록 팀 제외)
#   4) portal[slug][best_shirt] entry 존재
#   5) 현재 name_ko가 ASCII 포함 아님 (한글이 박혀있는 stale 케이스만)
#
# master team_id 검증은 제거 — 임대·이적 케이스(player.team_id가 옛 팀)도 정정 가능.

EXCLUDED_EVENT_IDS_SQL = "(90333089)"  # synthetic event 제외 (main.py 동일)

cur.execute(f"""
    WITH appearances AS (
        SELECT ml.player_id,
               ml.shirt_number,
               CASE WHEN ml.is_home=1 THEN e.home_team_id ELSE e.away_team_id END AS k_team_ss,
               COUNT(*) AS cnt
        FROM match_lineups ml
        JOIN events e ON e.id=ml.event_id
        WHERE e.tournament_id IN (410, 777)
          AND e.id NOT IN {EXCLUDED_EVENT_IDS_SQL}
          AND date(e.date_ts, 'unixepoch', 'localtime') >= '2026-01-01'
          AND ml.shirt_number IS NOT NULL
        GROUP BY ml.player_id, ml.shirt_number, k_team_ss
    ),
    best_per_player AS (
        SELECT player_id, shirt_number, k_team_ss, cnt,
               ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY cnt DESC) AS rn
        FROM appearances
    )
    SELECT p.id, p.team_id, p.name_ko, b.k_team_ss, b.shirt_number, b.cnt
    FROM best_per_player b
    JOIN players p ON p.id=b.player_id
    WHERE b.rn=1
      AND b.cnt >= 2
      AND b.k_team_ss IN ({ss_ids_csv})
      AND p.name_ko IS NOT NULL AND p.name_ko != ''
      AND p.name_ko NOT GLOB '*[a-zA-Z]*'
""")
phase2c_targets = cur.fetchall()
phase2c_updated = 0
for pid, master_team, name_ko, k_team_ss, shirt, cnt in phase2c_targets:
    slug = ss_id_to_slug.get(k_team_ss)
    if not slug:
        continue
    portal = all_players.get(slug, {}).get("players", [])
    match = next((p for p in portal if p.get("number") == int(shirt) and p.get("name")), None)
    if not match:
        continue
    portal_name = match["name"]
    if portal_name == name_ko:
        continue
    cur.execute("UPDATE players SET name_ko=? WHERE id=?", (portal_name, pid))
    if cur.rowcount:
        phase2c_updated += 1
        print(f"  phase2c overwrite: pid={pid} {slug} #{shirt} '{name_ko}' → '{portal_name}'")

conn.commit()
print(f"완료(phase2c portal 우선 덮어쓰기): name_ko {phase2c_updated}건")
conn.close()
