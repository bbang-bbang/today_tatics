import json
import os
import uuid
from datetime import datetime

from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

SAVES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
os.makedirs(SAVES_DIR, exist_ok=True)

# ── K리그 팀 데이터 ──────────────────────────────────────
TEAMS = [
    # K1
    {"id": "ulsan",    "name": "울산 HD FC",       "short": "울산",  "league": "K1", "primary": "#004a9f", "secondary": "#ffffff", "accent": "#f2a900"},
    {"id": "jeonbuk",  "name": "전북 현대 모터스",  "short": "전북",  "league": "K1", "primary": "#006b3f", "secondary": "#ffffff", "accent": "#ffd700"},
    {"id": "pohang",   "name": "포항 스틸러스",     "short": "포항",  "league": "K1", "primary": "#c8102e", "secondary": "#000000", "accent": "#ffffff"},
    {"id": "jeju",     "name": "제주 유나이티드",    "short": "제주",  "league": "K1", "primary": "#f47920", "secondary": "#000000", "accent": "#ffffff"},
    {"id": "incheon",  "name": "인천 유나이티드",    "short": "인천",  "league": "K1", "primary": "#004b87", "secondary": "#d4a843", "accent": "#ffffff"},
    {"id": "suwon_fc", "name": "수원 FC",          "short": "수원FC", "league": "K1", "primary": "#e30613", "secondary": "#1d2c6b", "accent": "#ffffff"},
    {"id": "daegu",    "name": "대구 FC",          "short": "대구",  "league": "K1", "primary": "#1e3a8a", "secondary": "#dc2626", "accent": "#ffffff"},
    {"id": "gangwon",  "name": "강원 FC",          "short": "강원",  "league": "K1", "primary": "#e30613", "secondary": "#ffffff", "accent": "#f47920"},
    {"id": "gwangju",  "name": "광주 FC",          "short": "광주",  "league": "K1", "primary": "#ffe600", "secondary": "#006b3f", "accent": "#000000"},
    {"id": "daejeon",  "name": "대전 하나 시티즌",   "short": "대전",  "league": "K1", "primary": "#6b2fa0", "secondary": "#e30613", "accent": "#ffffff"},
    {"id": "fcseoul",  "name": "FC 서울",          "short": "서울",  "league": "K1", "primary": "#c8102e", "secondary": "#000000", "accent": "#ffd700"},
    {"id": "gimcheon", "name": "김천 상무 FC",      "short": "김천",  "league": "K1", "primary": "#c8102e", "secondary": "#1e3a8a", "accent": "#ffffff"},
    # K2
    {"id": "busan",    "name": "부산 아이파크",     "short": "부산",  "league": "K2", "primary": "#f47920", "secondary": "#1e3a8a", "accent": "#ffffff"},
    {"id": "asan",     "name": "충남 아산 FC",      "short": "아산",  "league": "K2", "primary": "#004b87", "secondary": "#ffffff", "accent": "#e30613"},
    {"id": "anyang",   "name": "FC 안양",          "short": "안양",  "league": "K2", "primary": "#6b2fa0", "secondary": "#ffffff", "accent": "#ffd700"},
    {"id": "jeonnam",  "name": "전남 드래곤즈",     "short": "전남",  "league": "K2", "primary": "#ffe600", "secondary": "#006b3f", "accent": "#000000"},
    {"id": "bucheon",  "name": "부천 FC 1995",     "short": "부천",  "league": "K2", "primary": "#c8102e", "secondary": "#1e3a8a", "accent": "#ffffff"},
    {"id": "seouland", "name": "서울 이랜드 FC",    "short": "이랜드", "league": "K2", "primary": "#e30613", "secondary": "#ffffff", "accent": "#1e3a8a"},
    {"id": "ansan",    "name": "안산 그리너스",      "short": "안산",  "league": "K2", "primary": "#006b3f", "secondary": "#ffffff", "accent": "#ffd700"},
    {"id": "cheongju", "name": "충북 청주 FC",      "short": "청주",  "league": "K2", "primary": "#1e3a8a", "secondary": "#c8102e", "accent": "#ffffff"},
    {"id": "seongnam", "name": "성남 FC",          "short": "성남",  "league": "K2", "primary": "#000000", "secondary": "#ffe600", "accent": "#ffffff"},
    {"id": "gimpo",    "name": "김포 FC",          "short": "김포",  "league": "K2", "primary": "#004b87", "secondary": "#c9a84c", "accent": "#ffffff"},
    {"id": "cheonan",  "name": "천안 시티 FC",      "short": "천안",  "league": "K2", "primary": "#004b87", "secondary": "#ffffff", "accent": "#e30613"},
]


@app.route("/api/teams")
def teams():
    return jsonify(TEAMS)


def compute_formation(formation_str):
    """포메이션 문자열을 파싱하여 선수 좌표(0~1 정규화)를 계산한다."""
    rows = [int(x) for x in formation_str.split("-")]
    positions = []

    # 골키퍼
    positions.append({"x": 0.06, "y": 0.5})

    num_rows = len(rows)
    for row_idx, count in enumerate(rows):
        x = 0.15 + (row_idx / max(num_rows - 1, 1)) * 0.33
        for player_idx in range(count):
            if count == 1:
                y = 0.5
            else:
                margin = 0.1
                y = margin + (player_idx / (count - 1)) * (1.0 - 2 * margin)
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

FORMATIONS = {}
for name in POSITION_LABELS:
    team_a = compute_formation(name)
    team_b = [{"x": round(1.0 - p["x"], 3), "y": p["y"]} for p in compute_formation(name)]
    FORMATIONS[name] = {
        "teamA": team_a,
        "teamB": team_b,
        "labelsA": POSITION_LABELS[name],
        "labelsB": POSITION_LABELS[name],
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
        "arrows": body.get("arrows", []),
        "createdAt": now,
        "updatedAt": now,
    }
    fpath = os.path.join(SAVES_DIR, f"{save_id}.json")
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify(data), 201


@app.route("/api/saves/<save_id>", methods=["GET"])
def get_save(save_id):
    fpath = os.path.join(SAVES_DIR, f"{save_id}.json")
    if not os.path.exists(fpath):
        return jsonify({"error": "Not found"}), 404
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/saves/<save_id>", methods=["PUT"])
def update_save(save_id):
    fpath = os.path.join(SAVES_DIR, f"{save_id}.json")
    if not os.path.exists(fpath):
        return jsonify({"error": "Not found"}), 404
    with open(fpath, "r", encoding="utf-8") as f:
        existing = json.load(f)
    body = request.get_json()
    existing["name"] = body.get("name", existing["name"])
    existing["formation"] = body.get("formation", existing["formation"])
    existing["players"] = body.get("players", existing["players"])
    existing["arrows"] = body.get("arrows", existing["arrows"])
    existing["updatedAt"] = datetime.now().isoformat()
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return jsonify(existing)


@app.route("/api/saves/<save_id>", methods=["DELETE"])
def delete_save(save_id):
    fpath = os.path.join(SAVES_DIR, f"{save_id}.json")
    if not os.path.exists(fpath):
        return jsonify({"error": "Not found"}), 404
    os.remove(fpath)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
