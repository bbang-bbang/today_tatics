import json
import os
import uuid
import sqlite3
import urllib.request
from datetime import datetime

from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SAVES_DIR   = os.path.join(BASE_DIR, "saves")
SQUADS_DIR  = os.path.join(BASE_DIR, "squads")
STATUS_FILE = os.path.join(BASE_DIR, "data", "player_status.json")
os.makedirs(SAVES_DIR, exist_ok=True)
os.makedirs(SQUADS_DIR, exist_ok=True)

def _init_default_squads():
    """kleague_players_2026.json 을 읽어 팀별 기본 스쿼드 파일을 생성한다."""
    players_file = os.path.join(BASE_DIR, "data", "kleague_players_2026.json")
    if not os.path.exists(players_file):
        return
    with open(players_file, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    now = datetime.now().isoformat()
    for team_id, tdata in all_data.items():
        fpath = os.path.join(SQUADS_DIR, f"default_{team_id}.json")
        if os.path.exists(fpath):       # 이미 있으면 덮어쓰지 않음
            continue
        players = [{"number": p["number"], "name": p["name"], "position": p.get("position",""), "height": p.get("height",0), "weight": p.get("weight",0), "dob": p.get("dob","")} for p in tdata.get("players", [])]
        data = {
            "id": f"default_{team_id}",
            "teamId": team_id,
            "name": f"2026 시즌 ({tdata.get('team_name', team_id)})",
            "players": players,
            "createdAt": now,
            "updatedAt": now,
        }
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

_init_default_squads()

# ── K리그 2026 팀 데이터 (K리그 데이터 포털 기준) ─────────
TEAMS = [
    # K1 리그 (12팀)
    # border_home: HOME 킷 아이콘 테두리색 / border_away: AWAY 킷 아이콘 테두리색
    {"id": "ulsan",    "sofascore_id": 7653,  "name": "울산 HD FC",        "short": "울산",   "league": "K1", "primary": "#1d5fa5", "secondary": "#ffffff", "accent": "#f2a900", "emblem": "emblem_K01.png", "border_home": "#fbf500", "border_away": "#6294c1"},
    {"id": "pohang",   "sofascore_id": 7650,  "name": "포항 스틸러스",      "short": "포항",   "league": "K1", "primary": "#d41123", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K03.png", "border_home": "#191e24", "border_away": "#c70027"},
    {"id": "jeju",     "sofascore_id": 7649,  "name": "제주 유나이티드",     "short": "제주",   "league": "K1", "primary": "#f47920", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K04.png", "border_home": "#121928", "border_away": "#121928"},
    {"id": "jeonbuk",  "sofascore_id": 6908,  "name": "전북 현대 모터스",    "short": "전북",   "league": "K1", "primary": "#0a4436", "secondary": "#ffffff", "accent": "#ffd700", "emblem": "emblem_K05.png", "border_home": "#50b79a", "border_away": "#214b4f"},
    {"id": "fcseoul",  "sofascore_id": 7646,  "name": "FC 서울",           "short": "서울",   "league": "K1", "primary": "#ef3744", "secondary": "#e8e7ef", "accent": "#ffd700", "emblem": "emblem_K09.png", "border_home": "#161516", "border_away": "#1f2125"},
    {"id": "daejeon",  "sofascore_id": 7645,  "name": "대전 하나 시티즌",    "short": "대전",   "league": "K1", "primary": "#059a86", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K10.png", "border_home": "#771e34", "border_away": "#771e34"},
    {"id": "incheon",  "sofascore_id": 7648,  "name": "인천 유나이티드",     "short": "인천",   "league": "K1", "primary": "#01a0fc", "secondary": "#bac6d4", "accent": "#ffffff", "emblem": "emblem_K18.png", "border_home": "#1f2521", "border_away": "#52b3f7"},
    {"id": "gangwon",  "sofascore_id": 34220, "name": "강원 FC",           "short": "강원",   "league": "K1", "primary": "#f55947", "secondary": "#e4e3f3", "accent": "#f47920", "emblem": "emblem_K21.png", "border_home": "#191e24", "border_away": "#191e24"},
    {"id": "gwangju",  "sofascore_id": 48912, "name": "광주 FC",           "short": "광주",   "league": "K1", "primary": "#f3ad02", "secondary": "#e4e3ed", "accent": "#000000", "emblem": "emblem_K22.png", "border_home": "#121621", "border_away": "#0f1b2f"},
    {"id": "bucheon",  "sofascore_id": 92539, "name": "부천 FC 1995",      "short": "부천",   "league": "K1", "primary": "#8e272b", "secondary": "#e1d8db", "accent": "#ffffff", "emblem": "emblem_K26.png", "border_home": "#170f0c", "border_away": "##a31822"},
    {"id": "anyang",   "sofascore_id": 32675, "name": "FC 안양",           "short": "안양",   "league": "K1", "primary": "#501b85", "secondary": "#ffffff", "accent": "#ffd700", "emblem": "emblem_K27.png", "border_home": "#ffffff", "border_away": "#501b85"},
    {"id": "gimcheon", "sofascore_id": 7647,  "name": "김천 상무 FC",       "short": "김천",   "league": "K1", "primary": "#df242b", "secondary": "#eeeeee", "accent": "#ffffff", "emblem": "emblem_K35.png", "border_home": "#1d1e2e", "border_away": "#262d3d"},
    # K2 리그 (17팀)
    {"id": "suwon",    "sofascore_id": 7652,  "name": "수원 삼성 블루윙즈",  "short": "수원",   "league": "K2", "primary": "#2553a5", "secondary": "#e7e6ec", "accent": "#c8102e", "emblem": "emblem_K02.png", "border_home": "#253052", "border_away": "#1f4183"},
    {"id": "busan",    "sofascore_id": 7642,  "name": "부산 아이파크",      "short": "부산",   "league": "K2", "primary": "#b4050f", "secondary": "#b7c6ca", "accent": "#ffffff", "emblem": "emblem_K06.png", "border_home": "#120d11", "border_away": "#ffffff"},
    {"id": "jeonnam",  "sofascore_id": 7643,  "name": "전남 드래곤즈",      "short": "전남",   "league": "K2", "primary": "#fbea09", "secondary": "#f0f0f2", "accent": "#000000", "emblem": "emblem_K07.png", "border_home": "#000000", "border_away": "#000000"},
    {"id": "seongnam", "sofascore_id": 7651,  "name": "성남 FC",           "short": "성남",   "league": "K2", "primary": "#0e131b", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K08.png", "border_home": "#ffffff", "border_away": "#1a222d"},
    {"id": "daegu",    "sofascore_id": 7644,  "name": "대구 FC",           "short": "대구",   "league": "K2", "primary": "#86c5e8", "secondary": "#e2e5ea", "accent": "#ffffff", "emblem": "emblem_K17.png", "border_home": "#e2e5ea", "border_away": "#86c5e8"},
    {"id": "gyeongnam","sofascore_id": 22020,  "name": "경남 FC",           "short": "경남",   "league": "K2", "primary": "#ac101b", "secondary": "#d9d9d9", "accent": "#ffffff", "emblem": "emblem_K20.png", "border_home": "#121211", "border_away": "#121211"},
    {"id": "suwon_fc", "sofascore_id": 41261, "name": "수원 FC",           "short": "수원FC", "league": "K2", "primary": "#07306a", "secondary": "#cac3c3", "accent": "#ffffff", "emblem": "emblem_K29.png", "border_home": "#c9232e", "border_away": "#0b3972"},
    {"id": "seouland", "sofascore_id": 189422, "name": "서울 이랜드 FC",     "short": "이랜드", "league": "K2", "primary": "#030a1b", "secondary": "#d7dddd", "accent": "#1e3a8a", "emblem": "emblem_K31.png", "border_home": "#051025", "border_away": "#051025"},
    {"id": "ansan",    "sofascore_id": 248375, "name": "안산 그리너스 FC",    "short": "안산",   "league": "K2", "primary": "#0087a7", "secondary": "#eaedf4", "accent": "#ffd700", "emblem": "emblem_K32.png", "border_home": "#272c3d", "border_away": "#00677f"},
    {"id": "asan",     "sofascore_id": 339827, "name": "충남 아산 FC",       "short": "아산",   "league": "K2", "primary": "#12122c", "secondary": "#dfdfdf", "accent": "#e30613", "emblem": "emblem_K34.png", "border_home": "#d3a84c", "border_away": "#d3a84c"},
    {"id": "gimpo",    "sofascore_id": 195172, "name": "김포 FC",           "short": "김포",   "league": "K2", "primary": "#78bc36", "secondary": "#ebebeb", "accent": "#ffffff", "emblem": "emblem_K36.png", "border_home": "#0f2716", "border_away": "#0f2716"},
    {"id": "cheongju", "sofascore_id": 314293, "name": "충북 청주 FC",       "short": "청주",   "league": "K2", "primary": "#0d1026", "secondary": "#f0f0f0", "accent": "#ffffff", "emblem": "emblem_K37.png", "border_home": "#ae1d25", "border_away": "#0d1026"},
    {"id": "cheonan",  "sofascore_id": 41263,  "name": "천안 시티 FC",       "short": "천안",   "league": "K2", "primary": "#3e8fb3", "secondary": "#e2e2e2", "accent": "#e30613", "emblem": "emblem_K38.png", "border_home": "#201d1d", "border_away": "#3e8fb3"},
    {"id": "hwaseong", "sofascore_id": 195174, "name": "화성 FC",           "short": "화성",   "league": "K2", "primary": "#d45820", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "emblem_K39.png", "border_home": "#fbf5f6", "border_away": "#090811"},
    {"id": "paju",     "sofascore_id": 314294, "name": "파주 시민축구단",     "short": "파주",   "league": "K2", "primary": "#042ba0", "secondary": "#f8f8f8", "accent": "#c8102e", "emblem": "emblem_K40.png", "border_home": "#d381a2", "border_away": "#d381a2"},
    {"id": "gimhae",   "sofascore_id": 41260,  "name": "김해 FC",           "short": "김해",   "league": "K2", "primary": "#ac0d0e", "secondary": "#f3f3f3", "accent": "#ffd700", "emblem": "emblem_K41.png", "border_home": "#2c2c2c", "border_away": "#bba473"},
    {"id": "yongin",   "sofascore_id": 41266,  "name": "용인 시민축구단",     "short": "용인",   "league": "K2", "primary": "#910c26", "secondary": "#dddddd", "accent": "#ffd700", "emblem": "emblem_K42.png", "border_home": "#54bfe1", "border_away": "#8c0e29"},
    # K3 리그 및 기타 (팀명 표시 전용)
    {"id": "siheung",  "sofascore_id": 346812, "name": "시흥 시티",           "short": "시흥",   "league": "K3", "primary": "#000000", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "", "border_home": "#000000", "border_away": "#000000"},
    {"id": "gyeongju", "sofascore_id": 41257,  "name": "경주 KHNP",          "short": "경주",   "league": "K3", "primary": "#000000", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "", "border_home": "#000000", "border_away": "#000000"},
    {"id": "gangneung","sofascore_id": 41258,  "name": "강릉 시티 FC",        "short": "강릉",   "league": "K3", "primary": "#000000", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "", "border_home": "#000000", "border_away": "#000000"},
    {"id": "mokpo",    "sofascore_id": 41259,  "name": "FC 목포",            "short": "목포",   "league": "K3", "primary": "#000000", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "", "border_home": "#000000", "border_away": "#000000"},
    {"id": "changwon", "sofascore_id": 41262,  "name": "창원 시티 FC",        "short": "창원",   "league": "K3", "primary": "#000000", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "", "border_home": "#000000", "border_away": "#000000"},
    {"id": "dj_korail","sofascore_id": 41264,  "name": "대전 코레일",         "short": "코레일", "league": "K3", "primary": "#000000", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "", "border_home": "#000000", "border_away": "#000000"},
    {"id": "jinju",    "sofascore_id": 376197, "name": "진주 시민 FC",        "short": "진주",   "league": "K3", "primary": "#000000", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "", "border_home": "#000000", "border_away": "#000000"},
    {"id": "seosan",   "sofascore_id": 1169779,"name": "서산 시민 FC",        "short": "서산",   "league": "K3", "primary": "#000000", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "", "border_home": "#000000", "border_away": "#000000"},
    {"id": "jincheon", "sofascore_id": 1169782,"name": "진천 HR FC",         "short": "진천",   "league": "K3", "primary": "#000000", "secondary": "#ffffff", "accent": "#ffffff", "emblem": "", "border_home": "#000000", "border_away": "#000000"},
]


@app.route("/api/teams")
def teams():
    return jsonify(TEAMS)


PLAYER_STEP = 0.16  # 선수 간 고정 세로 간격

def compute_formation(formation_str):
    """포메이션 문자열을 파싱하여 선수 좌표(0~1 정규화)를 계산한다."""
    rows = [int(x) for x in formation_str.split("-")]
    positions = []

    # 골키퍼
    positions.append({"x": 0.05, "y": 0.5})

    num_rows = len(rows)
    for row_idx, count in enumerate(rows):
        # x: 0.12 ~ 0.44 (하프라인 직전까지, 중앙 여백 확보)
        x = 0.12 + (row_idx / max(num_rows - 1, 1)) * 0.32
        for player_idx in range(count):
            if count == 1:
                y = 0.5
            else:
                # 최대 5명 기준 전체 높이 0.8 사용
                total_h = min((count - 1) * PLAYER_STEP, 0.80)
                step = total_h / (count - 1)
                start = 0.5 - total_h / 2
                y = start + player_idx * step
            positions.append({"x": round(x, 3), "y": round(y, 3)})

    return positions


POSITION_LABELS = {
    "4-4-2": ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "ST", "ST"],
    "4-3-3": ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "CM", "LW", "ST", "RW"],
    "3-5-2": ["GK", "CB", "CB", "CB", "LM", "CM", "CDM", "CM", "RM", "ST", "ST"],
    "4-2-3-1": ["GK", "LB", "CB", "CB", "RB", "CDM", "CDM", "LW", "AM", "RW", "ST"],
    "4-1-4-1": ["GK", "LB", "CB", "CB", "RB", "CDM", "LM", "CM", "CM", "RM", "ST"],
    "3-4-3": ["GK", "CB", "CB", "CB", "LM", "CM", "CM", "RM", "LW", "ST", "RW"],
    "5-3-2": ["GK", "LWB", "CB", "CB", "CB", "RWB", "CM", "CM", "CM", "ST", "ST"],
    "5-4-1": ["GK", "LWB", "CB", "CB", "CB", "RWB", "LM", "CM", "CM", "RM", "ST"],
}

def mirror_labels(labels):
    result = []
    for label in labels:
        if label.startswith("L"):
            result.append("R" + label[1:])
        elif label.startswith("R"):
            result.append("L" + label[1:])
        else:
            result.append(label)
    return result


FORMATIONS = {}
for name in POSITION_LABELS:
    team_a = compute_formation(name)
    team_b = [{"x": round(1.0 - p["x"], 3), "y": p["y"]} for p in compute_formation(name)]
    FORMATIONS[name] = {
        "teamA": team_a,
        "teamB": team_b,
        "labelsA": POSITION_LABELS[name],
        "labelsB": mirror_labels(POSITION_LABELS[name]),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/formations")
def formations():
    return jsonify(FORMATIONS)


@app.route("/api/saves", methods=["GET"])
def list_saves():
    saves = []
    for fname in os.listdir(SAVES_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(SAVES_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        saves.append({
            "id": data["id"],
            "name": data["name"],
            "formation": data.get("formation", ""),
            "createdAt": data.get("createdAt", ""),
            "updatedAt": data.get("updatedAt", ""),
        })
    saves.sort(key=lambda s: s["updatedAt"], reverse=True)
    return jsonify(saves)


import re
_SAFE_ID_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')

def _safe_path(base_dir, file_id):
    """파일 ID를 검증하고 안전한 절대 경로를 반환한다. 경로 탈출 시 None."""
    if not file_id or not _SAFE_ID_RE.match(file_id):
        return None
    fpath = os.path.normpath(os.path.join(base_dir, f"{file_id}.json"))
    if not fpath.startswith(os.path.normpath(base_dir)):
        return None
    return fpath


@app.route("/api/saves", methods=["POST"])
def create_save():
    body = request.get_json()
    save_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    data = {
        "id": save_id,
        "name": body.get("name", "Untitled"),
        "formation": body.get("formation", ""),
        "players": body.get("players", []),
        "lines": body.get("lines", body.get("arrows", [])),
        "teamAId": body.get("teamAId"),
        "teamBId": body.get("teamBId"),
        "createdAt": now,
        "updatedAt": now,
    }
    fpath = _safe_path(SAVES_DIR, save_id)
    if not fpath:
        return jsonify({"error": "Invalid ID"}), 400
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify(data), 201


@app.route("/api/saves/<save_id>", methods=["GET"])
def get_save(save_id):
    fpath = _safe_path(SAVES_DIR, save_id)
    if not fpath or not os.path.exists(fpath):
        return jsonify({"error": "Not found"}), 404
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/saves/<save_id>", methods=["PUT"])
def update_save(save_id):
    fpath = _safe_path(SAVES_DIR, save_id)
    if not fpath or not os.path.exists(fpath):
        return jsonify({"error": "Not found"}), 404
    with open(fpath, "r", encoding="utf-8") as f:
        existing = json.load(f)
    body = request.get_json()
    existing["name"] = body.get("name", existing["name"])
    existing["formation"] = body.get("formation", existing["formation"])
    existing["players"] = body.get("players", existing["players"])
    existing["lines"] = body.get("lines", existing.get("lines", existing.get("arrows", [])))
    existing["teamAId"] = body.get("teamAId", existing.get("teamAId"))
    existing["teamBId"] = body.get("teamBId", existing.get("teamBId"))
    existing["updatedAt"] = datetime.now().isoformat()
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return jsonify(existing)


@app.route("/api/saves/<save_id>", methods=["DELETE"])
def delete_save(save_id):
    fpath = _safe_path(SAVES_DIR, save_id)
    if not fpath or not os.path.exists(fpath):
        return jsonify({"error": "Not found"}), 404
    os.remove(fpath)
    return jsonify({"ok": True})


# ── 스쿼드(선수 명단) API ──────────────────────────────────
@app.route("/api/squads", methods=["GET"])
def list_squads():
    team_id = request.args.get("teamId")
    squads = []
    for fname in os.listdir(SQUADS_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(SQUADS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if team_id and data.get("teamId") != team_id:
            continue
        squads.append({
            "id": data["id"],
            "teamId": data["teamId"],
            "name": data["name"],
            "playerCount": len(data.get("players", [])),
            "updatedAt": data.get("updatedAt", ""),
        })
    squads.sort(key=lambda s: s["updatedAt"], reverse=True)
    return jsonify(squads)


@app.route("/api/squads", methods=["POST"])
def create_squad():
    body = request.get_json()
    squad_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    data = {
        "id": squad_id,
        "teamId": body.get("teamId", ""),
        "name": body.get("name", "Untitled"),
        "players": body.get("players", []),
        "createdAt": now,
        "updatedAt": now,
    }
    fpath = _safe_path(SQUADS_DIR, squad_id)
    if not fpath:
        return jsonify({"error": "Invalid ID"}), 400
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify(data), 201


@app.route("/api/squads/<squad_id>", methods=["GET"])
def get_squad(squad_id):
    # 직접 파일명으로 시도
    fpath = _safe_path(SQUADS_DIR, squad_id)
    if not fpath:
        return jsonify({"error": "Invalid ID"}), 400
    if not os.path.exists(fpath):
        # 내부 id로 스캔 (safe: listdir은 SQUADS_DIR 내부만 탐색)
        fpath = None
        for fname in os.listdir(SQUADS_DIR):
            if not fname.endswith(".json"):
                continue
            candidate = os.path.join(SQUADS_DIR, fname)
            with open(candidate, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("id") == squad_id:
                fpath = candidate
                break
    if not fpath:
        return jsonify({"error": "Not found"}), 404
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/squads/<squad_id>", methods=["DELETE"])
def delete_squad(squad_id):
    # 직접 파일명으로 시도
    fpath = _safe_path(SQUADS_DIR, squad_id)
    if not fpath:
        return jsonify({"error": "Invalid ID"}), 400
    if not os.path.exists(fpath):
        # 내부 id로 스캔
        fpath = None
        for fname in os.listdir(SQUADS_DIR):
            if not fname.endswith(".json"):
                continue
            candidate = os.path.join(SQUADS_DIR, fname)
            with open(candidate, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("id") == squad_id:
                fpath = candidate
                break
    if not fpath:
        return jsonify({"error": "Not found"}), 404
    os.remove(fpath)
    return jsonify({"ok": True})


# ── 경기 결과 / H2H / 팀 스탯 API ──────────────────────
RESULTS_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kleague_results_2026.json")
H2H_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kleague_h2h.json")
STATS_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kleague_team_stats.json")

@app.route("/api/results")
def get_results():
    team_id = request.args.get("teamId")
    if not os.path.exists(RESULTS_FILE):
        return jsonify([])
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        all_results = json.load(f)
    if team_id:
        return jsonify(all_results.get(team_id, []))
    return jsonify(all_results)

@app.route("/api/h2h")
def get_h2h():
    team_a = request.args.get("teamA")
    team_b = request.args.get("teamB")
    if not team_a or not team_b:
        return jsonify({"error": "teamA and teamB required"}), 400
    if not os.path.exists(H2H_FILE):
        return jsonify({"w": 0, "d": 0, "l": 0, "total": 0})
    with open(H2H_FILE, "r", encoding="utf-8") as f:
        h2h = json.load(f)
    key = f"{team_a}|{team_b}"
    return jsonify(h2h.get(key, {"w": 0, "d": 0, "l": 0, "total": 0}))

@app.route("/api/h2h-matches")
def get_h2h_matches():
    """두 팀 간 최근 맞대결 경기 목록 + 득점 선수 (events DB 기반)"""
    team_a = request.args.get("teamA")
    team_b = request.args.get("teamB")
    if not team_a or not team_b:
        return jsonify([])
    info_a = next((t for t in TEAMS if t["id"] == team_a), None)
    info_b = next((t for t in TEAMS if t["id"] == team_b), None)
    if not info_a or not info_b:
        return jsonify([])
    ss_a, ss_b = info_a["sofascore_id"], info_b["sofascore_id"]

    db_path = os.path.join(BASE_DIR, "players.db")
    if not os.path.exists(db_path):
        return jsonify([])

    from datetime import datetime, timezone
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, date_ts, home_team_id, away_team_id, home_team_name, away_team_name,
               home_score, away_score
        FROM events
        WHERE tournament_id = 777
          AND home_score IS NOT NULL
          AND ((home_team_id=? AND away_team_id=?) OR (home_team_id=? AND away_team_id=?))
        ORDER BY date_ts DESC
        LIMIT 10
    """, (ss_a, ss_b, ss_b, ss_a))
    rows = cur.fetchall()

    result = []
    for event_id, ts, home_id, away_id, home_name, away_name, hs, as_ in rows:
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        is_home_a = (home_id == ss_a)
        result_a = "W" if (is_home_a and hs > as_) or (not is_home_a and as_ > hs) \
                   else ("D" if hs == as_ else "L")

        # 득점 선수 조회 (자책골 제외: 홈팀 득점자만 홈에, 원정팀 득점자만 원정에)
        cur.execute("""
            SELECT mps.team_id,
                   COALESCE(p.name_ko, mps.player_name) as name,
                   SUM(mps.goals) as g
            FROM match_player_stats mps
            LEFT JOIN players p ON mps.player_id = p.id
            WHERE mps.event_id = ? AND mps.goals > 0
            GROUP BY mps.player_id, mps.team_id
            ORDER BY mps.team_id, g DESC
        """, (event_id,))
        scorer_rows = cur.fetchall()

        # 홈팀 득점자는 home_id와 team_id가 일치하는 선수만
        # 원정팀 득점자는 away_id(= not home_id)와 team_id가 일치하는 선수만
        scorers_home = [{"name": r[1], "goals": r[2]} for r in scorer_rows if r[0] == home_id]
        scorers_away = [{"name": r[1], "goals": r[2]} for r in scorer_rows if r[0] == away_id]

        result.append({
            "date": date_str,
            "home": home_name,
            "away": away_name,
            "home_score": hs,
            "away_score": as_,
            "result_a": result_a,
            "is_home_a": is_home_a,
            "scorers_home": scorers_home,
            "scorers_away": scorers_away,
        })

    conn.close()
    return jsonify(result)

@app.route("/api/team-stats")
def get_team_stats():
    team_id = request.args.get("teamId")
    if not os.path.exists(STATS_FILE):
        return jsonify({})
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        stats = json.load(f)
    if team_id:
        return jsonify(stats.get(team_id, {}))
    return jsonify(stats)


@app.route("/api/team-stats-by-year")
def get_team_stats_by_year():
    """연도별 홈/원정 승무패 (match_player_stats DB 기반)"""
    team_id = request.args.get("teamId")
    if not team_id:
        return jsonify({})

    # slug → sofascore_id 변환
    team_info = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team_info:
        return jsonify({})
    ss_id = team_info["sofascore_id"]

    db_path = os.path.join(BASE_DIR, "players.db")
    if not os.path.exists(db_path):
        return jsonify({})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT strftime('%Y', datetime(e.date_ts, 'unixepoch', 'localtime')) as year,
               CASE WHEN e.home_team_id = ? THEN 1 ELSE 0 END as is_home,
               COUNT(CASE WHEN (e.home_team_id=? AND e.home_score > e.away_score)
                            OR (e.away_team_id=? AND e.away_score > e.home_score) THEN 1 END) as w,
               COUNT(CASE WHEN e.home_score = e.away_score THEN 1 END) as d,
               COUNT(CASE WHEN (e.home_team_id=? AND e.home_score < e.away_score)
                            OR (e.away_team_id=? AND e.away_score < e.home_score) THEN 1 END) as l,
               COUNT(*) as games,
               SUM(CASE WHEN e.home_team_id=? THEN e.home_score ELSE e.away_score END) as gf,
               SUM(CASE WHEN e.home_team_id=? THEN e.away_score ELSE e.home_score END) as ga
        FROM events e
        WHERE (e.home_team_id = ? OR e.away_team_id = ?)
          AND e.home_score IS NOT NULL
          AND e.tournament_id = 777
        GROUP BY year, is_home
        ORDER BY year, is_home
    """, (ss_id, ss_id, ss_id, ss_id, ss_id, ss_id, ss_id, ss_id, ss_id))
    rows = cur.fetchall()
    conn.close()

    result = {}
    total = {"home": {"w": 0, "d": 0, "l": 0, "games": 0, "gf": 0, "ga": 0},
             "away": {"w": 0, "d": 0, "l": 0, "games": 0, "gf": 0, "ga": 0}}
    for year, is_home, w, d, l, games, gf, ga in rows:
        if year not in result:
            result[year] = {"home": {}, "away": {}}
        key = "home" if is_home else "away"
        result[year][key] = {"w": w, "d": d, "l": l, "games": games, "gf": gf or 0, "ga": ga or 0}
        total[key]["w"] += w
        total[key]["d"] += d
        total[key]["l"] += l
        total[key]["games"] += games
        total[key]["gf"] += gf or 0
        total[key]["ga"] += ga or 0

    result["전체"] = total
    return jsonify(result)


@app.route("/api/team-ranking")
def get_team_ranking():
    """현재 시즌(최신 연도) 리그 순위 계산"""
    team_id = request.args.get("teamId")
    team_info = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team_info:
        return jsonify({})
    ss_id = team_info["sofascore_id"]

    db_path = os.path.join(BASE_DIR, "players.db")
    if not os.path.exists(db_path):
        return jsonify({})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 최신 연도 확인
    cur.execute("""
        SELECT MAX(strftime('%Y', datetime(date_ts,'unixepoch','localtime')))
        FROM events WHERE tournament_id = 777
    """)
    row = cur.fetchone()
    latest_year = row[0] if row and row[0] else str(datetime.now().year)

    # 해당 연도 전체 경기
    cur.execute("""
        SELECT home_team_id, away_team_id, home_score, away_score
        FROM events
        WHERE tournament_id = 777
          AND home_score IS NOT NULL
          AND strftime('%Y', datetime(date_ts,'unixepoch','localtime')) = ?
    """, (latest_year,))
    rows = cur.fetchall()
    conn.close()

    # 팀별 집계
    standings = {}
    for home_id, away_id, hs, as_ in rows:
        for tid, gf, ga, is_home in [(home_id, hs, as_, True), (away_id, as_, hs, False)]:
            if tid not in standings:
                standings[tid] = {"w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
            s = standings[tid]
            s["gf"] += gf
            s["ga"] += ga
            if gf > ga:
                s["w"] += 1; s["pts"] += 3
            elif gf == ga:
                s["d"] += 1; s["pts"] += 1
            else:
                s["l"] += 1

    # 정렬: 승점 → 득실차 → 득점
    sorted_teams = sorted(standings.items(),
                          key=lambda x: (x[1]["pts"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
                          reverse=True)
    rank = next((i + 1 for i, (tid, _) in enumerate(sorted_teams) if tid == ss_id), None)
    total_teams = len(sorted_teams)
    my = standings.get(ss_id, {})

    return jsonify({
        "rank": rank,
        "total": total_teams,
        "year": latest_year,
        "w": my.get("w", 0),
        "d": my.get("d", 0),
        "l": my.get("l", 0),
        "gf": my.get("gf", 0),
        "ga": my.get("ga", 0),
        "pts": my.get("pts", 0),
    })


@app.route("/api/team-top-players")
def get_team_top_players():
    """현재 시즌 팀 득점/어시스트 TOP 3"""
    team_id = request.args.get("teamId")
    team_info = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team_info:
        return jsonify({})
    ss_id = team_info["sofascore_id"]

    db_path = os.path.join(BASE_DIR, "players.db")
    if not os.path.exists(db_path):
        return jsonify({})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 최신 연도
    cur.execute("""
        SELECT MAX(strftime('%Y', datetime(date_ts,'unixepoch','localtime')))
        FROM events WHERE tournament_id = 777
    """)
    row = cur.fetchone()
    latest_year = row[0] if row and row[0] else str(datetime.now().year)

    _ALLOWED_TOP_STATS = {"goals", "assists"}

    def fetch_top(stat_col, limit=3):
        if stat_col not in _ALLOWED_TOP_STATS:
            raise ValueError(f"disallowed stat column: {stat_col}")
        cur.execute(f"""
            SELECT mps.player_id, mps.player_name,
                   COALESCE(p.name_ko, mps.player_name) as display_name,
                   SUM(mps.{stat_col}) as total
            FROM match_player_stats mps
            JOIN events e ON mps.event_id = e.id
            LEFT JOIN players p ON mps.player_id = p.id
            WHERE mps.team_id = ?
              AND e.tournament_id = 777
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) = ?
              AND mps.{stat_col} > 0
            GROUP BY mps.player_id
            ORDER BY total DESC
            LIMIT ?
        """, (ss_id, latest_year, limit))
        return [{"name": row[2], "val": row[3]} for row in cur.fetchall()]

    scorers = fetch_top("goals")
    assisters = fetch_top("assists")
    conn.close()

    return jsonify({"year": latest_year, "scorers": scorers, "assisters": assisters})


_ENG_TO_KO = {t["sofascore_id"]: t["name"] for t in TEAMS}

def _ko_name_by_ss_id(ss_id):
    """sofascore team id (int 또는 str) → 한국어 팀명"""
    try:
        return _ENG_TO_KO.get(int(ss_id)) or _ENG_TO_KO.get(ss_id)
    except (ValueError, TypeError):
        return _ENG_TO_KO.get(ss_id)


_LEAGUE_TID_BY_KEY = {"K1": 410, "K2": 777}


def _team_league(ss_id):
    """sofascore team id → ('K1'|'K2', tournament_id). 매칭 안 되면 ('K2', 777) 기본."""
    try:
        sid = int(ss_id)
    except (ValueError, TypeError):
        return "K2", 777
    for t in TEAMS:
        if t["sofascore_id"] == sid:
            key = t.get("league", "K2")
            return key, _LEAGUE_TID_BY_KEY.get(key, 777)
    return "K2", 777


@app.route("/api/team-analytics")
def get_team_analytics():
    """팀별 상대팀 승률 / 월별 승률 / 홈어웨이 분석"""
    team_id = request.args.get("teamId")
    year    = request.args.get("year")          # optional filter
    team_info = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team_info:
        return jsonify({}), 404

    ss_id = team_info["sofascore_id"]
    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 사용 가능 연도 목록
    cur.execute("""
        SELECT DISTINCT strftime('%Y', datetime(date_ts,'unixepoch','localtime'))
        FROM events WHERE tournament_id=777
          AND (home_team_id=? OR away_team_id=?)
        ORDER BY 1
    """, (ss_id, ss_id))
    available_years = [r[0] for r in cur.fetchall()]

    year_clause = "AND strftime('%Y', datetime(date_ts,'unixepoch','localtime')) = ?" if year else ""
    yp = (year,) if year else ()

    # 1. 상대팀별 승률 (홈+원정 합산, 팀 ID 포함해 한글명 변환)
    cur.execute("""
        SELECT opp_id, opp_name, SUM(g) games,
               SUM(w) w, SUM(d) d, SUM(l) l,
               SUM(gf) gf, SUM(ga) ga
        FROM (
            SELECT away_team_id opp_id, away_team_name opp_name,
                   COUNT(*) g,
                   SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) l,
                   SUM(home_score) gf, SUM(away_score) ga
            FROM events WHERE tournament_id=777 AND home_team_id=? {yc}
            GROUP BY away_team_id
            UNION ALL
            SELECT home_team_id opp_id, home_team_name opp_name,
                   COUNT(*) g,
                   SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN away_score < home_score THEN 1 ELSE 0 END) l,
                   SUM(away_score) gf, SUM(home_score) ga
            FROM events WHERE tournament_id=777 AND away_team_id=? {yc}
            GROUP BY home_team_id
        )
        GROUP BY opp_id ORDER BY games DESC, w DESC
    """.format(yc=year_clause), (ss_id, *yp, ss_id, *yp))
    vs_rows = cur.fetchall()
    vs_opponents = [
        {"name": _ko_name_by_ss_id(r[0]) or r[1],
         "games": r[2], "w": r[3], "d": r[4], "l": r[5],
         "gf": r[6], "ga": r[7]}
        for r in vs_rows
    ]

    # 2. 월별 승률
    cur.execute("""
        SELECT mon, SUM(g) games, SUM(w) w, SUM(d) d, SUM(l) l, SUM(gf) gf, SUM(ga) ga
        FROM (
            SELECT CAST(strftime('%m', datetime(date_ts,'unixepoch','localtime')) AS INT) mon,
                   COUNT(*) g,
                   SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) l,
                   SUM(home_score) gf, SUM(away_score) ga
            FROM events WHERE tournament_id=777 AND home_team_id=? {yc}
            GROUP BY mon
            UNION ALL
            SELECT CAST(strftime('%m', datetime(date_ts,'unixepoch','localtime')) AS INT) mon,
                   COUNT(*) g,
                   SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN away_score < home_score THEN 1 ELSE 0 END) l,
                   SUM(away_score) gf, SUM(home_score) ga
            FROM events WHERE tournament_id=777 AND away_team_id=? {yc}
            GROUP BY mon
        )
        GROUP BY mon ORDER BY mon
    """.format(yc=year_clause), (ss_id, *yp, ss_id, *yp))
    month_rows = cur.fetchall()
    by_month = [
        {"month": r[0], "games": r[1], "w": r[2], "d": r[3], "l": r[4],
         "gf": r[5], "ga": r[6]}
        for r in month_rows
    ]

    # 3. 홈/어웨이 연도별 승률
    cur.execute("""
        SELECT yr, side, SUM(g) games, SUM(w) w, SUM(d) d, SUM(l) l, SUM(gf) gf, SUM(ga) ga
        FROM (
            SELECT strftime('%Y', datetime(date_ts,'unixepoch','localtime')) yr,
                   'home' side,
                   COUNT(*) g,
                   SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) l,
                   SUM(home_score) gf, SUM(away_score) ga
            FROM events WHERE tournament_id=777 AND home_team_id=? {yc}
            GROUP BY yr
            UNION ALL
            SELECT strftime('%Y', datetime(date_ts,'unixepoch','localtime')) yr,
                   'away' side,
                   COUNT(*) g,
                   SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) d,
                   SUM(CASE WHEN away_score < home_score THEN 1 ELSE 0 END) l,
                   SUM(away_score) gf, SUM(home_score) ga
            FROM events WHERE tournament_id=777 AND away_team_id=? {yc}
            GROUP BY yr
        )
        GROUP BY yr, side ORDER BY yr, side
    """.format(yc=year_clause), (ss_id, *yp, ss_id, *yp))
    ha_rows = cur.fetchall()
    by_year_ha = {}
    for yr, side, g, w, d, l, gf, ga in ha_rows:
        if yr not in by_year_ha:
            by_year_ha[yr] = {}
        by_year_ha[yr][side] = {"games": g, "w": w, "d": d, "l": l, "gf": gf, "ga": ga}

    # 4. 날씨별 승률 (기온 / 습도 / 풍속)
    weather_sql = """
        SELECT
            e.id,
            CASE WHEN mps.team_id = ? THEN
                CASE WHEN (mps.is_home=1 AND e.home_score > e.away_score)
                          OR (mps.is_home=0 AND e.away_score > e.home_score) THEN 'w'
                     WHEN e.home_score = e.away_score THEN 'd'
                     ELSE 'l' END
            END result,
            CASE WHEN mps.is_home=1 THEN e.home_score ELSE e.away_score END gf,
            CASE WHEN mps.is_home=1 THEN e.away_score ELSE e.home_score END ga,
            mps.temperature, mps.humidity, mps.wind_speed
        FROM events e
        JOIN match_player_stats mps ON e.id = mps.event_id
        WHERE e.tournament_id = 777
          AND mps.team_id = ?
          AND mps.temperature IS NOT NULL
          {yc_e}
        GROUP BY e.id
    """.format(yc_e="AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) = ?" if year else "")
    cur.execute(weather_sql, (ss_id, ss_id, *yp))
    w_rows = cur.fetchall()

    def bucket_weather(rows, key_fn, labels):
        buckets = {lbl: {"games":0,"w":0,"d":0,"l":0,"gf":0,"ga":0} for lbl in labels}
        for _, result, gf, ga, temp, hum, wind in rows:
            lbl = key_fn(temp, hum, wind)
            if lbl and result:
                b = buckets[lbl]
                b["games"] += 1
                b[result] += 1
                b["gf"] += gf or 0
                b["ga"] += ga or 0
        return [{"label": k, **v} for k, v in buckets.items() if v["games"] > 0]

    temp_labels  = ["영하~5도","5~15도","15~25도","25도~"]
    hum_labels   = ["건조(<40%)","보통(40~65%)","습함(65%+)"]
    wind_labels  = ["약풍(<3)","중풍(3~7)","강풍(7+)"]

    by_temp = bucket_weather(w_rows,
        lambda t,h,w: "영하~5도" if t<5 else "5~15도" if t<15 else "15~25도" if t<25 else "25도~",
        temp_labels)
    by_hum  = bucket_weather(w_rows,
        lambda t,h,w: "건조(<40%)" if h<40 else "보통(40~65%)" if h<65 else "습함(65%+)",
        hum_labels)
    by_wind = bucket_weather(w_rows,
        lambda t,h,w: "약풍(<3)" if w<3 else "중풍(3~7)" if w<7 else "강풍(7+)",
        wind_labels)

    conn.close()
    return jsonify({
        "team": team_info["name"],
        "available_years": available_years,
        "vs_opponents": vs_opponents,
        "by_month": by_month,
        "by_year_ha": by_year_ha,
        "weather": {
            "by_temp": by_temp,
            "by_hum": by_hum,
            "by_wind": by_wind,
        },
    })


_POISSON_MAX_GOALS = 5  # 스코어 매트릭스 최대 (0~5골)

# 리그별 포아송 모델 상수 (2026 백테스트 그리드 서치로 튜닝)
# - K2: xG 커버 86%, 홈 약간 우위, 무승부 30% → draw_boost 불필요
# - K1: xG 자체 모델(shotmap lookup) 커버 100%, 무승부 37% → draw_boost 0.20
# draw_boost = argmax outcome 결정 시 draw 확률에 더해 줄 오프셋 (0~1 스케일)
_LEAGUE_CONSTANTS = {
    410: {"home_adv": 1.15, "away_adj": 0.90, "draw_boost": 0.20},  # K1 (xG 재튜닝)
    777: {"home_adv": 1.15, "away_adj": 0.90, "draw_boost": 0.00},  # K2
}
_DEFAULT_LEAGUE_CONSTANTS = {"home_adv": 1.15, "away_adj": 0.90, "draw_boost": 0.10}

# 레거시 상수 (기존 코드 호환용, 내부에서는 _LEAGUE_CONSTANTS 사용)
_HOME_ADVANTAGE    = 1.15
_AWAY_ADJUSTMENT   = 0.90
_INJURY_LOSS_CAP   = 0.20  # 부상자로 인한 팀 득점력 감소 최대치


def _league_coefs(tid_filter):
    return _LEAGUE_CONSTANTS.get(tid_filter, _DEFAULT_LEAGUE_CONSTANTS)


def _poisson_pmf(k, lam):
    """Poisson P(X=k) — math.exp/factorial 만 사용, scipy 불필요"""
    import math
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _score_matrix(lam_h, lam_a, max_goals=_POISSON_MAX_GOALS):
    """
    홈/원정 람다로 스코어 매트릭스 반환.
    m[i][j] = P(홈 i골 × 원정 j골).
    마지막 행/열은 max_goals 이상 누적 포함.
    """
    ph = [_poisson_pmf(k, lam_h) for k in range(max_goals + 1)]
    pa = [_poisson_pmf(k, lam_a) for k in range(max_goals + 1)]
    # 꼬리 확률(max_goals+ 이상)을 마지막 칸에 합산
    ph[-1] += max(0.0, 1.0 - sum(ph))
    pa[-1] += max(0.0, 1.0 - sum(pa))
    return [[ph[i] * pa[j] for j in range(max_goals + 1)] for i in range(max_goals + 1)]


def _matrix_outcomes(matrix, draw_boost=0.0):
    """
    스코어 매트릭스 → 홈승/무/원정승 확률 및 상위 5스코어.
    draw_boost: 0~1 스케일 오프셋. draw 확률에 더한 후 재정규화.
        K1처럼 무승부 비율 높은 리그에서 argmax outcome 결정 시 draw 선택 개선.
    """
    home_p = draw_p = away_p = 0.0
    scores = []
    n = len(matrix)
    for i in range(n):
        for j in range(n):
            p = matrix[i][j]
            scores.append({"home": i, "away": j, "prob": p})
            if i > j:
                home_p += p
            elif i == j:
                draw_p += p
            else:
                away_p += p
    draw_p += max(0.0, draw_boost)
    total = home_p + draw_p + away_p or 1
    scores.sort(key=lambda s: s["prob"], reverse=True)
    return {
        "home": round(home_p / total * 100),
        "draw": round(draw_p / total * 100),
        "away": round(away_p / total * 100),
        "top_scores": [
            {"home": s["home"], "away": s["away"], "pct": round(s["prob"] * 100, 1)}
            for s in scores[:5]
        ],
    }


def _all_team_def(cur, tid_filter, year_str, as_of_ts):
    """
    리그 내 모든 팀의 평균 xg_against (경기당 실점 xG) 사전 계산.
    상대 강도(SOS) 보정용. xG 없으면 실제 실점으로 fallback.
    반환: {team_id: avg_xg_against}
    """
    cur.execute("""
        SELECT team_id, AVG(xg_a)
        FROM (
            SELECT e.home_team_id AS team_id,
                   COALESCE((SELECT SUM(mps.expected_goals) FROM match_player_stats mps
                             WHERE mps.event_id=e.id AND mps.team_id=e.away_team_id),
                            e.away_score) AS xg_a
            FROM events e
            WHERE e.tournament_id=? AND e.home_score IS NOT NULL
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
              AND e.date_ts < ?
            UNION ALL
            SELECT e.away_team_id AS team_id,
                   COALESCE((SELECT SUM(mps.expected_goals) FROM match_player_stats mps
                             WHERE mps.event_id=e.id AND mps.team_id=e.home_team_id),
                            e.home_score) AS xg_a
            FROM events e
            WHERE e.tournament_id=? AND e.home_score IS NOT NULL
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
              AND e.date_ts < ?
        )
        GROUP BY team_id
    """, (tid_filter, year_str, as_of_ts, tid_filter, year_str, as_of_ts))
    return {row[0]: float(row[1]) for row in cur.fetchall() if row[1] is not None}


def _team_sos(cur, ss_id, tid_filter, year_str, as_of_ts, team_def_dict, league_def_avg):
    """
    팀이 만난 상대들의 평균 수비력 / 리그 평균 수비력.
    > 1.0: 약한 수비 상대들 만남 (xg_for 부풀림 의심) → 우리 atk를 디스카운트
    < 1.0: 강한 수비 상대들 만남 (xg_for 저평가) → 우리 atk를 부스트
    """
    cur.execute("""
        SELECT CASE WHEN e.home_team_id=? THEN e.away_team_id ELSE e.home_team_id END AS opp_id
        FROM events e
        WHERE e.tournament_id=?
          AND (e.home_team_id=? OR e.away_team_id=?)
          AND e.home_score IS NOT NULL
          AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
          AND e.date_ts < ?
    """, (ss_id, tid_filter, ss_id, ss_id, year_str, as_of_ts))
    opp_defs = []
    for (opp_id,) in cur.fetchall():
        d = team_def_dict.get(opp_id)
        if d is not None:
            opp_defs.append(d)
    if not opp_defs or league_def_avg <= 0:
        return 1.0
    return (sum(opp_defs) / len(opp_defs)) / league_def_avg


def _team_rest_days(cur, tid_filter, ss_id, as_of_ts):
    """팀의 직전 완료 경기로부터의 휴식일. 없으면 None."""
    cur.execute("""
        SELECT date_ts FROM events
        WHERE tournament_id=?
          AND (home_team_id=? OR away_team_id=?)
          AND home_score IS NOT NULL AND date_ts < ?
        ORDER BY date_ts DESC LIMIT 1
    """, (tid_filter, ss_id, ss_id, as_of_ts))
    r = cur.fetchone()
    if not r:
        return None
    return int((as_of_ts - r[0]) / 86400)


def _rest_factor(rest_days):
    """
    휴식일 기반 λ 보정 계수.
    백테스트 분석(K2)에서 rest≤3일 → 홈승률 27.5% (4-7일 36.1% 대비 -8.6pt).
    → 짧은 rest 팀의 공격력을 9% 디스카운트.
    K1은 signal 약하지만 동일 적용 (효과 없으면 무해).
    """
    if rest_days is None:
        return 1.0
    if rest_days <= 3:
        return 0.91  # 피로
    return 1.0


def _predict_core(cur, home_ss, away_ss, tid_filter, as_of_ts, year_str,
                  apply_sos=False, apply_rest=True,
                  home_rest_days=None, away_rest_days=None):
    """
    포아송 기반 핵심 예측 (백테스트/실시간 공통).
    - as_of_ts 직전까지의 데이터만 사용 (look-ahead bias 차단)
    - 부상자 보정은 호출자가 책임 (백테스트는 부상 데이터가 시점성 없으므로 제외)
    - apply_sos: True면 상대 강도(SOS) 보정 적용
    반환: {lam_home, lam_away, pred_home/draw/away, top_scores, h_games, a_games, league_avg, matrix, sos_home, sos_away}
    None 반환: 양 팀 중 한 쪽 사전 경기 0 (cold start)
    """
    cur.execute("""
        SELECT AVG(home_score + away_score) / 2.0
        FROM events
        WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL
          AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
          AND date_ts < ?
    """, (tid_filter, year_str, as_of_ts))
    _r = cur.fetchone()
    league_avg = float(_r[0]) if _r and _r[0] else 1.3

    def _team_xg(ss_id):
        cur.execute("""
            SELECT e.id, e.home_team_id=? AS is_home, e.home_score, e.away_score,
                   (SELECT SUM(mps.expected_goals) FROM match_player_stats mps
                    WHERE mps.event_id=e.id AND mps.team_id=?) AS xg_for,
                   (SELECT SUM(mps.expected_goals) FROM match_player_stats mps
                    WHERE mps.event_id=e.id AND mps.team_id IS NOT NULL
                      AND mps.team_id != ?) AS xg_against
            FROM events e
            WHERE e.tournament_id=?
              AND (e.home_team_id=? OR e.away_team_id=?)
              AND e.home_score IS NOT NULL AND e.away_score IS NOT NULL
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
              AND e.date_ts < ?
        """, (ss_id, ss_id, ss_id, tid_filter, ss_id, ss_id, year_str, as_of_ts))
        sf = sa = 0.0
        n = 0
        for _id, is_home, hs, as_, xg_f, xg_a in cur.fetchall():
            gf = hs if is_home else as_
            ga = as_ if is_home else hs
            sf += float(xg_f) if xg_f is not None else float(gf or 0)
            sa += float(xg_a) if xg_a is not None else float(ga or 0)
            n += 1
        if not n:
            return None
        return {"games": n, "xg_for": sf / n, "xg_against": sa / n}

    h = _team_xg(home_ss)
    a = _team_xg(away_ss)
    if not h or not a:
        return None

    h_atk = (h["xg_for"]     / league_avg) if league_avg else 1.0
    h_def = (h["xg_against"] / league_avg) if league_avg else 1.0
    a_atk = (a["xg_for"]     / league_avg) if league_avg else 1.0
    a_def = (a["xg_against"] / league_avg) if league_avg else 1.0

    # ── 상대 강도(SOS) 보정 ──
    # 양 팀 모두 6경기 이상 + 클램핑(0.88~1.12)으로 노이즈 억제
    sos_home = sos_away = 1.0
    if apply_sos and h["games"] >= 6 and a["games"] >= 6:
        team_def = _all_team_def(cur, tid_filter, year_str, as_of_ts)
        if team_def:
            league_def_avg = sum(team_def.values()) / len(team_def)
            sos_home = _team_sos(cur, home_ss, tid_filter, year_str, as_of_ts, team_def, league_def_avg)
            sos_away = _team_sos(cur, away_ss, tid_filter, year_str, as_of_ts, team_def, league_def_avg)
            sos_home = max(0.88, min(1.12, sos_home))
            sos_away = max(0.88, min(1.12, sos_away))
            h_atk = h_atk / sos_home
            a_atk = a_atk / sos_away

    coefs = _league_coefs(tid_filter)
    lam_h = max(0.1, h_atk * a_def * league_avg * coefs["home_adv"])
    lam_a = max(0.1, a_atk * h_def * league_avg * coefs["away_adj"])

    # 휴식일 보정 (≤3일 연전 시 피로 패널티)
    rest_factor_home = rest_factor_away = 1.0
    if apply_rest:
        rh = home_rest_days if home_rest_days is not None else _team_rest_days(cur, tid_filter, home_ss, as_of_ts)
        ra = away_rest_days if away_rest_days is not None else _team_rest_days(cur, tid_filter, away_ss, as_of_ts)
        rest_factor_home = _rest_factor(rh)
        rest_factor_away = _rest_factor(ra)
        lam_h *= rest_factor_home
        lam_a *= rest_factor_away

    matrix   = _score_matrix(lam_h, lam_a)
    outcomes = _matrix_outcomes(matrix, draw_boost=coefs.get("draw_boost", 0.0))
    return {
        "lam_home":   lam_h,
        "lam_away":   lam_a,
        "pred_home":  outcomes["home"],
        "pred_draw":  outcomes["draw"],
        "pred_away":  outcomes["away"],
        "top_scores": outcomes["top_scores"],
        "h_games":    h["games"],
        "a_games":    a["games"],
        "league_avg": league_avg,
        "matrix":     matrix,
        "sos_home":   round(sos_home, 3),
        "sos_away":   round(sos_away, 3),
        "rest_home":  round(rest_factor_home, 3),
        "rest_away":  round(rest_factor_away, 3),
    }


@app.route("/api/match-prediction")
def get_match_prediction():
    """두 팀 간 예측 보고서: 포아송 승률·스코어 매트릭스·신뢰도·부상자 반영"""
    home_id = request.args.get("homeTeam")
    away_id = request.args.get("awayTeam")
    home_info = next((t for t in TEAMS if t["id"] == home_id), None)
    away_info = next((t for t in TEAMS if t["id"] == away_id), None)
    if not home_info or not away_info:
        return jsonify({}), 404

    hid = home_info["sofascore_id"]
    aid = away_info["sofascore_id"]
    # 리그 구분: K1(410) or K2(777)
    league = home_info.get("league", "K2")
    tid_filter = 410 if league == "K1" else 777

    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    import math, datetime
    now_month = datetime.datetime.now().month
    now_year  = str(datetime.datetime.now().year)

    def compute_standings(year):
        """현재 순위표 계산 (해당 리그 기준)"""
        cur.execute("""
            SELECT home_team_id, away_team_id, home_score, away_score
            FROM events
            WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL
              AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
        """, (tid_filter, year,))
        standing = {}
        for home_id, away_id, hs, as_ in cur.fetchall():
            for tid, gf, ga, is_home in [(home_id, hs, as_, True), (away_id, as_, hs, False)]:
                if tid not in standing:
                    standing[tid] = {"played": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
                s = standing[tid]
                s["played"] += 1
                s["gf"] += gf; s["ga"] += ga
                if gf > ga:
                    s["w"] += 1; s["pts"] += 3
                elif gf == ga:
                    s["d"] += 1; s["pts"] += 1
                else:
                    s["l"] += 1
        # 정렬: pts → gd → gf
        ranked = sorted(standing.items(),
                        key=lambda x: (x[1]["pts"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
                        reverse=True)
        result = {}
        for rank, (tid, s) in enumerate(ranked, 1):
            result[tid] = {**s, "rank": rank, "gd": s["gf"] - s["ga"]}
        return result

    standings = compute_standings(now_year)

    def team_stats(ss_id, side_home):
        """팀 전반 지표 계산"""
        cur.execute("""
            SELECT COUNT(*) g,
                   SUM(CASE WHEN home_score>away_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score=away_score THEN 1 ELSE 0 END) d,
                   SUM(home_score) gf, SUM(away_score) ga
            FROM events WHERE tournament_id=? AND home_team_id=?
              AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
        """, (tid_filter, ss_id, now_year))
        hrow = cur.fetchone()
        cur.execute("""
            SELECT COUNT(*) g,
                   SUM(CASE WHEN away_score>home_score THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN home_score=away_score THEN 1 ELSE 0 END) d,
                   SUM(away_score) gf, SUM(home_score) ga
            FROM events WHERE tournament_id=? AND away_team_id=?
              AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
        """, (tid_filter, ss_id, now_year))
        arow = cur.fetchone()
        hg,hw,hd,hgf,hga = hrow
        ag,aw,ad,agf,aga = arow
        hg  = hg  or 0; hw  = hw  or 0; hd  = hd  or 0; hgf = hgf or 0; hga = hga or 0
        ag  = ag  or 0; aw  = aw  or 0; ad  = ad  or 0; agf = agf or 0; aga = aga or 0
        total_g = hg + ag
        total_w = hw + aw
        home_wr = hw / (hg or 1) * 100
        away_wr = aw / (ag or 1) * 100

        # 최근 5경기 폼
        cur.execute("""
            SELECT home_score, away_score, home_team_id FROM events
            WHERE tournament_id=? AND (home_team_id=? OR away_team_id=?)
            ORDER BY date_ts DESC LIMIT 5
        """, (tid_filter, ss_id, ss_id))
        recent = cur.fetchall()
        form = []
        for hs, as_, ht in recent:
            is_home = ht == ss_id
            gf = hs if is_home else as_
            ga = as_ if is_home else hs
            form.append("W" if gf>ga else "D" if gf==ga else "L")

        # 월별 승률 — 현재 달 기준 과거 데이터
        cur.execute("""
            SELECT SUM(g), SUM(w) FROM (
                SELECT COUNT(*) g, SUM(CASE WHEN home_score>away_score THEN 1 ELSE 0 END) w
                FROM events WHERE tournament_id=? AND home_team_id=?
                  AND CAST(strftime('%m', datetime(date_ts,'unixepoch','localtime')) AS INT)=?
                UNION ALL
                SELECT COUNT(*) g, SUM(CASE WHEN away_score>home_score THEN 1 ELSE 0 END) w
                FROM events WHERE tournament_id=? AND away_team_id=?
                  AND CAST(strftime('%m', datetime(date_ts,'unixepoch','localtime')) AS INT)=?
            )
        """, (tid_filter, ss_id, now_month, tid_filter, ss_id, now_month))
        mr = cur.fetchone()
        month_wr = (mr[1] or 0)/(mr[0] or 1)*100 if (mr and mr[0]) else None

        # 홈/원정 격차
        ha_gap = home_wr - away_wr

        # 득점 top3 (현재 시즌)
        cur.execute("""
            SELECT MAX(strftime('%Y', datetime(date_ts,'unixepoch','localtime')))
            FROM events WHERE tournament_id=?
        """, (tid_filter,))
        _row = cur.fetchone()
        latest_yr = _row[0] if _row and _row[0] else str(datetime.now().year)
        cur.execute("""
            SELECT mps.player_id, COALESCE(p.name_ko, mps.player_name), SUM(mps.goals) g
            FROM match_player_stats mps
            JOIN events e ON mps.event_id=e.id
            LEFT JOIN players p ON mps.player_id=p.id
            WHERE mps.team_id=? AND e.tournament_id=?
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
              AND mps.goals>0
            GROUP BY mps.player_id ORDER BY g DESC LIMIT 3
        """, (ss_id, tid_filter, latest_yr))
        top_scorers = [{"id": r[0], "name": r[1], "goals": r[2]} for r in cur.fetchall()]

        avg_gf = ((hgf or 0)+(agf or 0)) / (total_g or 1)
        avg_ga = ((hga or 0)+(aga or 0)) / (total_g or 1)

        # ── 클린시트 / 무득점 경기 비율
        cur.execute("""
            SELECT
                SUM(CASE WHEN is_home=1 AND away_g=0 THEN 1
                         WHEN is_home=0 AND home_g=0 THEN 1 ELSE 0 END) cs,
                SUM(CASE WHEN is_home=1 AND home_g=0 THEN 1
                         WHEN is_home=0 AND away_g=0 THEN 1 ELSE 0 END) blank,
                COUNT(*) total
            FROM (
                SELECT home_score home_g, away_score away_g, 1 is_home
                FROM events WHERE tournament_id=? AND home_team_id=?
                  AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
                UNION ALL
                SELECT home_score home_g, away_score away_g, 0 is_home
                FROM events WHERE tournament_id=? AND away_team_id=?
                  AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
            )
        """, (tid_filter, ss_id, now_year, tid_filter, ss_id, now_year))
        cs_row = cur.fetchone()
        cs_count  = (cs_row[0] or 0) if cs_row else 0
        blank_cnt = (cs_row[1] or 0) if cs_row else 0
        cs_total  = (cs_row[2] or 0) if cs_row else 0
        clean_sheet_rate = cs_count  / (cs_total or 1) * 100
        blank_rate       = blank_cnt / (cs_total or 1) * 100

        # ── 접전 경기 (1골차) 승/패
        cur.execute("""
            SELECT
                SUM(CASE WHEN gf-ga=1 THEN 1 ELSE 0 END) cw,
                SUM(CASE WHEN ga-gf=1 THEN 1 ELSE 0 END) cl,
                SUM(CASE WHEN ABS(gf-ga)=1 THEN 1 ELSE 0 END) ct
            FROM (
                SELECT home_score gf, away_score ga FROM events
                WHERE tournament_id=? AND home_team_id=?
                  AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
                UNION ALL
                SELECT away_score gf, home_score ga FROM events
                WHERE tournament_id=? AND away_team_id=?
                  AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
            )
        """, (tid_filter, ss_id, now_year, tid_filter, ss_id, now_year))
        cl_row = cur.fetchone()
        close_win   = (cl_row[0] or 0) if cl_row else 0
        close_loss  = (cl_row[1] or 0) if cl_row else 0
        close_total = (cl_row[2] or 0) if cl_row else 0
        close_wr = close_win / (close_total or 1) * 100

        # ── 대량 득점 (3골+) 빈도
        cur.execute("""
            SELECT SUM(CASE WHEN gf>=3 THEN 1 ELSE 0 END), COUNT(*) FROM (
                SELECT home_score gf FROM events
                WHERE tournament_id=? AND home_team_id=?
                  AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
                UNION ALL
                SELECT away_score gf FROM events
                WHERE tournament_id=? AND away_team_id=?
                  AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
            )
        """, (tid_filter, ss_id, now_year, tid_filter, ss_id, now_year))
        bs_row = cur.fetchone()
        big_score_rate = (bs_row[0] or 0) / (bs_row[1] or 1) * 100 if bs_row else 0

        # ── xG 효율 (match_player_stats)
        cur.execute("""
            SELECT SUM(mps.goals), SUM(mps.expected_goals)
            FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
            WHERE mps.team_id=? AND e.tournament_id=?
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
        """, (ss_id, tid_filter, latest_yr))
        xg_row = cur.fetchone()
        xg_actual = (xg_row[0] or 0) if xg_row else 0
        xg_sum_val = (xg_row[1] or 0) if xg_row else 0
        xg_efficiency = (xg_actual / xg_sum_val) if xg_sum_val >= 3 else None

        # ── 연속 기록 (최근 15경기 기준)
        cur.execute("""
            SELECT home_score, away_score, home_team_id FROM events
            WHERE tournament_id=? AND (home_team_id=? OR away_team_id=?)
            ORDER BY date_ts DESC LIMIT 15
        """, (tid_filter, ss_id, ss_id))
        streak_rows = cur.fetchall()
        streak_res = []
        for hs, as_, ht in streak_rows:
            ih = ht == ss_id
            gf_s = hs if ih else as_
            ga_s = as_ if ih else hs
            streak_res.append("W" if gf_s > ga_s else "D" if gf_s == ga_s else "L")
        win_streak = sum(1 for _ in __import__("itertools").takewhile(lambda r: r=="W",  streak_res))
        unbeat_streak = sum(1 for _ in __import__("itertools").takewhile(lambda r: r!="L", streak_res))
        loss_streak = sum(1 for _ in __import__("itertools").takewhile(lambda r: r=="L",  streak_res))

        # ── 최근 5경기 득점 추세 vs 시즌 평균
        recent5_gf = sum(
            (hs if ht==ss_id else as_)
            for hs, as_, ht in streak_rows[:5]
        )
        recent5_avg = recent5_gf / min(5, len(streak_rows)) if streak_rows else avg_gf

        # ── 득점 의존도 (top scorer 기여율)
        total_team_goals = (hgf or 0) + (agf or 0)
        scorer_dep = None
        if top_scorers and total_team_goals >= 5:
            scorer_dep = top_scorers[0]["goals"] / total_team_goals * 100

        # ── 유의사항 도출 ──
        notes = []

        # 연승/무패/연패 스트릭
        if win_streak >= 4:
            notes.append(f"현재 {win_streak}연승 행진 중")
        elif win_streak >= 3:
            notes.append(f"최근 {win_streak}연승")
        elif unbeat_streak >= 6:
            notes.append(f"최근 {unbeat_streak}경기 무패")
        if loss_streak >= 3:
            notes.append(f"현재 {loss_streak}연패 위기")
        elif form.count("L") >= 3 and loss_streak < 3:
            notes.append("최근 5경기 부진")

        # 홈/원정 강세
        if ha_gap > 20:
            notes.append(f"홈에서 특히 강함 (홈승률 {home_wr:.0f}% vs 원정 {away_wr:.0f}%)")
        elif ha_gap < -10:
            notes.append(f"원정이 오히려 강함 (원정승률 {away_wr:.0f}% vs 홈 {home_wr:.0f}%)")

        # 월별 강/약세
        if month_wr is not None:
            mn = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"][now_month-1]
            if month_wr >= 60:
                notes.append(f"{mn} 절정 (역대 {mn} 승률 {month_wr:.0f}%)")
            elif month_wr >= 50:
                notes.append(f"{mn} 강세 (역대 {mn} 승률 {month_wr:.0f}%)")
            elif month_wr <= 20:
                notes.append(f"{mn} 징크스 (역대 {mn} 승률 {month_wr:.0f}%)")
            elif month_wr <= 33:
                notes.append(f"{mn} 약세 (역대 {mn} 승률 {month_wr:.0f}%)")

        # 클린시트 / 수비력
        if clean_sheet_rate >= 50:
            notes.append(f"수비 철벽 (무실점률 {clean_sheet_rate:.0f}%)")
        elif clean_sheet_rate >= 35:
            notes.append(f"수비 견고 (무실점률 {clean_sheet_rate:.0f}%)")

        # 무득점 경기
        if blank_rate >= 40:
            notes.append(f"득점력 불안 (무득점 경기 {blank_rate:.0f}%)")
        elif blank_rate >= 30:
            notes.append(f"간헐적 득점 침묵 ({blank_rate:.0f}%)")

        # 접전 강/약
        if close_total >= 3:
            if close_wr >= 67:
                notes.append(f"접전에서 강함 (1골차 승률 {close_wr:.0f}%)")
            elif close_wr <= 30:
                notes.append(f"접전에서 약함 (1골차 승률 {close_wr:.0f}%)")

        # 대량 득점 폭발력
        if big_score_rate >= 40:
            notes.append(f"폭발적 공격력 (3골+ 경기 {big_score_rate:.0f}%)")

        # xG 효율
        if xg_efficiency is not None:
            if xg_efficiency >= 1.3:
                notes.append(f"결정력 탁월 (xG 대비 +{(xg_efficiency-1)*100:.0f}% 득점)")
            elif xg_efficiency <= 0.7:
                notes.append(f"결정력 부족 (xG 대비 -{(1-xg_efficiency)*100:.0f}% 손실)")

        # 득점력/실점 기본
        if avg_gf >= 2.0:
            notes.append(f"고득점 팀 (경기당 {avg_gf:.1f}골)")
        elif avg_gf >= 1.6:
            notes.append(f"공격적 (경기당 {avg_gf:.1f}골)")
        if avg_ga >= 2.0:
            notes.append(f"실점 다발 (경기당 {avg_ga:.1f}실점)")
        elif avg_ga >= 1.6:
            notes.append(f"수비 취약 (경기당 {avg_ga:.1f}실점)")

        # 득점 의존도
        if scorer_dep is not None and scorer_dep >= 50:
            notes.append(f"{top_scorers[0]['name']} 원톱 의존 ({scorer_dep:.0f}%)")

        # 최근 득점 추세
        if len(streak_rows) >= 3 and avg_gf > 0:
            if recent5_avg >= avg_gf * 1.4:
                notes.append(f"최근 공격력 급상승 (최근 {recent5_avg:.1f} vs 시즌 {avg_gf:.1f})")
            elif recent5_avg <= avg_gf * 0.55:
                notes.append(f"최근 득점 침체 (최근 {recent5_avg:.1f} vs 시즌 {avg_gf:.1f})")

        return {
            "total_games": total_g,
            "win_rate": total_w/(total_g or 1)*100,
            "home_wr": home_wr,
            "away_wr": away_wr,
            "form": form,
            "month_wr": month_wr,
            "notes": notes,
            "top_scorers": top_scorers,
            "avg_gf": avg_gf,
            "avg_ga": avg_ga,
            "standing": standings.get(ss_id),
        }

    # H2H 직접 전적
    cur.execute("""
        SELECT COUNT(*) g,
               SUM(CASE WHEN home_team_id=? THEN
                     CASE WHEN home_score>away_score THEN 1 ELSE 0 END
                   ELSE
                     CASE WHEN away_score>home_score THEN 1 ELSE 0 END
                   END) w,
               SUM(CASE WHEN home_score=away_score THEN 1 ELSE 0 END) d
        FROM events WHERE tournament_id=?
          AND ((home_team_id=? AND away_team_id=?) OR (home_team_id=? AND away_team_id=?))
    """, (tid_filter, hid, hid, aid, aid, hid))
    h2h = cur.fetchone()
    h2h_g, h2h_w, h2h_d = h2h
    h2h_l = (h2h_g or 0) - (h2h_w or 0) - (h2h_d or 0)

    home_stats = team_stats(hid, True)
    away_stats = team_stats(aid, False)

    # ──────────────────────────────────────────────────────────────
    # 포아송 기반 예측 (v2)
    # ──────────────────────────────────────────────────────────────

    def team_xg_avg(ss_id):
        """팀의 경기당 xG(for/against) — xG null 경기는 실제 득실로 fallback"""
        cur.execute("""
            SELECT e.id,
                   e.home_team_id=? AS is_home,
                   e.home_score, e.away_score,
                   (SELECT SUM(mps.expected_goals) FROM match_player_stats mps
                    WHERE mps.event_id=e.id AND mps.team_id=?) AS xg_for,
                   (SELECT SUM(mps.expected_goals) FROM match_player_stats mps
                    WHERE mps.event_id=e.id AND mps.team_id IS NOT NULL
                      AND mps.team_id != ?) AS xg_against
            FROM events e
            WHERE e.tournament_id=?
              AND (e.home_team_id=? OR e.away_team_id=?)
              AND e.home_score IS NOT NULL AND e.away_score IS NOT NULL
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
        """, (ss_id, ss_id, ss_id, tid_filter, ss_id, ss_id, now_year))
        xg_for_sum = xg_ag_sum = 0.0
        games = 0
        for _id, is_home, hs, as_, xg_f, xg_a in cur.fetchall():
            gf = hs if is_home else as_
            ga = as_ if is_home else hs
            # xG 없으면 실제 득실로 fallback
            xg_for_sum += float(xg_f) if xg_f is not None else float(gf or 0)
            xg_ag_sum  += float(xg_a) if xg_a is not None else float(ga or 0)
            games += 1
        if not games:
            return {"games": 0, "xg_for": 1.3, "xg_against": 1.3}
        return {
            "games": games,
            "xg_for": xg_for_sum / games,
            "xg_against": xg_ag_sum / games,
        }

    home_xg = team_xg_avg(hid)
    away_xg = team_xg_avg(aid)

    # 리그 평균 팀당 득점(= 경기당 총득점 / 2) — 공격/수비 계수 정규화용
    cur.execute("""
        SELECT AVG(home_score + away_score) / 2.0
        FROM events
        WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL
          AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
    """, (tid_filter, now_year))
    _row = cur.fetchone()
    league_avg = float(_row[0]) if _row and _row[0] else 1.3

    # 공격/수비 레이팅 (1.0 = 리그 평균)
    h_atk = (home_xg["xg_for"]    / league_avg) if league_avg else 1.0
    h_def = (home_xg["xg_against"] / league_avg) if league_avg else 1.0
    a_atk = (away_xg["xg_for"]    / league_avg) if league_avg else 1.0
    a_def = (away_xg["xg_against"] / league_avg) if league_avg else 1.0

    # 부상자 영향: 해당 팀 부상 선수들의 시즌 xG/골 합 → 공격력 감소
    def injury_impact(ss_id, app_team_id):
        """부상 선수들의 시즌 득점 기여분을 팀 공격력에서 차감 (max 20%)"""
        try:
            status_path = os.path.join(BASE_DIR, "data", "player_status.json")
            if not os.path.exists(status_path):
                return {"players": [], "xg_loss_pct": 0.0}
            with open(status_path, "r", encoding="utf-8") as f:
                statuses = json.load(f)
        except Exception:
            return {"players": [], "xg_loss_pct": 0.0}

        # 해당 팀의 결장 예정(부상/정지/의문) 선수만
        out_entries = [
            s for s in statuses.values()
            if s.get("teamId") == app_team_id
            and s.get("status") in ("injured", "suspended", "doubtful")
        ]
        if not out_entries:
            return {"players": [], "xg_loss_pct": 0.0}

        # 시즌 팀 총 xG(=attack 분모)
        team_season_xg = home_xg["xg_for"] if ss_id == hid else away_xg["xg_for"]
        team_games     = home_xg["games"]  if ss_id == hid else away_xg["games"]
        team_total_xg  = team_season_xg * team_games or 1.0

        impacted = []
        total_lost_xg = 0.0
        for s in out_entries:
            pid = s.get("playerId")
            if not pid:
                continue
            try:
                pid_int = int(pid)
            except (ValueError, TypeError):
                continue
            cur.execute("""
                SELECT COALESCE(SUM(mps.expected_goals), 0), COALESCE(SUM(mps.goals), 0),
                       COALESCE(SUM(mps.assists), 0), COUNT(*)
                FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
                WHERE mps.player_id=? AND e.tournament_id=?
                  AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
            """, (pid_int, tid_filter, now_year))
            r = cur.fetchone()
            xg, g, a, gms = (float(r[0] or 0), r[1] or 0, r[2] or 0, r[3] or 0) if r else (0, 0, 0, 0)
            # xG 데이터 없으면 실제 골로 대체
            lost = xg if xg > 0 else float(g)
            if lost <= 0 and gms == 0:
                continue
            total_lost_xg += lost
            impacted.append({
                "name": s.get("name", ""),
                "status": s.get("status"),
                "goals": int(g),
                "assists": int(a),
                "xg": round(xg, 2),
                "return_date": s.get("returnDate", ""),
            })

        loss_pct = min(_INJURY_LOSS_CAP, total_lost_xg / team_total_xg) if team_total_xg else 0.0
        return {
            "players": impacted,
            "xg_loss_pct": round(loss_pct * 100, 1),
            "xg_loss_ratio": loss_pct,
        }

    home_inj = injury_impact(hid, home_id)
    away_inj = injury_impact(aid, away_id)

    # 부상 반영된 공격 계수
    h_atk_adj = h_atk * (1.0 - home_inj.get("xg_loss_ratio", 0.0))
    a_atk_adj = a_atk * (1.0 - away_inj.get("xg_loss_ratio", 0.0))

    # 최종 람다
    _coefs   = _league_coefs(tid_filter)
    lam_home = max(0.1, h_atk_adj * a_def * league_avg * _coefs["home_adv"])
    lam_away = max(0.1, a_atk_adj * h_def * league_avg * _coefs["away_adj"])

    matrix     = _score_matrix(lam_home, lam_away)
    outcomes   = _matrix_outcomes(matrix, draw_boost=_coefs.get("draw_boost", 0.0))
    pred_home  = outcomes["home"]
    pred_draw  = outcomes["draw"]
    pred_away  = outcomes["away"]
    top_scores = outcomes["top_scores"]

    # 스코어 매트릭스 소수점 정리 (% 단위)
    score_matrix_pct = [[round(matrix[i][j] * 100, 1) for j in range(len(matrix))] for i in range(len(matrix))]

    # ──────────────────────────────────────────────────────────────
    # 신뢰도 배지
    # ──────────────────────────────────────────────────────────────
    h2h_games_cnt = h2h_g or 0
    season_games  = min(home_xg["games"], away_xg["games"])
    if h2h_games_cnt >= 5 and season_games >= 6:
        conf_level = "high"
    elif h2h_games_cnt >= 3 or season_games >= 4:
        conf_level = "med"
    else:
        conf_level = "low"

    # ──────────────────────────────────────────────────────────────
    # 최근 10경기 승점 이동(트렌드 라인용)
    # ──────────────────────────────────────────────────────────────
    def form_points(ss_id):
        cur.execute("""
            SELECT home_score, away_score, home_team_id, date_ts FROM events
            WHERE tournament_id=? AND (home_team_id=? OR away_team_id=?)
              AND home_score IS NOT NULL AND away_score IS NOT NULL
            ORDER BY date_ts DESC LIMIT 10
        """, (tid_filter, ss_id, ss_id))
        rows = list(reversed(cur.fetchall()))  # 과거→최근
        pts = []
        for hs, as_, ht, _dt in rows:
            is_home = ht == ss_id
            gf = hs if is_home else as_
            ga = as_ if is_home else hs
            pts.append(3 if gf > ga else 1 if gf == ga else 0)
        return pts

    home_form_pts = form_points(hid)
    away_form_pts = form_points(aid)

    # ──────────────────────────────────────────────────────────────
    # 골 타이밍 (시간대별 득점/실점) — 전후반 미니 차트용
    # ──────────────────────────────────────────────────────────────
    def goal_timing(ss_id):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='goal_events'")
        if not cur.fetchone():
            return {"for": [0, 0], "against": [0, 0]}
        # 전반(1-45+) vs 후반(46-90+)
        cur.execute("""
            SELECT SUM(CASE WHEN (g.minute + COALESCE(g.added_time,0)) <= 45 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN (g.minute + COALESCE(g.added_time,0)) > 45 THEN 1 ELSE 0 END)
            FROM goal_events g JOIN events e ON g.event_id=e.id
            WHERE e.tournament_id=? AND g.team_id=?
              AND (e.home_team_id=? OR e.away_team_id=?)
        """, (tid_filter, ss_id, ss_id, ss_id))
        _f = cur.fetchone()
        cur.execute("""
            SELECT SUM(CASE WHEN (g.minute + COALESCE(g.added_time,0)) <= 45 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN (g.minute + COALESCE(g.added_time,0)) > 45 THEN 1 ELSE 0 END)
            FROM goal_events g JOIN events e ON g.event_id=e.id
            WHERE e.tournament_id=? AND g.team_id!=?
              AND (e.home_team_id=? OR e.away_team_id=?)
        """, (tid_filter, ss_id, ss_id, ss_id))
        _a = cur.fetchone()
        return {
            "for":     [int(_f[0] or 0), int(_f[1] or 0)] if _f else [0, 0],
            "against": [int(_a[0] or 0), int(_a[1] or 0)] if _a else [0, 0],
        }

    home_timing = goal_timing(hid)
    away_timing = goal_timing(aid)

    # ──────────────────────────────────────────────────────────────
    # 세트피스 분석 (fromSetPiece + penalty = 세트피스, regular = 오픈플레이, ownGoal = 별도)
    # ──────────────────────────────────────────────────────────────
    def setpiece_analysis(ss_id):
        # 득점
        cur.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN g.goal_type IN ('fromSetPiece','penalty') THEN 1 ELSE 0 END),
                   SUM(CASE WHEN g.goal_type='penalty' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN g.goal_type='fromSetPiece' THEN 1 ELSE 0 END)
            FROM goal_events g JOIN events e ON g.event_id=e.id
            WHERE e.tournament_id=? AND g.team_id=?
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
        """, (tid_filter, ss_id, now_year))
        r = cur.fetchone() or (0, 0, 0, 0)
        total, sp, pk, fk = (r[0] or 0), (r[1] or 0), (r[2] or 0), (r[3] or 0)

        # 실점 (상대가 우리 경기에서 넣은 골 중 세트피스)
        cur.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN g.goal_type IN ('fromSetPiece','penalty') THEN 1 ELSE 0 END)
            FROM goal_events g JOIN events e ON g.event_id=e.id
            WHERE e.tournament_id=? AND g.team_id != ?
              AND (e.home_team_id=? OR e.away_team_id=?)
              AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?
        """, (tid_filter, ss_id, ss_id, ss_id, now_year))
        r2 = cur.fetchone() or (0, 0)
        conc_total, conc_sp = (r2[0] or 0), (r2[1] or 0)

        return {
            "goals_total":          total,
            "setpiece_goals":       sp,
            "setpiece_pct":         round(sp/total*100, 1) if total else None,
            "penalty_goals":        pk,
            "freekick_goals":       fk,
            "conceded_total":       conc_total,
            "setpiece_conceded":    conc_sp,
            "setpiece_conceded_pct": round(conc_sp/conc_total*100, 1) if conc_total else None,
        }

    home_sp = setpiece_analysis(hid)
    away_sp = setpiece_analysis(aid)

    # 휴식일 (현재 시각 기준 직전 경기로부터 일수)
    import time as _time
    _now_ts = int(_time.time())
    home_rest = _team_rest_days(cur, tid_filter, hid, _now_ts)
    away_rest = _team_rest_days(cur, tid_filter, aid, _now_ts)

    # ──────────────────────────────────────────────────────────────
    # 심판 정보 (K1 한정, K2는 원천 부재)
    # 양팀 마지막 경기에서 심판을 추정. 실제 매치업 심판은 사전에 발표돼야 알 수 있음.
    # ──────────────────────────────────────────────────────────────
    referee_info = None
    if tid_filter == 410:  # K1
        cur.execute("""
            SELECT r.id, r.name, r.career_games, r.career_yellow, r.career_red, r.career_yellow_red
            FROM referees r
            WHERE r.id IN (
                SELECT e.referee_id FROM events e
                WHERE e.tournament_id=? AND e.referee_id IS NOT NULL
                  AND ((e.home_team_id IN (?,?)) OR (e.away_team_id IN (?,?)))
                ORDER BY e.date_ts DESC LIMIT 1
            )
        """, (tid_filter, hid, aid, hid, aid))
        rrow = cur.fetchone()
        if rrow:
            rid, rname, rgames, ry, rr, ryr = rrow
            referee_info = {
                "id":              rid,
                "name":            rname,
                "career_games":    rgames or 0,
                "yellow_per_game": round((ry or 0)/(rgames or 1), 2) if rgames else None,
                "red_per_game":    round((rr or 0)/(rgames or 1), 3) if rgames else None,
                "strictness":      ("엄격" if ((ry or 0)/(rgames or 1) > 3.5) else
                                    "관대" if ((ry or 0)/(rgames or 1) < 2.5) else "보통") if rgames else None,
                "note":            "최근 양팀 경기 심판 — 실제 매치업 심판은 KFA 발표 후 확정",
            }

    conn.close()
    return jsonify({
        "home": {"id": home_id, "name": home_info["name"], **home_stats,
                 "form_points": home_form_pts, "goal_timing": home_timing,
                 "setpiece": home_sp, "rest_days": home_rest,
                 "xg_for": round(home_xg["xg_for"], 2), "xg_against": round(home_xg["xg_against"], 2)},
        "away": {"id": away_id, "name": away_info["name"], **away_stats,
                 "form_points": away_form_pts, "goal_timing": away_timing,
                 "setpiece": away_sp, "rest_days": away_rest,
                 "xg_for": round(away_xg["xg_for"], 2), "xg_against": round(away_xg["xg_against"], 2)},
        "h2h": {"games": h2h_g or 0, "home_w": h2h_w or 0, "draw": h2h_d or 0, "away_w": h2h_l},
        "prediction": {"home": pred_home, "draw": pred_draw, "away": pred_away},
        "poisson": {
            "lambda_home": round(lam_home, 2),
            "lambda_away": round(lam_away, 2),
            "league_avg":  round(league_avg, 2),
        },
        "score_matrix": score_matrix_pct,
        "top_scores":   top_scores,
        "confidence": {
            "level": conf_level,
            "h2h_games": h2h_games_cnt,
            "season_games": season_games,
        },
        "injuries": {
            "home": home_inj,
            "away": away_inj,
        },
        "referee": referee_info,
    })


KLEAGUE_CODE_MAP = {
    "K01": "ulsan",  "K02": "suwon",    "K03": "pohang",  "K04": "jeju",
    "K05": "jeonbuk","K06": "busan",    "K07": "jeonnam", "K08": "seongnam",
    "K09": "fcseoul","K10": "daejeon",  "K17": "daegu",   "K18": "incheon",
    "K20": "gyeongnam","K21": "gangwon","K22": "gwangju", "K26": "bucheon",
    "K27": "anyang", "K29": "suwon_fc", "K31": "seouland","K32": "ansan",
    "K34": "asan",   "K35": "gimcheon", "K36": "gimpo",   "K37": "cheongju",
    "K38": "cheonan","K39": "hwaseong", "K40": "paju",    "K41": "gimhae",
    "K42": "yongin",
}
TEAMS_BY_ID = {t["id"]: t for t in TEAMS}

@app.route("/api/standings")
def get_standings():
    try:
        req = urllib.request.Request(
            "https://www.kleague.com/api/clubRank.do",
            data=b"{}",
            headers={"Content-Type": "application/json; charset=UTF-8",
                     "Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            raw_data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    result = {}
    for league_key in ("league1", "league2"):
        rows = raw_data.get("data", {}).get(league_key, [])
        cleaned = []
        for row in rows:
            team_code = row.get("teamId", "")
            internal_id = KLEAGUE_CODE_MAP.get(team_code)
            team_info = TEAMS_BY_ID.get(internal_id, {}) if internal_id else {}
            recent = []
            for i in range(1, 7):
                g = row.get(f"game0{i}", "").strip()
                if g:
                    recent.append(g)
            cleaned.append({
                "rank":    row.get("rank"),
                "teamId":  internal_id or team_code,
                "name":    team_info.get("name", team_code),
                "short":   team_info.get("short", team_code),
                "emblem":  team_info.get("emblem", ""),
                "primary": team_info.get("primary", "#333"),
                "games":   row.get("gameCount", 0),
                "w":       row.get("winCnt", 0),
                "d":       row.get("tieCnt", 0),
                "l":       row.get("lossCnt", 0),
                "gf":      row.get("gainGoal", 0),
                "ga":      row.get("lossGoal", 0),
                "gd":      row.get("gapCnt", 0),
                "pts":     row.get("gainPoint", 0),
                "recent":  recent,
            })
        result[league_key] = cleaned
    return jsonify(result)


# ── DB 설정 + 인덱스 ────────────────────────────────────
DB_PATH = os.path.join(BASE_DIR, "players.db")

def _ensure_indexes():
    """자주 쿼리되는 컬럼에 인덱스를 생성한다 (이미 있으면 무시)."""
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_events_tournament ON events(tournament_id)",
        "CREATE INDEX IF NOT EXISTS idx_events_date ON events(date_ts)",
        "CREATE INDEX IF NOT EXISTS idx_mps_position ON match_player_stats(position)",
        "CREATE INDEX IF NOT EXISTS idx_mps_team_player ON match_player_stats(team_id, player_id)",
        "CREATE INDEX IF NOT EXISTS idx_mps_match_date ON match_player_stats(match_date)",
        "CREATE INDEX IF NOT EXISTS idx_heatmap_player_event ON heatmap_points(player_id, event_id)",
        "CREATE INDEX IF NOT EXISTS idx_players_name_ko ON players(name_ko)",
        "CREATE INDEX IF NOT EXISTS idx_goal_events_player ON goal_events(player_id)",
    ]
    for sql in indexes:
        try:
            conn.execute(sql)
        except Exception:
            pass  # 테이블이 아직 없을 수 있음
    conn.commit()
    conn.close()

_ensure_indexes()

# ── 히트맵 API ───────────────────────────────────────────

# sofascore_id → 한글 팀명 매핑
_SS_TO_KO = {t["sofascore_id"]: t["name"] for t in TEAMS}

def _ko_team(sofascore_id, fallback):
    return _SS_TO_KO.get(sofascore_id, fallback)

def _year_range(year_str):
    """연도 문자열 → (start_ts, end_ts) UTC 기준"""
    y = int(year_str)
    start = int(datetime(y,   1, 1).timestamp())
    end   = int(datetime(y+1, 1, 1).timestamp())
    return start, end

def _find_player(cur, name):
    """(player_id, team_id, matched_name) 반환, 없으면 (None, None, None)"""
    cur.execute("SELECT id, team_id, name_ko, name FROM players WHERE name_ko = ?", (name,))
    row = cur.fetchone()
    if not row:
        # 공백 제거 후 재시도 (예: '브루노 실바' vs '브루노실바')
        name_no_space = name.replace(" ", "")
        cur.execute("SELECT id, team_id, name_ko, name FROM players WHERE REPLACE(name_ko, ' ', '') = ?", (name_no_space,))
        row = cur.fetchone()
    if not row:
        cur.execute("SELECT id, team_id, name_ko, name FROM players WHERE name LIKE ?", (f"%{name}%",))
        row = cur.fetchone()
    if not row:
        return (None, None, None)
    matched = row["name_ko"] or row["name"]
    return (row["id"], row["team_id"], matched)

def _flip_points(rows, player_team_id):
    """away 경기 포인트를 x축 반전 (x→100-x)"""
    result = []
    for r in rows:
        if r["away_team_id"] == player_team_id:
            result.append({"x": 100 - r["x"], "y": r["y"]})
        else:
            result.append({"x": r["x"], "y": r["y"]})
    return result

CURRENT_YEAR = str(datetime.now().year)

@app.route("/api/heatmap")
def get_heatmap():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify({"points": []})
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    player_id, player_team_id, matched_name = _find_player(cur, name)
    if not player_id:
        conn.close()
        return jsonify({"points": [], "found": False})

    event_id    = request.args.get("eventId", "").strip()
    opponent_id = request.args.get("opponentId", "").strip()
    year        = request.args.get("year", CURRENT_YEAR).strip()
    year_start, year_end = _year_range(year)

    # 특정 경기 히트맵 → AWAY면 API에서 flip
    if event_id:
        cur.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            LEFT JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ? AND h.event_id = ?
        """, (player_id, event_id))
        points = _flip_points(cur.fetchall(), player_team_id)
        conn.close()
        return jsonify({"points": points, "found": True, "playerId": player_id,
                        "filtered": True, "matchedName": matched_name})

    # 누적 히트맵 — AWAY 경기도 flip 정규화 (Sofascore와 동일하게)
    if opponent_id:
        cur.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ?
              AND (e.home_team_id = ? OR e.away_team_id = ?)
              AND e.date_ts >= ? AND e.date_ts < ?
        """, (player_id, opponent_id, opponent_id, year_start, year_end))
    else:
        cur.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            LEFT JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ?
              AND (e.date_ts IS NULL OR (e.date_ts >= ? AND e.date_ts < ?))
        """, (player_id, year_start, year_end))

    points = _flip_points(cur.fetchall(), player_team_id)
    conn.close()
    return jsonify({"points": points, "found": True, "playerId": player_id,
                    "filtered": bool(opponent_id), "matchedName": matched_name})

@app.route("/api/player-matches")
def get_player_matches():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify({"matches": []})
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    player_id, player_team_id, matched_name = _find_player(cur, name)
    if not player_id:
        conn.close()
        return jsonify({"matches": [], "found": False})

    year = request.args.get("year", "all").strip()

    if year == "all":
        cur.execute("""
            SELECT DISTINCT e.id, e.home_team_id, e.home_team_name,
                            e.away_team_id, e.away_team_name,
                            e.home_score, e.away_score, e.date_ts
            FROM heatmap_points h
            JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ? AND e.date_ts IS NOT NULL
            ORDER BY e.date_ts DESC
        """, (player_id,))
    else:
        ys, ye = _year_range(year)
        cur.execute("""
            SELECT DISTINCT e.id, e.home_team_id, e.home_team_name,
                            e.away_team_id, e.away_team_name,
                            e.home_score, e.away_score, e.date_ts
            FROM heatmap_points h
            JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ? AND e.date_ts >= ? AND e.date_ts < ?
            ORDER BY e.date_ts DESC
        """, (player_id, ys, ye))

    matches = []
    for r in cur.fetchall():
        matches.append({
            "id":        r["id"],
            "home":      _ko_team(r["home_team_id"], r["home_team_name"]),
            "away":      _ko_team(r["away_team_id"], r["away_team_name"]),
            "homeScore": r["home_score"],
            "awayScore": r["away_score"],
            "datets":    r["date_ts"],
            "isAway":    r["away_team_id"] == player_team_id,
        })
    conn.close()
    return jsonify({"matches": matches, "found": True, "playerId": player_id})


@app.route("/api/player-stat-report")
def get_player_stat_report():
    """선수 상세 스탯 보고서 - 포지션 대비 퍼센타일 포함"""
    import datetime as _dt
    name      = request.args.get("name", "").strip()
    player_id = request.args.get("playerId", type=int)
    year      = request.args.get("year")

    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 선수 찾기
    if player_id:
        cur.execute("SELECT id, team_id, name_ko, name FROM players WHERE id=?", (player_id,))
        row = cur.fetchone()
        if row:
            pid, team_id_db = row["id"], row["team_id"]
            matched = row["name_ko"] or row["name"]
        else:
            pid, team_id_db, matched = None, None, None
    else:
        pid, team_id_db, matched = _find_player(cur, name)

    if not pid:
        conn.close()
        return jsonify({"found": False}), 404

    year_clause = "AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?" if year else ""
    yp = (year,) if year else ()

    # 선수 기본 정보
    cur.execute("SELECT * FROM players WHERE id=?", (pid,))
    prow = cur.fetchone()
    pos_raw = None
    height  = prow["height"] if prow else None

    # 출전 포지션 (mps에서 최빈값)
    cur.execute(f"""
        SELECT mps.position, COUNT(*) cnt
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 {year_clause}
        GROUP BY mps.position ORDER BY cnt DESC LIMIT 1
    """, (pid,) + yp)
    pr = cur.fetchone()
    pos_raw = pr[0] if pr else (prow["position"] if prow else "?")

    # 사용 가능 연도
    cur.execute("""
        SELECT DISTINCT strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) yr
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 ORDER BY yr
    """, (pid,))
    available_years = [r[0] for r in cur.fetchall()]

    # 대상 선수 집계 (90분 환산)
    cur.execute(f"""
        SELECT COUNT(*) games,
               SUM(mps.minutes_played) mins,
               SUM(mps.goals) goals, SUM(mps.assists) assists,
               SUM(mps.total_shots) shots, SUM(mps.shots_on_target) sot,
               AVG(mps.expected_goals) xg_avg,
               AVG(mps.accurate_passes_pct) pass_pct,
               SUM(mps.key_passes) key_passes,
               SUM(mps.total_passes) total_passes,
               SUM(mps.successful_dribbles) drib_s, SUM(mps.attempted_dribbles) drib_a,
               SUM(mps.tackles) tackles, SUM(mps.interceptions) ints,
               SUM(mps.clearances) clears, SUM(mps.blocked_shots) blocked,
               SUM(mps.aerial_won) aer_w, SUM(mps.aerial_lost) aer_l,
               SUM(mps.duel_won) duel_w, SUM(mps.duel_lost) duel_l,
               SUM(mps.fouls) fouls, SUM(mps.was_fouled) fouled,
               SUM(mps.yellow_cards) yellows, SUM(mps.red_cards) reds,
               SUM(mps.saves) saves, SUM(mps.goals_conceded) conceded,
               SUM(mps.touches) touches, SUM(mps.possession_lost) poss_lost,
               AVG(mps.rating) rating,
               SUM(mps.accurate_long_balls) long_b_s, SUM(mps.total_long_balls) long_b_a,
               SUM(mps.accurate_crosses) cross_s, SUM(mps.total_crosses) cross_a,
               SUM(mps.big_chances_missed) bcm
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 {year_clause}
    """, (pid,) + yp)
    p = cur.fetchone()
    mins = p["mins"] or 1
    games = p["games"] or 0

    def p90(v): return round((v or 0) / mins * 90, 3) if mins else 0
    def pct(a, b): return round((a or 0) / (b or 1) * 100, 1) if b else None

    # 팀명
    cur.execute("SELECT DISTINCT mps.team_id FROM match_player_stats mps WHERE mps.player_id=? LIMIT 1", (pid,))
    tid_row = cur.fetchone()
    ss_team_id = tid_row[0] if tid_row else team_id_db
    team_name = _ko_name_by_ss_id(ss_team_id) or str(ss_team_id)

    # 키 순위 (데이터 있는 경우)
    weight = prow["weight"] if prow and "weight" in prow.keys() else None

    _ALLOWED_PHYSICAL_COLS = {"height", "weight"}

    def physical_rank(col, val):
        if col not in _ALLOWED_PHYSICAL_COLS:
            raise ValueError(f"disallowed physical column: {col}")
        if not val: return None
        cur.execute(f"""
            SELECT COUNT(*) FROM players p2
            WHERE p2.{col} > ? AND p2.{col} IS NOT NULL AND p2.{col} > 0
              AND EXISTS (SELECT 1 FROM match_player_stats m2 JOIN events e2 ON m2.event_id=e2.id
                          WHERE m2.player_id=p2.id AND e2.tournament_id=777)
        """, (val,))
        above = cur.fetchone()[0]
        cur.execute(f"""
            SELECT COUNT(*) FROM players p2
            WHERE p2.{col} IS NOT NULL AND p2.{col} > 0
              AND EXISTS (SELECT 1 FROM match_player_stats m2 JOIN events e2 ON m2.event_id=e2.id
                          WHERE m2.player_id=p2.id AND e2.tournament_id=777)
        """)
        total = cur.fetchone()[0]
        return {"rank": above+1, "total": total, "pct": round((1 - above/total)*100) if total else None}

    height_rank = physical_rank("height", height)
    weight_rank = physical_rank("weight", weight)

    # ── 같은 포지션 선수 집계 (퍼센타일 기준) ──────────────────
    cur.execute(f"""
        SELECT mps.player_id,
               SUM(mps.minutes_played)              mins,
               SUM(mps.goals)                       goals,
               SUM(mps.assists)                     assists,
               SUM(mps.total_shots)                 shots,
               SUM(mps.shots_on_target)             sot,
               AVG(mps.accurate_passes_pct)         pass_pct,
               SUM(mps.key_passes)                  key_passes,
               SUM(mps.successful_dribbles)         drib_s,
               SUM(mps.attempted_dribbles)          drib_a,
               SUM(mps.tackles)                     tackles,
               SUM(mps.interceptions)               ints,
               SUM(mps.clearances)                  clears,
               SUM(mps.blocked_shots)               blocked,
               SUM(mps.aerial_won)                  aer_w,
               SUM(mps.aerial_lost)                 aer_l,
               SUM(mps.duel_won)                    duel_w,
               SUM(mps.duel_lost)                   duel_l,
               SUM(mps.saves)                       saves,
               SUM(mps.goals_conceded)              conceded,
               SUM(mps.fouls)                       fouls,
               SUM(mps.was_fouled)                  fouled,
               SUM(mps.touches)                     touches,
               COUNT(*)                             games
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE e.tournament_id=777 AND mps.position=? {year_clause}
        GROUP BY mps.player_id
        HAVING mins >= 270 AND games >= 5
    """, (pos_raw,) + yp)

    peers = {}
    for r in cur.fetchall():
        m = r["mins"] or 1
        def v90(col): return (r[col] or 0) / m * 90
        peers[r["player_id"]] = {
            "goals":    v90("goals"),
            "assists":  v90("assists"),
            "shots":    v90("shots"),
            "sot":      v90("sot"),
            "pass_pct": r["pass_pct"] or 0,
            "key_passes": v90("key_passes"),
            "drib_s":   v90("drib_s"),
            "drib_pct": pct(r["drib_s"], r["drib_a"]) or 0,
            "tackles":  v90("tackles"),
            "ints":     v90("ints"),
            "clears":   v90("clears"),
            "blocked":  v90("blocked"),
            "aer_w":    v90("aer_w"),
            "aer_pct":  pct(r["aer_w"], (r["aer_w"] or 0)+(r["aer_l"] or 0)) or 0,
            "duel_w":   v90("duel_w"),
            "duel_pct": pct(r["duel_w"], (r["duel_w"] or 0)+(r["duel_l"] or 0)) or 0,
            "saves":    v90("saves"),
            "touches":  v90("touches"),
            "fouls":    v90("fouls"),
        }

    def percentile(key, val, higher_is_better=True):
        vals = [v[key] for v in peers.values() if v[key] is not None]
        if not vals: return 50
        if higher_is_better:
            below = sum(1 for v in vals if v < val)
        else:
            below = sum(1 for v in vals if v > val)
        return round(below / len(vals) * 100)

    # 대상 선수 90분 환산값
    my = {
        "goals":    p90(p["goals"]),
        "assists":  p90(p["assists"]),
        "shots":    p90(p["shots"]),
        "sot":      p90(p["sot"]),
        "pass_pct": p["pass_pct"] or 0,
        "key_passes": p90(p["key_passes"]),
        "drib_s":   p90(p["drib_s"]),
        "drib_pct": pct(p["drib_s"], p["drib_a"]) or 0,
        "tackles":  p90(p["tackles"]),
        "ints":     p90(p["ints"]),
        "clears":   p90(p["clears"]),
        "blocked":  p90(p["blocked"]),
        "aer_w":    p90(p["aer_w"]),
        "aer_pct":  pct(p["aer_w"], (p["aer_w"] or 0)+(p["aer_l"] or 0)) or 0,
        "duel_w":   p90(p["duel_w"]),
        "duel_pct": pct(p["duel_w"], (p["duel_w"] or 0)+(p["duel_l"] or 0)) or 0,
        "saves":    p90(p["saves"]),
        "touches":  p90(p["touches"]),
        "fouls":    p90(p["fouls"]),
    }

    # 퍼센타일 계산
    pctile = {k: percentile(k, my[k]) for k in my}
    pctile["fouls"] = percentile("fouls", my["fouls"], higher_is_better=False)

    # 포지션별 주요 지표 그룹
    POS_GROUPS = {
        "G": [
            {"key":"saves",    "label":"선방(90분)",         "icon":"🧤"},
            {"key":"aer_pct",  "label":"공중볼 장악률(%)",    "icon":"✈"},
            {"key":"pass_pct", "label":"패스 성공률(%)",      "icon":"🎯"},
            {"key":"touches",  "label":"볼터치(90분)",        "icon":"👟"},
        ],
        "D": [
            {"key":"tackles",  "label":"태클(90분)",          "icon":"🛡"},
            {"key":"ints",     "label":"인터셉트(90분)",       "icon":"✂"},
            {"key":"clears",   "label":"클리어링(90분)",       "icon":"🥊"},
            {"key":"aer_w",    "label":"공중볼 성공(90분)",    "icon":"✈"},
            {"key":"aer_pct",  "label":"공중볼 장악률(%)",     "icon":"📊"},
            {"key":"blocked",  "label":"슈팅 차단(90분)",      "icon":"🚫"},
            {"key":"duel_pct", "label":"지상 듀얼 승률(%)",    "icon":"⚔"},
            {"key":"pass_pct", "label":"패스 성공률(%)",       "icon":"🎯"},
        ],
        "M": [
            {"key":"key_passes","label":"키패스(90분)",        "icon":"🔑"},
            {"key":"pass_pct", "label":"패스 성공률(%)",       "icon":"🎯"},
            {"key":"assists",  "label":"도움(90분)",           "icon":"🎨"},
            {"key":"drib_s",   "label":"드리블 성공(90분)",    "icon":"💨"},
            {"key":"tackles",  "label":"태클(90분)",           "icon":"🛡"},
            {"key":"ints",     "label":"인터셉트(90분)",       "icon":"✂"},
            {"key":"goals",    "label":"득점(90분)",           "icon":"⚽"},
            {"key":"touches",  "label":"볼터치(90분)",         "icon":"👟"},
        ],
        "F": [
            {"key":"goals",    "label":"득점(90분)",           "icon":"⚽"},
            {"key":"assists",  "label":"도움(90분)",           "icon":"🎨"},
            {"key":"shots",    "label":"슈팅(90분)",           "icon":"🎯"},
            {"key":"sot",      "label":"유효슈팅(90분)",       "icon":"🎯"},
            {"key":"drib_s",   "label":"드리블 성공(90분)",    "icon":"💨"},
            {"key":"drib_pct", "label":"드리블 성공률(%)",     "icon":"📊"},
            {"key":"aer_w",    "label":"공중볼 성공(90분)",    "icon":"✈"},
            {"key":"fouls",    "label":"파울 유도(90분)",      "icon":"🤸"},
        ],
    }

    stat_groups = POS_GROUPS.get(pos_raw, POS_GROUPS["M"])
    stat_items = []
    for sg in stat_groups:
        k = sg["key"]
        raw_val = my.get(k, 0)
        stat_items.append({
            "key":     k,
            "label":   sg["label"],
            "icon":    sg["icon"],
            "val":     round(raw_val, 2),
            "pctile":  pctile.get(k, 50),
            "peer_cnt": len(peers),
        })

    # 활동량 지표 (전체 선수 대비)
    cur.execute(f"""
        SELECT mps.player_id,
               SUM(mps.touches)                              AS touches,
               SUM(mps.duel_won) + SUM(mps.duel_lost)       AS duels,
               SUM(mps.total_passes)                         AS passes,
               SUM(mps.tackles) + SUM(mps.interceptions)    AS def_acts,
               SUM(mps.attempted_dribbles)                   AS dribbles,
               SUM(mps.minutes_played)                       AS mins2,
               COUNT(*)                                      AS games2
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE e.tournament_id=777 {year_clause}
        GROUP BY mps.player_id
        HAVING games2 >= 3 AND mins2 >= 150
    """, yp)

    all_activity = {}
    for r in cur.fetchall():
        m2 = r["mins2"] or 1
        all_activity[r["player_id"]] = {
            "touches_p90":  (r["touches"]  or 0) / m2 * 90,
            "duels_p90":    (r["duels"]    or 0) / m2 * 90,
            "passes_p90":   (r["passes"]   or 0) / m2 * 90,
            "def_p90":      (r["def_acts"] or 0) / m2 * 90,
            "dribbles_p90": (r["dribbles"] or 0) / m2 * 90,
        }

    def _act_pct(axis, val):
        vals = [v[axis] for v in all_activity.values()]
        if not vals: return 0
        return round(sum(1 for v in vals if v < val) / len(vals) * 100)

    p_act = all_activity.get(pid, {})
    activity_score = 0
    activity_percentiles = {}
    if p_act:
        weights = {"touches_p90": 0.35, "duels_p90": 0.25,
                   "passes_p90": 0.20, "def_p90": 0.10, "dribbles_p90": 0.10}
        for axis, w in weights.items():
            pct2 = _act_pct(axis, p_act.get(axis, 0))
            activity_percentiles[axis] = pct2
            activity_score += pct2 * w
        activity_score = round(activity_score)

    league_avg_act = {}
    if all_activity:
        for axis in ["touches_p90", "duels_p90", "passes_p90", "def_p90", "dribbles_p90"]:
            vals = [v[axis] for v in all_activity.values()]
            league_avg_act[axis] = round(sum(vals) / len(vals), 1) if vals else 0

    # 레이더용 5개 지표 (포지션별)
    RADAR_KEYS = {
        "G": ["saves","aer_pct","pass_pct","touches","duel_pct"],
        "D": ["tackles","ints","aer_pct","blocked","pass_pct"],
        "M": ["key_passes","pass_pct","drib_s","tackles","goals"],
        "F": ["goals","shots","drib_s","aer_w","assists"],
    }
    radar_keys = RADAR_KEYS.get(pos_raw, RADAR_KEYS["M"])
    RADAR_LABELS = {
        "goals":"득점","assists":"도움","shots":"슈팅","sot":"유효슈팅",
        "pass_pct":"패스%","key_passes":"키패스","drib_s":"드리블",
        "tackles":"태클","ints":"인터셉트","aer_pct":"공중볼%",
        "blocked":"슈팅차단","saves":"선방","touches":"터치","duel_pct":"듀얼승률%",
    }
    radar = [{"label": RADAR_LABELS.get(k, k), "pctile": pctile.get(k, 50)} for k in radar_keys]

    # 최근 5경기 폼
    cur.execute("""
        SELECT e.date_ts,
               CASE WHEN mps.is_home=1 THEN e.away_team_id ELSE e.home_team_id END opp_id,
               mps.goals, mps.assists, mps.rating, mps.result, mps.is_home,
               e.home_score, e.away_score,
               mps.tackles, mps.interceptions, mps.clearances, mps.aerial_won,
               mps.saves, mps.shots_on_target, mps.key_passes
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=777 AND e.date_ts IS NOT NULL
        ORDER BY e.date_ts DESC LIMIT 5
    """, (pid,))
    recent_form = []
    for r in cur.fetchall():
        d = _dt.datetime.utcfromtimestamp(r[0])
        hs, aws, is_home = r[7], r[8], r[6]
        if hs is not None and aws is not None:
            my_score, opp_score = (hs, aws) if is_home else (aws, hs)
            calc_result = "W" if my_score > opp_score else ("D" if my_score == opp_score else "L")
        else:
            calc_result = "?"
        recent_form.append({
            "date":       f"{d.year}/{d.month}/{d.day}",
            "opponent":   _ko_name_by_ss_id(str(r[1])) or str(r[1]),
            "is_home":    bool(r[6]),
            "goals":      r[2] or 0,
            "assists":    r[3] or 0,
            "rating":     round(r[4], 1) if r[4] else None,
            "result":     calc_result,
            "score":      f"{r[7]}-{r[8]}",
            "tackles":    r[9] or 0,
            "ints":       r[10] or 0,
            "clears":     r[11] or 0,
            "aer_w":      r[12] or 0,
            "saves":      r[13] or 0,
            "sot":        r[14] or 0,
            "key_passes": r[15] or 0,
        })

    conn.close()
    pos_label = {"G":"GK","D":"DF","M":"MF","F":"FW"}.get(pos_raw, pos_raw or "?")
    return jsonify({
        "found":      True,
        "player": {
            "id":       pid,
            "name":     matched,
            "team":     team_name,
            "pos":      pos_raw,
            "pos_label": pos_label,
            "height":   height,
            "weight":   weight,
            "height_rank": height_rank,
            "weight_rank": weight_rank,
            "games":    games,
            "mins":     int(mins),
            "goals":    p["goals"] or 0,
            "assists":  p["assists"] or 0,
            "rating":   round(p["rating"], 2) if p["rating"] else None,
            "yellows":  p["yellows"] or 0,
            "reds":     p["reds"] or 0,
        },
        "available_years": available_years,
        "stat_items":  stat_items,
        "radar":       radar,
        "recent_form": recent_form,
        "peer_count":  len(peers),
        "activity": {
            "score":       activity_score,
            "values":      {k: round(v, 1) for k, v in p_act.items()} if p_act else {},
            "percentiles": activity_percentiles,
            "league_avg":  league_avg_act,
        },
    })


@app.route("/api/player-analytics")
def get_player_analytics():
    """선수 개인 분석 보고서"""
    import datetime as _dt
    player_id = request.args.get("playerId", type=int)
    year      = request.args.get("year")
    if not player_id:
        return jsonify({}), 400

    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 선수 기본 정보
    cur.execute("""
        SELECT COALESCE(p.name_ko, p.name) nm, p.position pos, p.team_id, p.height, p.preferred_foot
        FROM players p WHERE p.id=?
    """, (player_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({}), 404

    name, position, team_id, height, preferred_foot = row["nm"], row["pos"], row["team_id"], row["height"], row["preferred_foot"]

    # 팀 한국어명 조회 + 소속 리그 판별 (가장 최근에 뛴 팀 기준)
    cur.execute("""
        SELECT mps.team_id
        FROM match_player_stats mps
        JOIN events e ON mps.event_id = e.id
        WHERE mps.player_id = ? AND e.date_ts IS NOT NULL
        ORDER BY e.date_ts DESC LIMIT 1
    """, (player_id,))
    tid_row = cur.fetchone()
    ss_team_id = tid_row[0] if tid_row else team_id
    team_name = _ko_name_by_ss_id(ss_team_id) or str(ss_team_id)
    league_key, tournament_id = _team_league(ss_team_id)

    year_clause = "AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?" if year else ""
    yp = (year,) if year else ()

    # 사용 가능 연도
    cur.execute("""
        SELECT DISTINCT strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) yr
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=? AND e.date_ts IS NOT NULL
        ORDER BY yr
    """, (player_id, tournament_id))
    available_years = [r[0] for r in cur.fetchall()]

    # 시즌별 집계
    cur.execute("""
        SELECT strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) yr,
               COUNT(*) games, SUM(mps.goals) goals, SUM(mps.assists) assists,
               AVG(mps.rating) rating, SUM(mps.minutes_played) minutes
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=?
        GROUP BY yr ORDER BY yr
    """, (player_id, tournament_id))
    season_summary = [
        {"year": r[0], "games": r[1], "goals": r[2] or 0, "assists": r[3] or 0,
         "rating": round(r[4], 2) if r[4] else None, "minutes": r[5] or 0}
        for r in cur.fetchall()
    ]

    # 월별 분석
    cur.execute(f"""
        SELECT CAST(strftime('%m', datetime(e.date_ts,'unixepoch','localtime')) AS INTEGER) mn,
               COUNT(*) games, SUM(mps.goals) goals, SUM(mps.assists) assists,
               AVG(mps.rating) rating
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=? {year_clause}
        GROUP BY mn ORDER BY mn
    """, (player_id, tournament_id) + yp)
    monthly = [
        {"month": r[0], "games": r[1], "goals": r[2] or 0, "assists": r[3] or 0,
         "rating": round(r[4], 2) if r[4] else None}
        for r in cur.fetchall()
    ]

    # 최근 10경기 폼
    cur.execute("""
        SELECT e.date_ts,
               CASE WHEN mps.is_home=1 THEN e.away_team_id ELSE e.home_team_id END opp_id,
               mps.goals, mps.assists, mps.rating, mps.result, mps.is_home,
               e.home_score, e.away_score
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=? AND e.date_ts IS NOT NULL
        ORDER BY e.date_ts DESC LIMIT 10
    """, (player_id, tournament_id))
    recent_form = []
    for r in cur.fetchall():
        d = _dt.datetime.utcfromtimestamp(r[0])
        opp_name = _ko_name_by_ss_id(str(r[1])) or str(r[1])
        hs2, aws2, is_home2 = r[7], r[8], r[6]
        if hs2 is not None and aws2 is not None:
            my2, opp2 = (hs2, aws2) if is_home2 else (aws2, hs2)
            calc_result2 = "W" if my2 > opp2 else ("D" if my2 == opp2 else "L")
        else:
            calc_result2 = "?"
        recent_form.append({
            "date": f"{d.year}/{d.month}/{d.day}",
            "opponent": opp_name,
            "is_home": bool(r[6]),
            "goals": r[2] or 0,
            "assists": r[3] or 0,
            "rating": round(r[4], 1) if r[4] else None,
            "result": calc_result2,
            "score": f"{r[7]}-{r[8]}" if r[7] is not None else "?"
        })

    # 레이더: 소속 리그 전체 선수 대비 백분위 (5경기 이상, 300분 이상)
    cur.execute(f"""
        SELECT mps.player_id,
               SUM(mps.goals) + SUM(mps.assists)        AS ga,
               SUM(mps.minutes_played)                   AS mins,
               AVG(mps.accurate_passes_pct)              AS pass_pct,
               SUM(mps.tackles) + SUM(mps.interceptions) + SUM(mps.clearances) AS def_acts,
               SUM(mps.shots_on_target)                  AS sot,
               SUM(mps.total_shots)                      AS ts,
               SUM(mps.successful_dribbles)              AS sdr,
               SUM(mps.attempted_dribbles)               AS adr,
               COUNT(*)                                  AS games
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE e.tournament_id=? {year_clause}
        GROUP BY mps.player_id
        HAVING games >= 5 AND mins >= 300
    """, (tournament_id,) + yp)

    all_stats = {}
    for r in cur.fetchall():
        pid, ga, mins, pass_pct, def_acts, sot, ts, sdr, adr, games = r
        if not mins: continue
        all_stats[pid] = {
            "attack":   (ga or 0) / mins * 90,
            "passing":  pass_pct or 0,
            "defense":  (def_acts or 0) / mins * 90,
            "shooting": ((sot or 0) / ts) * 100 if ts and ts >= 3 else 0,
            "dribble":  ((sdr or 0) / adr) * 100 if adr and adr >= 3 else 0,
        }

    radar = {}
    if player_id in all_stats:
        p_vals = all_stats[player_id]
        n = len(all_stats)
        for axis in ["attack", "passing", "defense", "shooting", "dribble"]:
            vals = [v[axis] for v in all_stats.values()]
            below = sum(1 for v in vals if v < p_vals[axis])
            radar[axis] = round(below / n * 100)
    else:
        radar = {k: 0 for k in ["attack", "passing", "defense", "shooting", "dribble"]}

    # 활동량 지표 (proxy metrics)
    cur.execute(f"""
        SELECT mps.player_id,
               SUM(mps.touches)                                        AS touches,
               SUM(mps.duel_won) + SUM(mps.duel_lost)                 AS duels,
               SUM(mps.total_passes)                                   AS passes,
               SUM(mps.tackles) + SUM(mps.interceptions)              AS def_acts,
               SUM(mps.attempted_dribbles)                             AS dribbles,
               SUM(mps.minutes_played)                                 AS mins,
               COUNT(*)                                                AS games
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE e.tournament_id=? {year_clause}
        GROUP BY mps.player_id
        HAVING games >= 3 AND mins >= 150
    """, (tournament_id,) + yp)

    all_activity = {}
    for r in cur.fetchall():
        pid2, touches, duels, passes, def_acts2, dribbles, mins2, games2 = r
        if not mins2: continue
        all_activity[pid2] = {
            "touches_p90":  round((touches or 0) / mins2 * 90, 1),
            "duels_p90":    round((duels or 0)   / mins2 * 90, 1),
            "passes_p90":   round((passes or 0)  / mins2 * 90, 1),
            "def_p90":      round((def_acts2 or 0) / mins2 * 90, 1),
            "dribbles_p90": round((dribbles or 0) / mins2 * 90, 1),
        }

    def _activity_pct(axis, val):
        vals = [v[axis] for v in all_activity.values()]
        if not vals: return 0
        below = sum(1 for v in vals if v < val)
        return round(below / len(vals) * 100)

    p_act = all_activity.get(player_id, {})
    activity_score = 0
    activity_percentiles = {}
    if p_act:
        weights = {"touches_p90": 0.35, "duels_p90": 0.25,
                   "passes_p90": 0.20, "def_p90": 0.10, "dribbles_p90": 0.10}
        for axis, w in weights.items():
            pct = _activity_pct(axis, p_act.get(axis, 0))
            activity_percentiles[axis] = pct
            activity_score += pct * w
        activity_score = round(activity_score)

    # 리그 평균 (기준값)
    league_avg_act = {}
    if all_activity:
        for axis in ["touches_p90", "duels_p90", "passes_p90", "def_p90", "dribbles_p90"]:
            vals = [v[axis] for v in all_activity.values()]
            league_avg_act[axis] = round(sum(vals) / len(vals), 1) if vals else 0

    # 전체 집계 (헤더용)
    cur.execute(f"""
        SELECT COUNT(*), SUM(mps.goals), SUM(mps.assists), AVG(mps.rating), SUM(mps.minutes_played),
               SUM(mps.yellow_cards), SUM(mps.red_cards)
        FROM match_player_stats mps JOIN events e ON mps.event_id=e.id
        WHERE mps.player_id=? AND e.tournament_id=? {year_clause}
    """, (player_id, tournament_id) + yp)
    agg = cur.fetchone()
    conn.close()

    return jsonify({
        "info": {
            "name": name,
            "position": position or "?",
            "team": team_name,
            "height": height,
            "preferred_foot": preferred_foot,
            "games":   agg[0] or 0,
            "goals":   agg[1] or 0,
            "assists": agg[2] or 0,
            "rating":  round(agg[3], 2) if agg[3] else None,
            "minutes": agg[4] or 0,
            "yellow_cards": agg[5] or 0,
            "red_cards":    agg[6] or 0,
        },
        "league":          league_key,
        "available_years": available_years,
        "season_summary":  season_summary,
        "monthly":         monthly,
        "recent_form":     recent_form,
        "radar":           radar,
        "activity": {
            "score":        activity_score,
            "values":       p_act,
            "percentiles":  activity_percentiles,
            "league_avg":   league_avg_act,
        },
    })


@app.route("/api/league-dashboard")
def get_league_dashboard():
    """K리그 전체 선수 인사이트 대시보드 (league=k1|k2, 기본 k2)"""
    year = request.args.get("year")   # None → 전체
    tournament_id = _league_tid(request.args.get("league"))
    if tournament_id is None:
        return jsonify({"error": "invalid league"}), 400

    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    year_clause = "AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?" if year else ""
    yp = (year,) if year else ()

    # 사용 가능 연도
    cur.execute("""
        SELECT DISTINCT strftime('%Y', datetime(e.date_ts,'unixepoch','localtime')) yr
        FROM events e WHERE e.tournament_id=? AND e.date_ts IS NOT NULL ORDER BY yr
    """, (tournament_id,))
    available_years = [r[0] for r in cur.fetchall()]

    # ── 랭킹 공통 쿼리 ─────────────────────────────────────────
    base_sql = f"""
        SELECT mps.player_id,
               COALESCE(p.name_ko, mps.player_name) name,
               mps.position pos,
               mps.team_id,
               COUNT(*)                   games,
               SUM(mps.goals)             goals,
               SUM(mps.assists)           assists,
               AVG(mps.rating)            rating,
               SUM(mps.minutes_played)    minutes,
               SUM(mps.total_shots)       shots,
               SUM(mps.shots_on_target)   sot,
               SUM(mps.key_passes)        key_passes,
               SUM(mps.tackles)           tackles,
               SUM(mps.interceptions)     interceptions,
               SUM(mps.successful_dribbles) dribbles,
               SUM(mps.attempted_dribbles) dribbles_att,
               SUM(mps.duel_won)          duel_won,
               SUM(mps.duel_lost)         duel_lost,
               SUM(mps.yellow_cards)      yellows,
               SUM(mps.red_cards)         reds,
               SUM(mps.saves)             saves
        FROM match_player_stats mps
        JOIN events e ON mps.event_id=e.id
        LEFT JOIN players p ON mps.player_id=p.id
        WHERE e.tournament_id=? {year_clause}
        GROUP BY mps.player_id
        HAVING games >= 3
    """
    cur.execute(base_sql, (tournament_id,) + yp)
    rows = cur.fetchall()

    def row_to_dict(r):
        tid = r["team_id"]
        return {
            "id":       r["player_id"],
            "name":     r["name"] or "?",
            "pos":      r["pos"] or "?",
            "team":     _ko_name_by_ss_id(tid) or str(tid),
            "games":    r["games"],
            "goals":    r["goals"] or 0,
            "assists":  r["assists"] or 0,
            "rating":   round(r["rating"], 2) if r["rating"] else None,
            "minutes":  r["minutes"] or 0,
            "shots":    r["shots"] or 0,
            "sot":      r["sot"] or 0,
            "key_passes": r["key_passes"] or 0,
            "tackles":  r["tackles"] or 0,
            "interceptions": r["interceptions"] or 0,
            "dribbles": r["dribbles"] or 0,
            "dribbles_att": r["dribbles_att"] or 0,
            "duel_won":  r["duel_won"] or 0,
            "duel_lost": r["duel_lost"] or 0,
            "duel_pct":  round((r["duel_won"] or 0) / max((r["duel_won"] or 0) + (r["duel_lost"] or 0), 1) * 100, 1),
            "tackles_p90": round((r["tackles"] or 0) / max(r["minutes"] or 1, 1) * 90, 2),
            "ints_p90":    round((r["interceptions"] or 0) / max(r["minutes"] or 1, 1) * 90, 2),
            "yellows":  r["yellows"] or 0,
            "reds":     r["reds"] or 0,
            "saves":    r["saves"] or 0,
        }

    all_players = [row_to_dict(r) for r in rows]

    # 랭킹 TOP20
    top_scorers  = sorted(all_players, key=lambda x: (-x["goals"],  -(x["assists"]), x["name"]))[:20]
    top_assists  = sorted(all_players, key=lambda x: (-x["assists"], -(x["goals"]),  x["name"]))[:20]
    top_rated    = sorted(
        [p for p in all_players if p["rating"] and p["minutes"] >= 270],
        key=lambda x: -x["rating"]
    )[:20]
    top_dribbles = sorted(
        [p for p in all_players if p["dribbles"] > 0],
        key=lambda x: -x["dribbles"]
    )[:20]
    top_defenders = sorted(
        [p for p in all_players if p["pos"] in ("D", "M") and (p["duel_won"] + p["duel_lost"]) >= 10],
        key=lambda x: (-x["duel_pct"], -(x["tackles_p90"] + x["ints_p90"]))
    )[:20]

    # ── 포지션별 평균 스탯 ─────────────────────────────────────
    pos_map = {"G": "GK", "D": "DF", "M": "MF", "F": "FW"}
    pos_stats = {}
    for p in all_players:
        pos = pos_map.get(p["pos"], "기타")
        if pos == "기타": continue
        if pos not in pos_stats:
            pos_stats[pos] = {"goals":0,"assists":0,"rating_sum":0,"rating_cnt":0,
                              "tackles":0,"dribbles":0,"key_passes":0,"shots":0,"cnt":0}
        s = pos_stats[pos]
        s["cnt"] += 1
        mins = p["minutes"] or 1
        s["goals"]    += p["goals"] / mins * 90
        s["assists"]  += p["assists"] / mins * 90
        s["tackles"]  += p["tackles"] / mins * 90
        s["dribbles"] += p["dribbles"] / mins * 90
        s["key_passes"] += p["key_passes"] / mins * 90
        s["shots"]    += p["shots"] / mins * 90
        if p["rating"]:
            s["rating_sum"] += p["rating"]; s["rating_cnt"] += 1

    position_avg = {}
    for pos, s in pos_stats.items():
        n = s["cnt"] or 1
        position_avg[pos] = {
            "goals":     round(s["goals"]/n, 3),
            "assists":   round(s["assists"]/n, 3),
            "tackles":   round(s["tackles"]/n, 3),
            "dribbles":  round(s["dribbles"]/n, 3),
            "key_passes":round(s["key_passes"]/n, 3),
            "shots":     round(s["shots"]/n, 3),
            "rating":    round(s["rating_sum"]/s["rating_cnt"], 2) if s["rating_cnt"] else None,
            "count":     s["cnt"],
        }

    # ── 팀별 공격력 ────────────────────────────────────────────
    team_stats = {}
    for p in all_players:
        t = p["team"]
        if t not in team_stats:
            team_stats[t] = {"goals":0,"assists":0,"rating_sum":0,"rating_cnt":0,
                             "players":0,"minutes":0}
        s = team_stats[t]
        s["goals"]   += p["goals"]
        s["assists"] += p["assists"]
        s["players"] += 1
        s["minutes"] += p["minutes"]
        if p["rating"]: s["rating_sum"] += p["rating"]; s["rating_cnt"] += 1

    team_attack = [
        {"team": t, "goals": s["goals"], "assists": s["assists"],
         "rating": round(s["rating_sum"]/s["rating_cnt"],2) if s["rating_cnt"] else None,
         "players": s["players"]}
        for t, s in team_stats.items()
    ]
    team_attack.sort(key=lambda x: -x["goals"])

    # ── 월별 리그 트렌드 ───────────────────────────────────────
    cur.execute(f"""
        SELECT CAST(strftime('%m', datetime(e.date_ts,'unixepoch','localtime')) AS INTEGER) mn,
               SUM(mps.goals) goals,
               SUM(mps.assists) assists,
               AVG(mps.rating) rating,
               COUNT(DISTINCT e.id) games
        FROM match_player_stats mps
        JOIN events e ON mps.event_id=e.id
        WHERE e.tournament_id=? {year_clause}
        GROUP BY mn ORDER BY mn
    """, (tournament_id,) + yp)
    monthly_trend = [
        {"month": r[0], "goals": r[1] or 0, "assists": r[2] or 0,
         "rating": round(r[3],2) if r[3] else None, "games": r[4]}
        for r in cur.fetchall()
    ]

    # ── 평점 분포 (히스토그램 버킷) ───────────────────────────
    rating_buckets = {}
    for p in all_players:
        if not p["rating"]: continue
        bucket = f"{int(p['rating']*10)//5 * 5 / 10:.1f}"
        rating_buckets[bucket] = rating_buckets.get(bucket, 0) + 1
    rating_dist = [{"bucket": k, "count": v}
                   for k, v in sorted(rating_buckets.items(), key=lambda x: float(x[0]))]

    conn.close()
    return jsonify({
        "available_years": available_years,
        "top_scorers":     top_scorers,
        "top_assists":     top_assists,
        "top_rated":       top_rated,
        "top_dribbles":    top_dribbles,
        "top_defenders":   top_defenders,
        "position_avg":    position_avg,
        "team_attack":     team_attack,
        "monthly_trend":   monthly_trend,
        "rating_dist":     rating_dist,
    })


@app.route("/api/team-goal-timing")
def get_team_goal_timing():
    """팀 득점/실점 시간대·전후반 분석"""
    team_id_str = request.args.get("teamId")
    year        = request.args.get("year")
    team_info   = next((t for t in TEAMS if t["id"] == team_id_str), None)
    if not team_info:
        return jsonify({"error": "team not found"}), 404

    ss_id   = team_info["sofascore_id"]
    db_path = os.path.join(BASE_DIR, "players.db")
    conn    = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur     = conn.cursor()

    # goal_events 테이블 없으면 빈 데이터 반환
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='goal_events'")
    if not cur.fetchone():
        conn.close()
        return jsonify({"ready": False})

    year_clause = ""
    yp = ()
    if year:
        year_clause = "AND strftime('%Y', datetime(e.date_ts,'unixepoch','localtime'))=?"
        yp = (year,)

    # 시간대 구간
    BANDS = [(1,15),(16,30),(31,45),(46,60),(61,75),(76,90),(91,120)]
    BAND_LABELS = ["1-15'","16-30'","31-45'","46-60'","61-75'","76-90'","90+'"]

    def count_goals(for_or_against):
        """for_or_against: 'for' = 득점, 'against' = 실점"""
        if for_or_against == "for":
            team_cond = "g.team_id = ?"
        else:
            # 실점 = 상대팀이 우리 팀 경기에서 넣은 골 (team_id != ss_id)
            team_cond = "g.team_id != ? AND (e.home_team_id=? OR e.away_team_id=?)"

        results = []
        for (s, e_min), label in zip(BANDS, BAND_LABELS):
            if for_or_against == "for":
                cur.execute(f"""
                    SELECT COUNT(*) FROM goal_events g
                    JOIN events e ON g.event_id = e.id
                    WHERE {team_cond}
                      AND (e.home_team_id=? OR e.away_team_id=?)
                      AND (g.minute + COALESCE(g.added_time,0)) >= ?
                      AND (g.minute + COALESCE(g.added_time,0)) <= ?
                      {year_clause}
                """, (ss_id, ss_id, ss_id, s, e_min) + yp)
            else:
                cur.execute(f"""
                    SELECT COUNT(*) FROM goal_events g
                    JOIN events e ON g.event_id = e.id
                    WHERE {team_cond}
                      AND (g.minute + COALESCE(g.added_time,0)) >= ?
                      AND (g.minute + COALESCE(g.added_time,0)) <= ?
                      {year_clause}
                """, (ss_id, ss_id, ss_id, s, e_min) + yp)
            _cr = cur.fetchone()
            results.append({"label": label, "count": _cr[0] if _cr else 0})
        return results

    gf_bands = count_goals("for")
    ga_bands = count_goals("against")

    # 전후반 집계
    def half_sum(bands, half):
        idxs = range(0, 3) if half == 1 else range(3, len(bands))
        return sum(bands[i]["count"] for i in idxs)

    gf_h1 = half_sum(gf_bands, 1)
    gf_h2 = half_sum(gf_bands, 2)
    ga_h1 = half_sum(ga_bands, 1)
    ga_h2 = half_sum(ga_bands, 2)

    # 전체 경기 수 (비율 계산용)
    cur.execute(f"""
        SELECT COUNT(*) FROM events e
        WHERE tournament_id=777 AND (home_team_id=? OR away_team_id=?)
        {year_clause}
    """, (ss_id, ss_id) + yp)
    total_games = cur.fetchone()[0] or 1

    conn.close()
    return jsonify({
        "ready": True,
        "team": team_info["name"],
        "total_games": total_games,
        "gf_bands":  gf_bands,
        "ga_bands":  ga_bands,
        "half": {
            "gf_h1": gf_h1, "gf_h2": gf_h2,
            "ga_h1": ga_h1, "ga_h2": ga_h2,
        }
    })


LEAGUE_TOURNAMENT_ID = {"k1": 410, "k2": 777}


def _league_tid(league_raw):
    """쿼리 파라미터 league → tournament_id. 기본값 k2(777). 잘못된 값은 None."""
    key = (league_raw or "k2").strip().lower()
    return LEAGUE_TOURNAMENT_ID.get(key)


def _heatmap_teams_for_league(tournament_id):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT DISTINCT mps.team_id
        FROM match_player_stats mps
        JOIN events e ON mps.event_id = e.id
        WHERE e.tournament_id = ? AND mps.team_id != 7652
        ORDER BY mps.team_id
    """, (tournament_id,)).fetchall()
    conn.close()
    team_map = {t["sofascore_id"]: t for t in TEAMS}
    result = []
    for (tid,) in rows:
        t = team_map.get(tid)
        if t:
            result.append({"id": t["id"], "sofascore_id": tid, "name": t["name"],
                           "short": t["short"], "emblem": t["emblem"], "primary": t["primary"]})
    result.sort(key=lambda x: x["name"])
    return result


def _heatmap_players_for_team(team_id, tournament_id):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT mps.player_id,
               COALESCE(NULLIF(mps.player_name,''), p.name_ko, p.name) AS name,
               COALESCE(mps.position, p.position) AS pos,
               COUNT(DISTINCT mps.event_id) as games,
               ROUND(AVG(mps.rating), 2) as avg_rating
        FROM match_player_stats mps
        JOIN events e ON mps.event_id = e.id
        LEFT JOIN players p ON mps.player_id = p.id
        WHERE mps.team_id = ? AND e.tournament_id = ?
        GROUP BY mps.player_id
        HAVING name IS NOT NULL
        ORDER BY games DESC, name
    """, (team_id, tournament_id)).fetchall()
    conn.close()
    return [{
        "playerId": r[0], "name": r[1], "position": r[2],
        "games": r[3], "avgRating": r[4]
    } for r in rows]


def _heatmap_points_for_player(player_id, team_id, event_id, tournament_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if event_id:
        rows = conn.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            LEFT JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ? AND h.event_id = ? AND e.tournament_id = ?
        """, (player_id, event_id, tournament_id)).fetchall()
    else:
        rows = conn.execute("""
            SELECT h.x, h.y, e.away_team_id
            FROM heatmap_points h
            LEFT JOIN events e ON h.event_id = e.id
            WHERE h.player_id = ? AND e.tournament_id = ?
        """, (player_id, tournament_id)).fetchall()

    points = _flip_points(rows, int(team_id))

    matches_rows = conn.execute("""
        SELECT DISTINCT e.id, e.home_team_id, e.home_team_name,
               e.away_team_id, e.away_team_name,
               e.home_score, e.away_score, e.date_ts
        FROM heatmap_points h
        JOIN events e ON h.event_id = e.id
        WHERE h.player_id = ? AND e.tournament_id = ? AND e.date_ts IS NOT NULL
        ORDER BY e.date_ts DESC
    """, (player_id, tournament_id)).fetchall()

    matches = [{
        "id":        r["id"],
        "home":      _ko_team(r["home_team_id"], r["home_team_name"]),
        "away":      _ko_team(r["away_team_id"], r["away_team_name"]),
        "homeScore": r["home_score"],
        "awayScore": r["away_score"],
        "datets":    r["date_ts"],
        "isAway":    r["away_team_id"] == int(team_id),
    } for r in matches_rows]

    conn.close()
    return {"points": points, "matches": matches, "playerId": player_id}


@app.route("/api/kleague2/teams")
def get_kleague2_teams():
    """히트맵 데이터가 있는 K리그2 팀 목록 (수원 삼성 제외)"""
    if not os.path.exists(DB_PATH):
        return jsonify([])
    return jsonify(_heatmap_teams_for_league(LEAGUE_TOURNAMENT_ID["k2"]))


@app.route("/api/kleague1/teams")
def get_kleague1_teams():
    """히트맵 데이터가 있는 K리그1 팀 목록"""
    if not os.path.exists(DB_PATH):
        return jsonify([])
    return jsonify(_heatmap_teams_for_league(LEAGUE_TOURNAMENT_ID["k1"]))


@app.route("/api/kleague2/players")
def get_kleague2_players():
    """K리그2 팀별 선수 목록 (player_id + 이름)"""
    team_id = request.args.get("teamId", "").strip()
    if not team_id:
        return jsonify({"error": "teamId required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify([])
    return jsonify(_heatmap_players_for_team(team_id, LEAGUE_TOURNAMENT_ID["k2"]))


@app.route("/api/kleague1/players")
def get_kleague1_players():
    """K리그1 팀별 선수 목록 (player_id + 이름)"""
    team_id = request.args.get("teamId", "").strip()
    if not team_id:
        return jsonify({"error": "teamId required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify([])
    return jsonify(_heatmap_players_for_team(team_id, LEAGUE_TOURNAMENT_ID["k1"]))


@app.route("/api/kleague2/heatmap")
def get_kleague2_heatmap():
    """K리그2 선수 ID 기반 히트맵"""
    player_id = request.args.get("playerId", "").strip()
    team_id   = request.args.get("teamId", "").strip()
    event_id  = request.args.get("eventId", "").strip()
    if not player_id or not team_id:
        return jsonify({"error": "playerId and teamId required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify({"points": []})
    return jsonify(_heatmap_points_for_player(player_id, team_id, event_id, LEAGUE_TOURNAMENT_ID["k2"]))


@app.route("/api/kleague1/heatmap")
def get_kleague1_heatmap():
    """K리그1 선수 ID 기반 히트맵"""
    player_id = request.args.get("playerId", "").strip()
    team_id   = request.args.get("teamId", "").strip()
    event_id  = request.args.get("eventId", "").strip()
    if not player_id or not team_id:
        return jsonify({"error": "playerId and teamId required"}), 400
    if not os.path.exists(DB_PATH):
        return jsonify({"points": []})
    return jsonify(_heatmap_points_for_player(player_id, team_id, event_id, LEAGUE_TOURNAMENT_ID["k1"]))


# ── 포지션 인사이트 API ──────────────────────────────────

def _year_date_params(year):
    """year 파라미터를 안전한 SQL 조건절 + 바인딩 파라미터로 변환한다.
    반환: (sql_condition_string, params_tuple)
    - year == "all" -> ("", ())
    - year == "2026" -> ("AND match_date >= ? AND match_date < ?", ("2026-01-01", "2027-01-01"))
    """
    if not year or year == "all":
        return "", ()
    try:
        y = int(year)
    except (ValueError, TypeError):
        return "", ()
    return "AND match_date >= ? AND match_date < ?", (f"{y}-01-01", f"{y+1}-01-01")

@app.route("/api/insights/top-performers")
def insights_top_performers():
    """포지션별 TOP 퍼포머 (최소 3경기 이상, 90분 환산)"""
    year = request.args.get("year", "2026")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    date_cond, date_params = _year_date_params(year)

    def pinfo(r):
        return {
            "player_id": r["player_id"],
            "name": r["name_ko"] or r["player_name"] or "",
            "team": _ko_team(r["team_id"], ""),
            "games": r["games"], "mins": r["mins"],
        }

    result = {}

    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.player_name, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.goals) as goals, SUM(COALESCE(m.expected_goals,0)) as xg,
               AVG(m.rating) as avg_rating,
               (SELECT COUNT(*) FROM goal_events g
                WHERE g.player_id=m.player_id AND g.is_penalty=1 AND g.is_own_goal=0
                AND g.event_id IN (
                    SELECT event_id FROM match_player_stats
                    WHERE player_id=m.player_id {date_cond})) as pk_goals
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='F' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND mins>=90
        ORDER BY goals DESC LIMIT 30
    """, date_params * 2).fetchall()
    result["F"] = [{**pinfo(r),
        "goals": r["goals"] or 0,
        "pk_goals": r["pk_goals"] or 0,
        "np_goals": (r["goals"] or 0) - (r["pk_goals"] or 0),
        "goals_p90": round((r["goals"] or 0) / r["mins"] * 90, 2),
        "np_goals_p90": round(((r["goals"] or 0) - (r["pk_goals"] or 0)) / r["mins"] * 90, 2),
        "xg": round(r["xg"] or 0, 2),
        "xg_eff": round((r["goals"] or 0) / r["xg"], 2) if (r["xg"] or 0) > 0 else None,
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows]

    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.player_name, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.total_passes) as tp, SUM(m.accurate_passes) as ap,
               SUM(m.tackles) as tkl, AVG(m.rating) as avg_rating
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='M' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND mins>=90 AND tp>0
        ORDER BY (CAST(ap AS REAL)/tp) DESC LIMIT 30
    """, date_params).fetchall()
    result["M"] = [{**pinfo(r),
        "pass_acc": round((r["ap"] or 0) / r["tp"] * 100, 1) if r["tp"] else None,
        "passes_p90": round((r["tp"] or 0) / r["mins"] * 90, 1),
        "tackles_p90": round((r["tkl"] or 0) / r["mins"] * 90, 2),
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows]

    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.player_name, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.tackles) as tkl, SUM(COALESCE(m.interceptions,0)) as intc,
               SUM(m.clearances) as clr, SUM(m.aerial_won) as aer,
               SUM(m.duel_won) as duel, AVG(m.rating) as avg_rating
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='D' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND mins>=90
        ORDER BY (tkl + intc*1.5 + clr + aer + duel) / mins DESC LIMIT 30
    """, date_params).fetchall()
    result["D"] = [{**pinfo(r),
        "def_score_p90": round(
            ((r["tkl"] or 0) + (r["intc"] or 0)*1.5 + (r["clr"] or 0)
             + (r["aer"] or 0) + (r["duel"] or 0)) / r["mins"] * 90, 2),
        "tackles_p90": round((r["tkl"] or 0) / r["mins"] * 90, 2),
        "clearances_p90": round((r["clr"] or 0) / r["mins"] * 90, 2),
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows]

    conn.close()
    return jsonify(result)


@app.route("/api/insights/xg-efficiency")
def insights_xg_efficiency():
    year = request.args.get("year", "2026")
    date_cond, date_params = _year_date_params(year)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id,
               COUNT(*) as games, SUM(m.goals) as goals,
               SUM(COALESCE(m.expected_goals,0)) as xg, SUM(m.total_shots) as shots,
               (SELECT COUNT(*) FROM goal_events g
                WHERE g.player_id=m.player_id AND g.is_penalty=1 AND g.is_own_goal=0
                AND g.event_id IN (
                    SELECT event_id FROM match_player_stats
                    WHERE player_id=m.player_id {date_cond})) as pk_goals
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='F' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND xg>0.5
        ORDER BY goals DESC LIMIT 20
    """, date_params * 2).fetchall()
    conn.close()
    return jsonify([{
        "player_id": r["player_id"],
        "name": r["name_ko"] or "",
        "team": _ko_team(r["team_id"], ""),
        "games": r["games"],
        "goals": r["goals"] or 0,
        "pk_goals": r["pk_goals"] or 0,
        "np_goals": (r["goals"] or 0) - (r["pk_goals"] or 0),
        "xg": round(r["xg"], 2),
        "diff": round((r["goals"] or 0) - r["xg"], 2),
        "shots": r["shots"] or 0,
    } for r in rows])


@app.route("/api/insights/forward-goals")
def insights_forward_goals():
    player_id = request.args.get("playerId", "").strip()
    year = request.args.get("year", "all")

    if not player_id:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        date_cond, date_params = _year_date_params(year)
        rows = conn.execute(f"""
            SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id,
                   SUM(m.goals) as total_goals,
                   (SELECT COUNT(*) FROM goal_events g
                    WHERE g.player_id=m.player_id AND g.is_penalty=1 AND g.is_own_goal=0
                    AND g.event_id IN (
                        SELECT event_id FROM match_player_stats
                        WHERE player_id=m.player_id {date_cond})) as pk_goals
            FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
            WHERE m.position='F' AND m.minutes_played>0 AND m.goals>0 {date_cond}
            GROUP BY m.player_id ORDER BY total_goals DESC LIMIT 30
        """, date_params * 2).fetchall()
        conn.close()
        return jsonify([{
            "player_id": r["player_id"],
            "name": r["name_ko"] or "",
            "team": _ko_team(r["team_id"], ""),
            "goals": r["total_goals"],
            "pk_goals": r["pk_goals"] or 0,
            "np_goals": (r["total_goals"] or 0) - (r["pk_goals"] or 0),
        } for r in rows])

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    bands = [("1-15",1,15),("16-30",16,30),("31-45",31,45),
             ("46-60",46,60),("61-75",61,75),("76-90",76,120)]
    time_data = []
    for label, lo, hi in bands:
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM goal_events
            WHERE player_id=? AND minute>=? AND minute<=? AND is_own_goal=0
        """, (player_id, lo, hi)).fetchone()
        time_data.append({"band": label, "goals": row["cnt"]})

    opp_rows = conn.execute("""
        SELECT CASE WHEN g.is_home=1 THEN e.away_team_id ELSE e.home_team_id END as opp_id,
               CASE WHEN g.is_home=1 THEN e.away_team_name ELSE e.home_team_name END as opp_name,
               COUNT(*) as goals
        FROM goal_events g JOIN events e ON g.event_id = e.id
        WHERE g.player_id=? AND g.is_own_goal=0
        GROUP BY opp_id ORDER BY goals DESC
    """, (player_id,)).fetchall()

    info = conn.execute("""
        SELECT COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.player_id=? AND m.player_name IS NOT NULL LIMIT 1
    """, (player_id,)).fetchone()
    conn.close()

    return jsonify({
        "player_id": int(player_id),
        "name": info["name_ko"] if info else "",
        "team": _ko_team(info["team_id"], "") if info else "",
        "time_bands": time_data,
        "by_opponent": [
            {"opponent": _ko_team(r["opp_id"], r["opp_name"]), "goals": r["goals"]}
            for r in opp_rows
        ],
    })


@app.route("/api/insights/midfielder-pass")
def insights_midfielder_pass():
    year = request.args.get("year", "2026")
    date_cond, date_params = _year_date_params(year)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.total_passes) as tp, SUM(m.accurate_passes) as ap,
               AVG(m.rating) as avg_rating
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='M' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND tp>=50
        ORDER BY (CAST(ap AS REAL)/tp) DESC LIMIT 25
    """, date_params).fetchall()
    conn.close()
    return jsonify([{
        "player_id": r["player_id"],
        "name": r["name_ko"] or "",
        "team": _ko_team(r["team_id"], ""),
        "games": r["games"], "mins": r["mins"],
        "total_passes": r["tp"] or 0, "accurate_passes": r["ap"] or 0,
        "pass_acc": round((r["ap"] or 0) / r["tp"] * 100, 1) if r["tp"] else 0,
        "passes_p90": round((r["tp"] or 0) / r["mins"] * 90, 1) if r["mins"] else 0,
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows])


@app.route("/api/insights/defender-score")
def insights_defender_score():
    year = request.args.get("year", "2026")
    date_cond, date_params = _year_date_params(year)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"""
        SELECT m.player_id, COALESCE(p.name_ko, m.player_name) as name_ko, m.team_id,
               COUNT(*) as games, SUM(m.minutes_played) as mins,
               SUM(m.tackles) as tkl, SUM(COALESCE(m.interceptions,0)) as intc,
               SUM(m.clearances) as clr, SUM(m.aerial_won) as aer,
               SUM(m.duel_won) as duel, AVG(m.rating) as avg_rating
        FROM match_player_stats m LEFT JOIN players p ON m.player_id=p.id
        WHERE m.position='D' AND m.minutes_played>0 {date_cond}
        GROUP BY m.player_id HAVING games>=3 AND mins>=90
        ORDER BY (tkl + intc*1.5 + clr + aer + duel) / mins DESC LIMIT 25
    """, date_params).fetchall()
    conn.close()
    return jsonify([{
        "player_id": r["player_id"],
        "name": r["name_ko"] or "",
        "team": _ko_team(r["team_id"], ""),
        "games": r["games"], "mins": r["mins"],
        "tackles": r["tkl"] or 0, "interceptions": r["intc"] or 0,
        "clearances": r["clr"] or 0, "aerial_won": r["aer"] or 0,
        "duel_won": r["duel"] or 0,
        "def_score": round(
            ((r["tkl"] or 0) + (r["intc"] or 0)*1.5 + (r["clr"] or 0)
             + (r["aer"] or 0) + (r["duel"] or 0)) / r["mins"] * 90, 2),
        "rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
    } for r in rows])


@app.route("/api/insights/player-detail")
def insights_player_detail():
    player_id = request.args.get("playerId", "").strip()
    pos       = request.args.get("pos", "F")
    if not player_id:
        return jsonify({"error": "playerId required"}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 기본 정보
    info = conn.execute("""
        SELECT COALESCE(p.name_ko, m.player_name) as name_ko, m.player_name, m.team_id, m.position
        FROM match_player_stats m LEFT JOIN players p ON m.player_id = p.id
        WHERE m.player_id = ? LIMIT 1
    """, (player_id,)).fetchone()

    if not info:
        conn.close()
        return jsonify({"error": "not found"}), 404

    # 경기별 스탯 (최신순, 최대 30경기)
    rows = conn.execute("""
        SELECT m.match_date,
               e.home_team_id, e.away_team_id, e.home_team_name, e.away_team_name,
               e.home_score, e.away_score, m.is_home,
               m.minutes_played, m.rating,
               m.goals, COALESCE(m.expected_goals, 0) as xg,
               m.total_passes, m.accurate_passes, m.accurate_passes_pct,
               m.key_passes, m.assists,
               m.tackles, COALESCE(m.interceptions, 0) as interceptions,
               m.clearances, m.aerial_won, m.duel_won,
               m.total_shots, m.shots_on_target
        FROM match_player_stats m
        JOIN events e ON m.event_id = e.id
        WHERE m.player_id = ? AND m.minutes_played > 0
        ORDER BY m.match_date DESC LIMIT 30
    """, (player_id,)).fetchall()

    matches = []
    for r in rows:
        opp_id   = r["away_team_id"] if r["is_home"] else r["home_team_id"]
        opp_name = r["away_team_name"] if r["is_home"] else r["home_team_name"]
        score    = f"{r['home_score']}-{r['away_score']}"
        def_score = round(
            ((r["tackles"] or 0) + (r["interceptions"] or 0)*1.5
             + (r["clearances"] or 0) + (r["aerial_won"] or 0) + (r["duel_won"] or 0))
            / r["minutes_played"] * 90, 2
        ) if r["minutes_played"] else 0
        matches.append({
            "date":       r["match_date"],
            "opponent":   _ko_team(opp_id, opp_name),
            "score":      score,
            "is_home":    bool(r["is_home"]),
            "mins":       r["minutes_played"],
            "rating":     round(r["rating"], 2) if r["rating"] else None,
            "goals":      r["goals"] or 0,
            "xg":         round(r["xg"], 2),
            "assists":    r["assists"] or 0,
            "pass_acc":   round(r["accurate_passes_pct"], 1) if r["accurate_passes_pct"] else None,
            "key_passes": r["key_passes"] or 0,
            "tackles":    r["tackles"] or 0,
            "def_score":  def_score,
            "shots":      r["total_shots"] or 0,
        })

    # 포지션 평균 (비교용)
    avg = conn.execute("""
        SELECT ROUND(AVG(rating), 2) as avg_rating,
               ROUND(AVG(goals), 2) as avg_goals,
               ROUND(AVG(COALESCE(expected_goals,0)), 2) as avg_xg,
               ROUND(AVG(CAST(accurate_passes AS REAL)/NULLIF(total_passes,0)*100), 1) as avg_pass_acc,
               ROUND(AVG(tackles), 2) as avg_tackles
        FROM match_player_stats
        WHERE position = ? AND minutes_played >= 45
    """, (pos,)).fetchone()

    conn.close()
    return jsonify({
        "player_id": int(player_id),
        "name":  info["name_ko"] or info["player_name"] or "",
        "team":  _ko_team(info["team_id"], ""),
        "pos":   pos,
        "matches": matches,
        "pos_avg": {
            "rating":   avg["avg_rating"],
            "goals":    avg["avg_goals"],
            "xg":       avg["avg_xg"],
            "pass_acc": avg["avg_pass_acc"],
            "tackles":  avg["avg_tackles"],
        },
    })


# ── K리그2 다음 경기 일정 ─────────────────────────────────
KLEAGUE_TEAM_CODE = {
    # K2
    "K02": "suwon",   "K06": "busan",   "K07": "jeonnam", "K08": "seongnam",
    "K17": "daegu",   "K20": "gyeongnam","K29": "suwon_fc","K31": "seouland",
    "K32": "ansan",   "K34": "asan",    "K36": "gimpo",   "K37": "cheongju",
    "K38": "cheonan", "K39": "hwaseong","K40": "paju",    "K41": "gimhae",
    "K42": "yongin",
    # K1
    "K01": "ulsan",   "K03": "pohang",  "K04": "jeju",    "K05": "jeonbuk",
    "K09": "fcseoul", "K10": "daejeon", "K18": "incheon", "K21": "gangwon",
    "K22": "gwangju", "K26": "bucheon", "K27": "anyang",  "K35": "gimcheon",
}

def _fetch_k2_all_games(year=None):
    """K리그 공식 API에서 K2 전체 경기(완료+예정) 수집 — 1~12월"""
    import urllib.request, datetime
    url = "https://www.kleague.com/getScheduleList.do"
    if year is None:
        year = datetime.datetime.now().year
    games = []
    now_month = datetime.datetime.now().month if year == datetime.datetime.now().year else 12
    for m in range(1, now_month + 2):
        if m > 12:
            break
        payload = json.dumps({"leagueId": "2", "year": str(year), "month": str(m).zfill(2)}).encode("utf-8")
        req = urllib.request.Request(url, data=payload,
            headers={"Content-Type": "application/json; charset=UTF-8", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                games += data.get("data", {}).get("scheduleList", [])
        except Exception:
            pass
    return games

def _parse_k2_game(g):
    """K리그 API 경기 dict → 통일 포맷"""
    home_code = g.get("homeTeam", "")
    away_code = g.get("awayTeam", "")
    home_id   = KLEAGUE_TEAM_CODE.get(home_code)
    away_id   = KLEAGUE_TEAM_CODE.get(away_code)
    home_info = next((t for t in TEAMS if t["id"] == home_id), None)
    away_info = next((t for t in TEAMS if t["id"] == away_id), None)
    finished  = g.get("endYn") == "Y" or g.get("gameStatus") == "FE"
    return {
        "date":       g.get("gameDate", ""),
        "time":       g.get("gameTime", ""),
        "round":      g.get("roundId"),
        "home_code":  home_code,
        "away_code":  away_code,
        "home_id":    home_id,
        "away_id":    away_id,
        "home_name":  home_info["name"]  if home_info else g.get("homeTeamName", home_code),
        "away_name":  away_info["name"]  if away_info else g.get("awayTeamName", away_code),
        "home_short": home_info["short"] if home_info else g.get("homeTeamName", home_code),
        "away_short": away_info["short"] if away_info else g.get("awayTeamName", away_code),
        "venue":      g.get("fieldName", ""),
        "finished":   finished,
        "home_score": g.get("homeGoal") if finished else None,
        "away_score": g.get("awayGoal") if finished else None,
    }

@app.route("/api/k2/schedule")
def get_k2_schedule():
    """K2 예정 경기 + 팀별 다음 경기"""
    import datetime
    now_str = datetime.datetime.now().strftime("%Y.%m.%d")
    try:
        raw = _fetch_k2_all_games()
    except Exception:
        return jsonify({"upcoming": [], "next_by_team": {}}), 200

    upcoming = []
    for g in raw:
        if g.get("endYn") == "Y" or g.get("gameStatus") == "FE":
            continue
        if g.get("gameDate", "") < now_str:
            continue
        upcoming.append(_parse_k2_game(g))
    upcoming.sort(key=lambda x: (x["date"], x["time"]))

    next_by_team = {}
    for g in upcoming:
        for side in ("home_id", "away_id"):
            tid = g.get(side)
            if tid and tid not in next_by_team:
                next_by_team[tid] = {**g, "is_home": side == "home_id"}

    return jsonify({"upcoming": upcoming, "next_by_team": next_by_team})


@app.route("/api/k2/rounds")
def get_k2_rounds():
    """K2 라운드 목록 + 각 라운드 경기 결과/예정"""
    import datetime
    try:
        raw = _fetch_k2_all_games()
    except Exception:
        return jsonify({"rounds": [], "current_round": None}), 200

    games_by_round = {}
    for g in raw:
        r = g.get("roundId")
        if not r:
            continue
        if r not in games_by_round:
            games_by_round[r] = []
        games_by_round[r].append(_parse_k2_game(g))

    rounds = []
    now_str = datetime.datetime.now().strftime("%Y.%m.%d")
    current_round = None
    for rnd in sorted(games_by_round.keys()):
        items = sorted(games_by_round[rnd], key=lambda x: (x["date"], x["time"]))
        finished_count = sum(1 for g in items if g["finished"])
        rounds.append({
            "round":    rnd,
            "games":    items,
            "finished": finished_count,
            "total":    len(items),
        })
        # 가장 최근 완료 라운드 or 진행 중 라운드를 current로
        if finished_count > 0:
            current_round = rnd

    return jsonify({"rounds": rounds, "current_round": current_round})


def _fetch_k1_all_games(year=None):
    """K리그 공식 API에서 K1 전체 경기(완료+예정) 수집 — 1~12월"""
    import urllib.request, datetime
    url = "https://www.kleague.com/getScheduleList.do"
    if year is None:
        year = datetime.datetime.now().year
    games = []
    now_month = datetime.datetime.now().month if year == datetime.datetime.now().year else 12
    for m in range(1, now_month + 2):
        if m > 12:
            break
        payload = json.dumps({"leagueId": "1", "year": str(year), "month": str(m).zfill(2)}).encode("utf-8")
        req = urllib.request.Request(url, data=payload,
            headers={"Content-Type": "application/json; charset=UTF-8", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                games += data.get("data", {}).get("scheduleList", [])
        except Exception:
            pass
    return games


def _parse_k1_game(g):
    """K1 API 경기 dict → 통일 포맷"""
    home_code = g.get("homeTeam", "")
    away_code = g.get("awayTeam", "")
    home_id   = KLEAGUE_TEAM_CODE.get(home_code)
    away_id   = KLEAGUE_TEAM_CODE.get(away_code)
    home_info = next((t for t in TEAMS if t["id"] == home_id), None)
    away_info = next((t for t in TEAMS if t["id"] == away_id), None)
    finished  = g.get("endYn") == "Y" or g.get("gameStatus") == "FE"
    return {
        "date":       g.get("gameDate", ""),
        "time":       g.get("gameTime", ""),
        "round":      g.get("roundId"),
        "home_code":  home_code,
        "away_code":  away_code,
        "home_id":    home_id,
        "away_id":    away_id,
        "home_name":  home_info["name"]  if home_info else g.get("homeTeamName", home_code),
        "away_name":  away_info["name"]  if away_info else g.get("awayTeamName", away_code),
        "home_short": home_info["short"] if home_info else g.get("homeTeamName", home_code),
        "away_short": away_info["short"] if away_info else g.get("awayTeamName", away_code),
        "venue":      g.get("fieldName", ""),
        "finished":   finished,
        "home_score": g.get("homeGoal") if finished else None,
        "away_score": g.get("awayGoal") if finished else None,
    }


@app.route("/api/k1/schedule")
def get_k1_schedule():
    """K1 예정 경기 + 팀별 다음 경기"""
    import datetime
    now_str = datetime.datetime.now().strftime("%Y.%m.%d")
    try:
        raw = _fetch_k1_all_games()
    except Exception:
        return jsonify({"upcoming": [], "next_by_team": {}}), 200

    upcoming = []
    for g in raw:
        if g.get("endYn") == "Y" or g.get("gameStatus") == "FE":
            continue
        if g.get("gameDate", "") < now_str:
            continue
        upcoming.append(_parse_k1_game(g))
    upcoming.sort(key=lambda x: (x["date"], x["time"]))

    next_by_team = {}
    for g in upcoming:
        for side in ("home_id", "away_id"):
            tid = g.get(side)
            if tid and tid not in next_by_team:
                next_by_team[tid] = {**g, "is_home": side == "home_id"}

    return jsonify({"upcoming": upcoming, "next_by_team": next_by_team})


@app.route("/api/k1/rounds")
def get_k1_rounds():
    """K1 라운드 목록 + 각 라운드 경기 결과/예정"""
    import datetime
    try:
        raw = _fetch_k1_all_games()
    except Exception:
        return jsonify({"rounds": [], "current_round": None}), 200

    games_by_round = {}
    for g in raw:
        r = g.get("roundId")
        if not r:
            continue
        if r not in games_by_round:
            games_by_round[r] = []
        games_by_round[r].append(_parse_k1_game(g))

    rounds = []
    current_round = None
    for rnd in sorted(games_by_round.keys()):
        items = sorted(games_by_round[rnd], key=lambda x: (x["date"], x["time"]))
        finished_count = sum(1 for g in items if g["finished"])
        rounds.append({
            "round":    rnd,
            "games":    items,
            "finished": finished_count,
            "total":    len(items),
        })
        if finished_count > 0:
            current_round = rnd

    return jsonify({"rounds": rounds, "current_round": current_round})


@app.route("/api/player-vs-teams")
def get_player_vs_teams():
    """선수가 상대팀별로 기록한 성적 (평점·G+A·출전수)"""
    player_id = request.args.get("playerId", type=int)
    if not player_id:
        return jsonify([]), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT
            CASE WHEN mps.is_home=1 THEN e.away_team_id ELSE e.home_team_id END AS opp_ss_id,
            COUNT(*)                    AS games,
            SUM(mps.goals)              AS goals,
            SUM(mps.assists)            AS assists,
            SUM(mps.goals+mps.assists)  AS ga,
            AVG(mps.rating)             AS avg_rating,
            AVG(mps.minutes_played)     AS avg_mins,
            SUM(mps.shots_on_target)    AS sot,
            SUM(mps.key_passes)         AS key_passes
        FROM match_player_stats mps
        JOIN events e ON mps.event_id = e.id
        WHERE mps.player_id = ? AND e.tournament_id = 777
        GROUP BY opp_ss_id
        HAVING games >= 1
        ORDER BY avg_rating DESC NULLS LAST
    """, (player_id,)).fetchall()
    conn.close()

    result = []
    for r in rows:
        opp_info = next((t for t in TEAMS if t["sofascore_id"] == r["opp_ss_id"]), None)
        opp_name = opp_info["short"] if opp_info else str(r["opp_ss_id"])
        result.append({
            "opp_id":    r["opp_ss_id"],
            "opp_name":  opp_name,
            "games":     r["games"],
            "goals":     r["goals"] or 0,
            "assists":   r["assists"] or 0,
            "ga":        r["ga"] or 0,
            "avg_rating": round(r["avg_rating"], 2) if r["avg_rating"] else None,
            "avg_mins":  round(r["avg_mins"] or 0),
            "sot":       r["sot"] or 0,
            "key_passes": r["key_passes"] or 0,
        })
    return jsonify(result)


# ── 선수 상태 (부상/출전정지/정상) 관리 API ─────────────

def _load_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_status(data):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/api/player-status", methods=["GET"])
def get_player_status():
    """전체 선수 상태 조회. ?teamId=xxx 로 팀 필터 가능."""
    data = _load_status()
    team_id = request.args.get("teamId", "")
    if team_id:
        data = {k: v for k, v in data.items() if v.get("teamId") == team_id}
    return jsonify(data)

@app.route("/api/player-status", methods=["POST"])
def update_player_status():
    """선수 상태 업데이트. body: {playerId, teamId, name, status, note, returnDate}
    status: "available" | "injured" | "suspended" | "doubtful"
    """
    body = request.get_json()
    pid = str(body.get("playerId", ""))
    if not pid:
        return jsonify({"error": "playerId required"}), 400
    data = _load_status()
    status = body.get("status", "available")
    if status == "available" and pid in data:
        del data[pid]
    else:
        data[pid] = {
            "playerId": pid,
            "teamId": body.get("teamId", ""),
            "name": body.get("name", ""),
            "status": status,
            "note": body.get("note", ""),
            "returnDate": body.get("returnDate", ""),
            "updatedAt": datetime.now().isoformat(),
        }
    _save_status(data)
    return jsonify({"ok": True, "total": len(data)})

@app.route("/api/player-status/<player_id>", methods=["DELETE"])
def delete_player_status(player_id):
    """선수 상태 삭제 (정상 복귀)"""
    data = _load_status()
    if player_id in data:
        del data[player_id]
        _save_status(data)
    return jsonify({"ok": True})


_BACKTEST_CACHE = {}  # {(league,year): {ts:..., data:...}}
_BACKTEST_TTL_SEC = 600


@app.route("/api/prediction-backtest")
def prediction_backtest():
    """
    Rolling backtest: 각 종료 경기 직전까지의 데이터만으로 예측 → 실제 결과와 비교.
    1X2 적중률 / 정확 스코어 / TOP3 / Brier / λ MAE 산출.
    K2 한정으로 검증된 모델 (K1은 별도 캘리브레이션 필요).
    """
    league = request.args.get("league", "k2").lower()
    year   = request.args.get("year", "2026")
    tid    = 410 if league == "k1" else 777

    import time as _time
    cache_key = (league, year)
    cached = _BACKTEST_CACHE.get(cache_key)
    if cached and (_time.time() - cached["ts"] < _BACKTEST_TTL_SEC):
        return jsonify(cached["data"])

    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # round 컬럼이 있는지 확인 (events 테이블에 round 컬럼 없으면 날짜 기반으로 라운드 추정)
    cur.execute("PRAGMA table_info(events)")
    ev_cols = {r[1] for r in cur.fetchall()}
    has_round = "round" in ev_cols

    round_expr = "round" if has_round else "NULL"
    cur.execute(f"""
        SELECT id, date_ts, home_team_id, away_team_id, home_score, away_score, {round_expr}
        FROM events
        WHERE tournament_id=?
          AND home_score IS NOT NULL AND away_score IS NOT NULL
          AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
        ORDER BY date_ts ASC
    """, (tid, year))
    games = cur.fetchall()

    # round 없으면 날짜 주차로 대체 (경기 몰린 주 = 같은 라운드)
    if not has_round:
        import datetime as _dt
        week_to_round = {}
        _counter = 0
        _games_aug = []
        for g in games:
            gid, ts, hid, aid, hs, as_, _r = g
            wk = _dt.datetime.fromtimestamp(ts).strftime("%Y-%W")
            if wk not in week_to_round:
                _counter += 1
                week_to_round[wk] = _counter
            _games_aug.append((gid, ts, hid, aid, hs, as_, week_to_round[wk]))
        games = _games_aug

    n_total = n_skipped = 0
    n_hit_1x2 = n_exact = n_top3 = 0
    sum_brier = sum_mae_h = sum_mae_a = 0.0
    n_pred_home_wins = n_pred_draws = n_pred_away_wins = 0
    n_actual_home_wins = n_actual_draws = n_actual_away_wins = 0
    confidence_buckets = {"high": [0, 0], "med": [0, 0], "low": [0, 0]}  # [hit, total]
    per_round_agg = {}  # {round: {"hit": n, "total": n}}

    for g in games:
        gid, ts, hid, aid, hs, as_, rnd = g
        pred = _predict_core(cur, hid, aid, tid, ts, year)
        if not pred:
            n_skipped += 1
            continue
        n_total += 1

        actual = "home" if hs > as_ else "away" if hs < as_ else "draw"
        outcome_p = {"home": pred["pred_home"], "draw": pred["pred_draw"], "away": pred["pred_away"]}
        pred_outcome = max(outcome_p, key=outcome_p.get)

        if pred_outcome == actual:
            n_hit_1x2 += 1

        actual_str = f"{int(hs)}-{int(as_)}"
        top_strs = [f"{s['home']}-{s['away']}" for s in pred["top_scores"]]
        if top_strs and top_strs[0] == actual_str:
            n_exact += 1
        if actual_str in top_strs[:3]:
            n_top3 += 1

        actual_p = {"home": 1 if actual == "home" else 0,
                    "draw": 1 if actual == "draw" else 0,
                    "away": 1 if actual == "away" else 0}
        brier = sum((outcome_p[k] / 100.0 - actual_p[k]) ** 2 for k in ("home", "draw", "away")) / 3
        sum_brier += brier
        sum_mae_h += abs(pred["lam_home"] - hs)
        sum_mae_a += abs(pred["lam_away"] - as_)

        if pred_outcome == "home": n_pred_home_wins += 1
        elif pred_outcome == "draw": n_pred_draws += 1
        else: n_pred_away_wins += 1

        if actual == "home": n_actual_home_wins += 1
        elif actual == "draw": n_actual_draws += 1
        else: n_actual_away_wins += 1

        # 신뢰도 버킷 (백테스트 시점 기준 표본 크기로 재계산)
        season_g = min(pred["h_games"], pred["a_games"])
        # H2H 사전 경기 수
        cur.execute("""
            SELECT COUNT(*) FROM events
            WHERE tournament_id=?
              AND ((home_team_id=? AND away_team_id=?) OR (home_team_id=? AND away_team_id=?))
              AND date_ts < ?
              AND home_score IS NOT NULL AND away_score IS NOT NULL
        """, (tid, hid, aid, aid, hid, ts))
        h2h_g = cur.fetchone()[0] or 0
        bucket = "high" if (h2h_g >= 5 and season_g >= 6) else \
                 "med"  if (h2h_g >= 3 or  season_g >= 4) else "low"
        confidence_buckets[bucket][1] += 1
        if pred_outcome == actual:
            confidence_buckets[bucket][0] += 1

        # 라운드별 집계 (누적 차트용)
        if rnd is not None:
            bag = per_round_agg.setdefault(int(rnd), {"hit": 0, "total": 0})
            bag["total"] += 1
            if pred_outcome == actual:
                bag["hit"] += 1

    conn.close()

    # per-round 누적 라인 생성
    per_round = []
    cum_hit = cum_total = 0
    for r in sorted(per_round_agg.keys()):
        a = per_round_agg[r]
        cum_hit   += a["hit"]
        cum_total += a["total"]
        per_round.append({
            "round":     r,
            "hit":       a["hit"],
            "total":     a["total"],
            "round_pct": round(a["hit"] / a["total"] * 100, 1) if a["total"] else None,
            "cum_hit":   cum_hit,
            "cum_total": cum_total,
            "cum_pct":   round(cum_hit / cum_total * 100, 1) if cum_total else None,
        })

    if n_total == 0:
        result = {"league": league.upper(), "year": year, "n_total": 0, "n_skipped": n_skipped,
                  "ready": False}
    else:
        result = {
            "league":            league.upper(),
            "year":              year,
            "n_total":           n_total,
            "n_skipped":         n_skipped,
            "hit_1x2_pct":       round(n_hit_1x2 / n_total * 100, 1),
            "exact_score_pct":   round(n_exact   / n_total * 100, 1),
            "top3_score_pct":    round(n_top3    / n_total * 100, 1),
            "brier_score":       round(sum_brier / n_total, 3),
            "mae_lambda_home":   round(sum_mae_h / n_total, 2),
            "mae_lambda_away":   round(sum_mae_a / n_total, 2),
            "baseline_random":   33.3,
            "predicted_outcomes":  {"home": n_pred_home_wins, "draw": n_pred_draws, "away": n_pred_away_wins},
            "actual_outcomes":     {"home": n_actual_home_wins, "draw": n_actual_draws, "away": n_actual_away_wins},
            "by_confidence":     {
                k: {"hit": v[0], "total": v[1],
                    "pct": round(v[0] / v[1] * 100, 1) if v[1] else None}
                for k, v in confidence_buckets.items()
            },
            "per_round":         per_round,
            "ready": True,
        }

    _BACKTEST_CACHE[cache_key] = {"ts": _time.time(), "data": result}
    return jsonify(result)


_SEASON_SIM_CACHE = {}
_SEASON_SIM_TTL_SEC = 600


@app.route("/api/season-simulation")
def season_simulation():
    """
    잔여 경기 몬테카를로 시뮬레이션으로 시즌 마지막 순위 확률 계산.
    각 팀의 우승/TOP4(K1)·승격(K2)/강등 확률 반환.
    """
    league = request.args.get("league", "k2").lower()
    year   = request.args.get("year", "2026")
    n_iter = max(1000, min(20000, int(request.args.get("iter", 10000))))
    tid    = 410 if league == "k1" else 777

    import time as _time, random
    cache_key = (league, year, n_iter)
    cached = _SEASON_SIM_CACHE.get(cache_key)
    if cached and (_time.time() - cached["ts"] < _SEASON_SIM_TTL_SEC):
        return jsonify(cached["data"])

    db_path = os.path.join(BASE_DIR, "players.db")
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    cur.execute("""
        SELECT home_team_id, away_team_id, home_score, away_score
        FROM events
        WHERE tournament_id=? AND home_score IS NOT NULL
          AND strftime('%Y', datetime(date_ts,'unixepoch','localtime'))=?
    """, (tid, year))
    standings = {}
    def _bag(team_id):
        if team_id not in standings:
            standings[team_id] = {"played": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
        return standings[team_id]
    for hid, aid, hs, as_ in cur.fetchall():
        h = _bag(hid); a = _bag(aid)
        h["played"] += 1; a["played"] += 1
        h["gf"] += hs; h["ga"] += as_
        a["gf"] += as_; a["ga"] += hs
        if hs > as_:
            h["w"] += 1; h["pts"] += 3; a["l"] += 1
        elif hs < as_:
            a["w"] += 1; a["pts"] += 3; h["l"] += 1
        else:
            h["d"] += 1; h["pts"] += 1
            a["d"] += 1; a["pts"] += 1

    # 잔여 경기는 K리그 schedule API에서 (events 테이블에 미진행 경기가 없음)
    try:
        raw_schedule = _fetch_k1_all_games(int(year)) if league == "k1" else _fetch_k2_all_games(int(year))
    except Exception:
        raw_schedule = []

    # app slug → sofascore_id 매핑
    slug_to_ss = {t["id"]: t["sofascore_id"] for t in TEAMS}
    parser = _parse_k1_game if league == "k1" else _parse_k2_game

    upcoming_games = []
    for g in raw_schedule:
        parsed = parser(g)
        if parsed.get("finished"):
            continue
        h_slug = parsed.get("home_id")
        a_slug = parsed.get("away_id")
        if not h_slug or not a_slug:
            continue
        h_ss = slug_to_ss.get(h_slug)
        a_ss = slug_to_ss.get(a_slug)
        if not h_ss or not a_ss:
            continue
        upcoming_games.append((h_ss, a_ss))

    # 각 잔여 경기에 대해 P(H/D/A) 사전 계산
    now_ts = int(__import__("time").time())
    fixtures = []
    pred_cache = {}  # (hid, aid) → pred (같은 매치업 중복 계산 방지)
    for hid, aid in upcoming_games:
        key = (hid, aid)
        if key in pred_cache:
            pred = pred_cache[key]
        else:
            pred = _predict_core(cur, hid, aid, tid, now_ts, year)
            pred_cache[key] = pred
        if not pred:
            continue
        ph = pred["pred_home"] / 100.0
        pd = pred["pred_draw"] / 100.0
        pa = pred["pred_away"] / 100.0
        fixtures.append({"hid": hid, "aid": aid,
                         "ph": ph, "pdraw": pd, "pa": pa,
                         "lam_h": pred["lam_home"], "lam_a": pred["lam_away"]})

    # 모든 팀 풀 (기존 경기 등장 + 잔여 경기 등장)
    all_teams = set(standings.keys())
    for fx in fixtures:
        all_teams.add(fx["hid"]); all_teams.add(fx["aid"])

    rank_counts = {tid_: [0] * len(all_teams) for tid_ in all_teams}  # rank_counts[team][rank-1]

    rng = random.random
    sorted_teams_for_rank = list(all_teams)

    for _ in range(n_iter):
        # 시즌 시작 standing 복제
        sim = {t: dict(standings.get(t, {"played":0,"w":0,"d":0,"l":0,"gf":0,"ga":0,"pts":0})) for t in all_teams}
        for fx in fixtures:
            r = rng()
            if r < fx["ph"]:
                outcome = "home"
            elif r < fx["ph"] + fx["pdraw"]:
                outcome = "draw"
            else:
                outcome = "away"
            # 가벼운 스코어 추정 (λ 반올림)
            hs = max(0, int(round(fx["lam_h"])))
            as_ = max(0, int(round(fx["lam_a"])))
            if outcome == "home" and hs <= as_: hs = as_ + 1
            elif outcome == "away" and as_ <= hs: as_ = hs + 1
            elif outcome == "draw": as_ = hs
            h = sim[fx["hid"]]; a = sim[fx["aid"]]
            h["gf"] += hs; h["ga"] += as_
            a["gf"] += as_; a["ga"] += hs
            if outcome == "home":
                h["w"] += 1; h["pts"] += 3; a["l"] += 1
            elif outcome == "away":
                a["w"] += 1; a["pts"] += 3; h["l"] += 1
            else:
                h["d"] += 1; h["pts"] += 1
                a["d"] += 1; a["pts"] += 1
        # 최종 순위
        ranked = sorted(sim.items(),
                        key=lambda x: (x[1]["pts"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
                        reverse=True)
        for rank_idx, (tid_, _s) in enumerate(ranked):
            rank_counts[tid_][rank_idx] += 1

    n_teams = len(all_teams)
    relegation_zone = max(1, n_teams - 1)  # 최하위만 강등 (K1 12팀 중 12위 등)
    top_zone        = 4 if league == "k1" else 2  # K1 ACL TOP4, K2 승격 TOP2
    teams_result = []
    for tid_ in all_teams:
        cnts = rank_counts[tid_]
        most_likely_rank = max(range(n_teams), key=lambda i: cnts[i]) + 1
        win_pct  = round(cnts[0] / n_iter * 100, 1)
        top_pct  = round(sum(cnts[:top_zone]) / n_iter * 100, 1)
        rel_pct  = round(sum(cnts[relegation_zone:]) / n_iter * 100, 1)
        avg_rank = round(sum((i+1) * cnts[i] for i in range(n_teams)) / n_iter, 1)
        # 팀명
        team_info = next((t for t in TEAMS if t["sofascore_id"] == tid_), None)
        teams_result.append({
            "team_id":     team_info["id"] if team_info else str(tid_),
            "name":        team_info["name"] if team_info else str(tid_),
            "current_pts": standings.get(tid_, {}).get("pts", 0),
            "current_played": standings.get(tid_, {}).get("played", 0),
            "win_pct":     win_pct,
            "top_pct":     top_pct,
            "rel_pct":     rel_pct,
            "avg_rank":    avg_rank,
            "most_likely_rank": most_likely_rank,
        })
    teams_result.sort(key=lambda t: (-t["win_pct"], -t["top_pct"], t["avg_rank"]))

    conn.close()
    result = {
        "league":          league.upper(),
        "year":            year,
        "iter":            n_iter,
        "n_teams":         n_teams,
        "remaining_games": len(fixtures),
        "top_zone":        top_zone,
        "top_zone_label":  "ACL TOP4" if league == "k1" else "승격권 TOP2",
        "rel_zone":        n_teams - relegation_zone + 1,
        "rel_zone_label":  "최하위 강등권",
        "teams":           teams_result,
        "ready":           True,
    }
    _SEASON_SIM_CACHE[cache_key] = {"ts": _time.time(), "data": result}
    return jsonify(result)


@app.route("/api/predicted-lineup")
def get_predicted_lineup():
    """
    팀 예상 출전 라인업 (가장 최근 완료 경기 + 출전시간 TOP11 기반).
    부상자 정보를 player_status.json과 cross-ref 해서 결장 표시.
    """
    team_id = request.args.get("teamId", "")
    team_info = next((t for t in TEAMS if t["id"] == team_id), None)
    if not team_info:
        return jsonify({"ready": False, "reason": "unknown_team"}), 404
    ss_id  = team_info["sofascore_id"]
    league = team_info.get("league", "K2")
    tid    = 410 if league == "K1" else 777

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    # 최근 경기 중 minutes_played 데이터가 있는 첫 경기 찾기 (최대 5경기까지 거슬러 올라감)
    cur.execute("""
        SELECT e.id, e.date_ts FROM events e
        WHERE e.tournament_id=?
          AND (e.home_team_id=? OR e.away_team_id=?)
          AND e.home_score IS NOT NULL
        ORDER BY e.date_ts DESC LIMIT 5
    """, (tid, ss_id, ss_id))
    recent_events = cur.fetchall()
    if not recent_events:
        conn.close()
        return jsonify({"ready": False, "reason": "no_recent_match"})

    last_eid = last_ts = None
    rows = []
    for re_row in recent_events:
        eid, ts = re_row["id"], re_row["date_ts"]
        cur.execute("""
            SELECT mps.player_id,
                   COALESCE(p.name_ko, mps.player_name) AS name,
                   mps.position, mps.shirt_number, mps.minutes_played, mps.rating
            FROM match_player_stats mps
            LEFT JOIN players p ON mps.player_id = p.id
            WHERE mps.event_id=? AND mps.team_id=?
              AND mps.minutes_played IS NOT NULL AND mps.minutes_played > 0
            ORDER BY mps.minutes_played DESC, mps.position
            LIMIT 11
        """, (eid, ss_id))
        rows = cur.fetchall()
        if len(rows) >= 11:
            last_eid, last_ts = eid, ts
            break

    if not rows or len(rows) < 11:
        conn.close()
        return jsonify({"ready": False, "reason": "insufficient_lineup_data"})

    statuses = _load_status()
    team_injured = {
        str(s.get("playerId")): s for s in statuses.values()
        if s.get("teamId") == team_id and s.get("status") in ("injured", "suspended", "doubtful")
    }

    starters = []
    pos_counts = {"G": 0, "D": 0, "M": 0, "F": 0}
    for r in rows:
        pid = r["player_id"]
        pos = r["position"] or "?"
        s = {
            "player_id":    pid,
            "name":         r["name"],
            "position":     pos,
            "shirt_number": r["shirt_number"],
            "minutes":      r["minutes_played"],
            "rating":       round(r["rating"], 2) if r["rating"] is not None else None,
        }
        st = team_injured.get(str(pid))
        if st:
            s["injury_status"] = st.get("status")
            s["injury_note"]   = st.get("note", "")
            s["return_date"]   = st.get("returnDate", "")
        starters.append(s)
        if pos in pos_counts:
            pos_counts[pos] += 1

    in_lineup_ids = {str(s["player_id"]) for s in starters}
    out_players = []
    for sid, st in team_injured.items():
        if sid not in in_lineup_ids:
            out_players.append({
                "player_id":   sid,
                "name":        st.get("name", ""),
                "status":      st.get("status"),
                "note":        st.get("note", ""),
                "return_date": st.get("returnDate", ""),
            })

    if pos_counts["G"] == 1 and (pos_counts["D"] + pos_counts["M"] + pos_counts["F"]) == 10:
        formation = f'{pos_counts["D"]}-{pos_counts["M"]}-{pos_counts["F"]}'
    else:
        formation = None

    conn.close()
    return jsonify({
        "ready":          True,
        "team":           team_info["name"],
        "team_id":        team_id,
        "league":         league,
        "based_on_event": last_eid,
        "based_on_date":  datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d"),
        "formation":      formation,
        "starters":       starters,
        "out_players":    out_players,
    })


# ── 경기 라인업 불러오기 ─────────────────────────────────
# SofaScore lineup 데이터를 전술판에 그대로 로드하기 위한 API.
# crawlers/crawl_lineups.py 가 채운 match_lineups 테이블을 조회한다.

def _default_labels_for_rows(rows):
    """미지 포메이션(예: 4-5-1)용 기본 라벨 생성. rows=[4,5,1] -> ['GK','D1','D2','D3','D4','M1'...'F1']."""
    labels = ["GK"]
    prefixes = ("D", "M", "F")
    for i, count in enumerate(rows):
        prefix = prefixes[min(i, len(prefixes) - 1)] if i < len(prefixes) else "A"
        if count == 1:
            labels.append(prefix)
        else:
            for j in range(count):
                labels.append(f"{prefix}{j+1}")
    return labels


def _build_formation_slots(formation, mirror=False):
    """포메이션 문자열 -> [{slot_order, x, y, label}]. mirror=True면 원정팀용(x 반전)."""
    if not formation or not all(part.isdigit() for part in formation.split("-")):
        formation = "4-4-2"  # fallback
    if formation in POSITION_LABELS:
        labels = POSITION_LABELS[formation]
    else:
        rows = [int(x) for x in formation.split("-")]
        labels = _default_labels_for_rows(rows)
    positions = compute_formation(formation)
    # 홈=좌측, 원정=우측(반전)
    slots = []
    for i, pos in enumerate(positions):
        x = round(1.0 - pos["x"], 3) if mirror else pos["x"]
        label = labels[i] if i < len(labels) else ""
        if mirror:
            if label.startswith("L"): label = "R" + label[1:]
            elif label.startswith("R"): label = "L" + label[1:]
        slots.append({"slot_order": i, "x": x, "y": pos["y"], "label": label})
    return slots


def _team_info_by_sofascore_id(ss_id):
    t = next((t for t in TEAMS if t.get("sofascore_id") == ss_id), None)
    if not t:
        return None
    return {
        "slug":        t["id"],
        "name":        t["name"],
        "short":       t["short"],
        "league":      t.get("league"),
        "emblem":      t.get("emblem"),
        "primary":     t.get("primary"),
        "secondary":   t.get("secondary"),
        "accent":      t.get("accent"),
    }


@app.route("/api/matches-by-date")
def matches_by_date():
    """
    특정 날짜에 치러진 경기 목록 반환.
    쿼리: ?date=YYYY-MM-DD  (없으면 라인업이 저장된 전체 경기)
        ?has_lineup=1     (라인업 데이터가 있는 경기만)
    """
    date_str   = request.args.get("date", "").strip()
    has_lineup = request.args.get("has_lineup") == "1"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    where   = []
    params  = []
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            conn.close()
            return jsonify({"error": "invalid date"}), 400
        start_ts = int(dt.timestamp())
        end_ts   = start_ts + 86400
        where.append("e.date_ts >= ? AND e.date_ts < ?")
        params.extend([start_ts, end_ts])

    if has_lineup:
        where.append("EXISTS (SELECT 1 FROM match_lineups m WHERE m.event_id = e.id)")

    sql = """
        SELECT e.id, e.home_team_id, e.home_team_name, e.away_team_id, e.away_team_name,
               e.date_ts, e.home_score, e.away_score, e.tournament_id,
               (SELECT 1 FROM match_lineups m WHERE m.event_id = e.id LIMIT 1) AS has_lu
        FROM events e
        WHERE e.tournament_id IN (410, 777)
    """
    if where:
        sql += " AND " + " AND ".join(where)
    sql += " ORDER BY e.date_ts ASC, e.id ASC"
    cur.execute(sql, params)
    rows = cur.fetchall()

    out = []
    for r in rows:
        ts = r["date_ts"] or 0
        dt = datetime.fromtimestamp(ts) if ts else None
        home_info = _team_info_by_sofascore_id(r["home_team_id"])
        away_info = _team_info_by_sofascore_id(r["away_team_id"])
        out.append({
            "event_id":      r["id"],
            "date_ts":       ts,
            "date":          dt.strftime("%Y-%m-%d") if dt else "",
            "kickoff":       dt.strftime("%H:%M") if dt else "",
            "tournament_id": r["tournament_id"],
            "league":        "K1" if r["tournament_id"] == 410 else "K2",
            "home_score":    r["home_score"],
            "away_score":    r["away_score"],
            "has_lineup":    bool(r["has_lu"]),
            "home": {
                "team_id":   r["home_team_id"],
                "name":      r["home_team_name"],
                "slug":      home_info["slug"] if home_info else None,
                "short":     home_info["short"] if home_info else (r["home_team_name"] or ""),
                "emblem":    home_info["emblem"] if home_info else None,
            },
            "away": {
                "team_id":   r["away_team_id"],
                "name":      r["away_team_name"],
                "slug":      away_info["slug"] if away_info else None,
                "short":     away_info["short"] if away_info else (r["away_team_name"] or ""),
                "emblem":    away_info["emblem"] if away_info else None,
            },
        })

    conn.close()
    return jsonify(out)


@app.route("/api/matches-latest-lineup-date")
def matches_latest_lineup_date():
    """라인업이 저장된 가장 최근 경기일(YYYY-MM-DD) 반환. 프론트 기본값용."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT MAX(e.date_ts) FROM events e
        WHERE EXISTS (SELECT 1 FROM match_lineups m WHERE m.event_id = e.id)
    """).fetchone()
    conn.close()
    ts = row[0] if row else None
    if not ts:
        return jsonify({"date": None})
    return jsonify({"date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d")})


@app.route("/api/match-lineup")
def match_lineup():
    """
    특정 경기의 홈/원정 라인업(포메이션 + 선발 + 교체) 반환.
    전술판이 그대로 적용할 수 있도록 슬롯 좌표까지 계산해서 내려준다.
    쿼리:
      - ?event_id=<int>                                (SofaScore event id 직접 지정)
      - ?date=YYYY-MM-DD(또는 YYYY.MM.DD)&home_slug=X&away_slug=Y
        (K리그 일정 패널 등 event_id 없을 때 팀 슬러그로 조회)
    """
    event_id = request.args.get("event_id", "").strip()
    date_str = request.args.get("date", "").strip()
    home_slug = request.args.get("home_slug", "").strip()
    away_slug = request.args.get("away_slug", "").strip()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    ev = None
    if event_id:
        try:
            event_id = int(event_id)
        except ValueError:
            conn.close()
            return jsonify({"error": "event_id must be int"}), 400
        ev = cur.execute("""
            SELECT id, home_team_id, home_team_name, away_team_id, away_team_name,
                   date_ts, home_score, away_score, tournament_id
            FROM events WHERE id = ?
        """, (event_id,)).fetchone()
    elif date_str and home_slug and away_slug:
        # date: "YYYY-MM-DD" 또는 "YYYY.MM.DD" 허용
        dt_str = date_str.replace(".", "-")
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
        except ValueError:
            conn.close()
            return jsonify({"error": "invalid date"}), 400
        start_ts, end_ts = int(dt.timestamp()), int(dt.timestamp()) + 86400
        home_team = next((t for t in TEAMS if t["id"] == home_slug), None)
        away_team = next((t for t in TEAMS if t["id"] == away_slug), None)
        if not home_team or not away_team:
            conn.close()
            return jsonify({"error": "unknown team slug"}), 400
        ev = cur.execute("""
            SELECT id, home_team_id, home_team_name, away_team_id, away_team_name,
                   date_ts, home_score, away_score, tournament_id
            FROM events
            WHERE date_ts >= ? AND date_ts < ?
              AND home_team_id = ? AND away_team_id = ?
            LIMIT 1
        """, (start_ts, end_ts, home_team["sofascore_id"], away_team["sofascore_id"])).fetchone()
    else:
        conn.close()
        return jsonify({"error": "event_id or (date+home_slug+away_slug) required"}), 400

    if not ev:
        conn.close()
        return jsonify({"ready": False, "reason": "event_not_found"}), 404

    resolved_event_id = ev["id"]
    lu_rows = cur.execute("""
        SELECT ml.is_home, ml.team_id, ml.formation, ml.player_id, ml.player_name,
               ml.shirt_number, ml.position, ml.is_starter, ml.slot_order,
               ml.confirmed,
               COALESCE(p.name_ko, ml.player_name) AS name_display,
               p.height
        FROM match_lineups ml
        LEFT JOIN players p ON p.id = ml.player_id
        WHERE ml.event_id = ?
        ORDER BY ml.is_home DESC, ml.is_starter DESC, ml.slot_order ASC
    """, (resolved_event_id,)).fetchall()

    if not lu_rows:
        conn.close()
        return jsonify({"ready": False, "reason": "no_lineup", "event_id": resolved_event_id})

    def build_side(is_home_flag, ss_team_id, ss_team_name):
        rows = [r for r in lu_rows if r["is_home"] == is_home_flag]
        if not rows:
            return None
        formation = next((r["formation"] for r in rows if r["formation"]), None)
        slots     = _build_formation_slots(formation, mirror=(not is_home_flag))

        starters, subs = [], []
        for r in rows:
            p = {
                "player_id":    r["player_id"],
                "name":         r["name_display"] or r["player_name"] or "",
                "name_raw":     r["player_name"] or "",
                "shirt_number": r["shirt_number"],
                "position":     r["position"],
                "height":       r["height"],
            }
            if r["is_starter"]:
                p["slot_order"] = r["slot_order"]
                starters.append(p)
            else:
                subs.append(p)

        team_info = _team_info_by_sofascore_id(ss_team_id) or {}
        return {
            "team_id":    ss_team_id,
            "slug":       team_info.get("slug"),
            "name":       team_info.get("name") or ss_team_name,
            "short":      team_info.get("short") or ss_team_name,
            "emblem":     team_info.get("emblem"),
            "formation":  formation or "4-4-2",
            "slots":      slots,
            "starters":   starters,
            "subs":       subs,
        }

    confirmed = any(r["confirmed"] for r in lu_rows)
    home = build_side(1, ev["home_team_id"], ev["home_team_name"])
    away = build_side(0, ev["away_team_id"], ev["away_team_name"])

    conn.close()
    ts = ev["date_ts"] or 0
    return jsonify({
        "ready":      True,
        "event_id":   ev["id"],
        "date_ts":    ts,
        "date":       datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "",
        "kickoff":    datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "",
        "home_score": ev["home_score"],
        "away_score": ev["away_score"],
        "league":     "K1" if ev["tournament_id"] == 410 else "K2",
        "confirmed":  confirmed,
        "home":       home,
        "away":       away,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
