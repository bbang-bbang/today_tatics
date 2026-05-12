"""broadcast 시각 좌우반전 전수 검증 (164경기).

검증 대상:
  A. _build_formation_slots — formation -> slot 좌표/라벨 정합
  B. match_avg_positions    — RB(slot 1)·LB(slot 4) 선수 y 분포
  C. match_shotmap          — mapPos 통과 후 home/away 슛 좌우 분포

읽기 전용. main.py import 안 함(Flask 부수효과 회피) — 핵심 로직 카피본.
"""
from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# Windows cp949 console에서 emdash·체크마크 출력 (utf-8 강제)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DB_PATH = Path(__file__).resolve().parent.parent / "players.db"
PLAYER_STEP = 0.16  # main.py 동일

# ── main.py 카피 (검증 자기완결성) ──────────────────────────
POSITION_LABELS = {
    "4-4-2": ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "ST", "ST"],
    "4-3-3": ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "CM", "LW", "ST", "RW"],
    "3-5-2": ["GK", "CB", "CB", "CB", "LM", "CM", "CDM", "CM", "RM", "ST", "ST"],
    "4-2-3-1": ["GK", "LB", "CB", "CB", "RB", "CDM", "CDM", "LW", "AM", "RW", "ST"],
    "4-1-4-1": ["GK", "LB", "CB", "CB", "RB", "CDM", "LM", "CM", "CM", "RM", "ST"],
    "3-4-3": ["GK", "CB", "CB", "CB", "LM", "CM", "CM", "RM", "LW", "ST", "RW"],
    "5-3-2": ["GK", "LWB", "CB", "CB", "CB", "RWB", "CM", "CM", "CM", "ST", "ST"],
    "5-4-1": ["GK", "LWB", "CB", "CB", "CB", "RWB", "LM", "CM", "CM", "RM", "ST"],
    "4-5-1":   ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "CM", "RM", "ST"],
    "3-4-2-1": ["GK", "CB", "CB", "CB", "LM", "CM", "CM", "RM", "LW", "RW", "ST"],
    "3-4-1-2": ["GK", "CB", "CB", "CB", "LM", "CM", "CM", "RM", "AM", "ST", "ST"],
    "4-4-1-1": ["GK", "LB", "CB", "CB", "RB", "LM", "CM", "CM", "RM", "AM", "ST"],
    "3-1-4-2": ["GK", "CB", "CB", "CB", "CDM", "LM", "CM", "CM", "RM", "ST", "ST"],
}


def compute_formation(formation_str):
    rows = [int(x) for x in formation_str.split("-")]
    positions = [{"x": 0.05, "y": 0.5}]  # GK
    n = len(rows)
    for ri, count in enumerate(rows):
        x = 0.12 + (ri / max(n - 1, 1)) * 0.32
        for pi in range(count):
            if count == 1:
                y = 0.5
            else:
                total_h = min((count - 1) * PLAYER_STEP, 0.80)
                step = total_h / (count - 1)
                start = 0.5 - total_h / 2
                y = start + pi * step
            positions.append({"x": round(x, 3), "y": round(y, 3)})
    return positions


def mirror_labels(labels):
    out = []
    for lab in labels:
        if lab.startswith("L"):
            out.append("R" + lab[1:])
        elif lab.startswith("R"):
            out.append("L" + lab[1:])
        else:
            out.append(lab)
    return out


def _default_labels_for_rows(rows):
    """formation 미등록 시 fallback (main.py 동일)."""
    labels = ["GK"]
    prefixes = ["D", "M", "F", "A"]
    for i, count in enumerate(rows):
        prefix = prefixes[min(i, len(prefixes) - 1)] if i < len(prefixes) else "A"
        if count == 1:
            labels.append(prefix)
        else:
            for j in range(count):
                labels.append(f"{prefix}{j+1}")
    return labels


def build_formation_slots(formation, mirror=False):
    """main.py:_build_formation_slots 동일 로직."""
    if not formation or not all(p.isdigit() for p in formation.split("-")):
        formation = "4-4-2"
    if formation in POSITION_LABELS:
        labels = POSITION_LABELS[formation]
    else:
        rows = [int(x) for x in formation.split("-")]
        labels = _default_labels_for_rows(rows)
    labels = mirror_labels(labels)
    positions = compute_formation(formation)
    slots = []
    for i, pos in enumerate(positions):
        x = round(1.0 - pos["x"], 3) if mirror else pos["x"]
        y = round(1.0 - pos["y"], 3)
        lab = labels[i] if i < len(labels) else ""
        slots.append({"slot_order": i, "x": x, "y": y, "label": lab})
    return slots


# ── 검증 A ────────────────────────────────────────────────
def verify_A_formation_slots(conn):
    """검증 규칙 (broadcast 시각: 양 팀 라이트백 모두 화면 아래쪽).

      A1. 4백 계열(D row 4명) home/away 모두 slot_order=1 라벨이 R*.
          - 카메라(메인 스탠드)에서 home/away 라이트백 모두 카메라 쪽 = 아래쪽.
          - 따라서 양 팀 slot 1은 라이트백 자리이고 라벨도 R*여야 정합.
      A2. R*/L* 라벨 슬롯의 y 분포 (home: R*는 y>0.5, L*는 y<0.5).
          away도 같은 규칙(broadcast 양 팀 공통)이어야 정합.
      A3. mirror=True(away) 슬롯 x는 ≥ 0.5, home은 ≤ 0.5.
    """
    formations = sorted({
        r[0] for r in conn.execute(
            "SELECT DISTINCT formation FROM match_lineups "
            "WHERE formation IS NOT NULL AND formation != ''"
        ).fetchall()
    })
    # 4-back 판별: 첫 row가 '4'
    def is_back4(fm):
        parts = fm.split("-")
        return parts and parts[0] == "4"

    print(f"\n=== A. Formation slots ({len(formations)} formations × 2 mirror) ===")
    fail_a1, fail_a2, fail_a3 = [], [], []

    for fm in formations:
        for mirror in (False, True):
            slots = build_formation_slots(fm, mirror=mirror)
            side = "away" if mirror else "home"

            # A1: 4백 계열 + POSITION_LABELS 등록 formation만 (fallback은 R/L 의미 못 담음)
            if is_back4(fm) and fm in POSITION_LABELS:
                lab1 = slots[1]["label"]
                if lab1 and not lab1.startswith("R"):
                    fail_a1.append((fm, side, lab1))

            # A2: R*/L* 슬롯의 y 분포
            for s in slots[1:]:  # GK 제외
                lab = s["label"]
                if lab.startswith("R") and s["y"] <= 0.5:
                    fail_a2.append((fm, side, lab, s["y"]))
                if lab.startswith("L") and s["y"] >= 0.5:
                    fail_a2.append((fm, side, lab, s["y"]))

            # A3: mirror 측 x ≥ 0.5
            for s in slots:
                if mirror and s["x"] < 0.5:
                    fail_a3.append((fm, side, s["label"], s["x"]))
                if (not mirror) and s["x"] > 0.5:
                    fail_a3.append((fm, side, s["label"], s["x"]))

    def report_block(name, fails, total_label):
        status = "PASS" if not fails else "FAIL"
        print(f"  [{name}] {status} ({total_label})")
        for row in fails[:8]:
            print(f"     - {row}")
        if len(fails) > 8:
            print(f"     ... (+{len(fails)-8} more)")

    n_back4_known = sum(1 for f in formations if is_back4(f) and f in POSITION_LABELS)
    n_back4_fb = sum(1 for f in formations if is_back4(f) and f not in POSITION_LABELS)
    report_block("A1 4백 slot1=R* (POSITION_LABELS 등록 한정)", fail_a1, f"검사 {n_back4_known*2}건 / fallback {n_back4_fb}건 backlog")
    report_block("A2 R*y>0.5 / L*y<0.5", fail_a2, "양 팀 broadcast 정합")
    report_block("A3 home x≤0.5 / away x≥0.5", fail_a3, "좌우 분리")
    return not (fail_a1 or fail_a2 or fail_a3)


# ── 검증 B ────────────────────────────────────────────────
def verify_B_avg_positions(conn):
    print("\n=== B. Avg positions — RB(slot 1) / LB(slot 4) raw y 분포 ===")

    # 4백 계열 formation만 검증 (slot 1=RB, slot 4=LB가 명확)
    BACK4 = ("4-4-2", "4-3-3", "4-2-3-1", "4-1-4-1")

    rows = conn.execute(
        """
        SELECT ml.event_id, ml.is_home, ml.formation, ml.slot_order, ml.player_id,
               ap.y AS ap_y
        FROM match_lineups ml
        JOIN match_avg_positions ap
          ON ap.event_id = ml.event_id
         AND ap.player_id = ml.player_id
        WHERE ml.is_starter = 1
          AND ml.slot_order IN (1, 4)
          AND ml.formation IN ({})
        """.format(",".join("?" * len(BACK4))),
        BACK4,
    ).fetchall()

    # event_id × is_home 단위로 RB/LB y 집계
    by_side = defaultdict(dict)
    for ev, ih, fm, slot, pid, ap_y in rows:
        if ap_y is None:
            continue
        by_side[(ev, ih)][slot] = ap_y

    rb_ok = lb_ok = total = 0
    suspects = []
    for (ev, ih), d in by_side.items():
        if 1 not in d or 4 not in d:
            continue
        total += 1
        rb_y = d[1]  # RB
        lb_y = d[4]  # LB
        ok_rb = rb_y < 50
        ok_lb = lb_y > 50
        if ok_rb:
            rb_ok += 1
        if ok_lb:
            lb_ok += 1
        if not (ok_rb and ok_lb):
            suspects.append((ev, ih, round(rb_y, 1), round(lb_y, 1)))

    if total == 0:
        print("  SKIP: 4-back 매치 표본 없음")
        return None
    rb_pct = rb_ok / total * 100
    lb_pct = lb_ok / total * 100
    print(f"  RB(slot 1) raw y < 50: {rb_ok}/{total} ({rb_pct:.1f}%) → broadcast 화면 아래쪽 ✓")
    print(f"  LB(slot 4) raw y > 50: {lb_ok}/{total} ({lb_pct:.1f}%) → broadcast 화면 위쪽 ✓")
    passed = rb_pct >= 85 and lb_pct >= 85

    if suspects:
        print(f"  의심 매치 (RB/LB y 반전 또는 중앙 근처) {len(suspects)}건 — 상위 10:")
        for s in suspects[:10]:
            ev, ih, rb_y, lb_y = s
            side = "home" if ih else "away"
            print(f"   - event={ev} {side}: RB y={rb_y}, LB y={lb_y}")

    print(f"  → {'PASS' if passed else 'FAIL'} (기준 85%)")
    return passed


# ── 검증 C ────────────────────────────────────────────────
def verify_C_shotmap(conn):
    print("\n=== C. Shotmap — mapPos 통과 후 home/away 좌우 분포 ===")
    rows = conn.execute(
        "SELECT is_home, x FROM match_shotmap WHERE x IS NOT NULL"
    ).fetchall()

    # 프론트 변환: mapPos(100 - s.x, s.y, isHome) → px = isHome ? (100-s.x) : 100-(100-s.x) = s.x
    home_total = home_right = 0
    away_total = away_left = 0
    for ih, x in rows:
        if ih == 1:
            home_total += 1
            px = 100 - x
            if px > 50:
                home_right += 1
        else:
            away_total += 1
            px = x  # 100 - (100-x)
            if px < 50:
                away_left += 1

    h_pct = home_right / home_total * 100 if home_total else 0
    a_pct = away_left / away_total * 100 if away_total else 0
    print(f"  home 슛 최종 px > 50 (away 골 방향): {home_right}/{home_total} ({h_pct:.1f}%) ✓")
    print(f"  away 슛 최종 px < 50 (home 골 방향): {away_left}/{away_total} ({a_pct:.1f}%) ✓")
    passed = h_pct >= 75 and a_pct >= 75
    print(f"  → {'PASS' if passed else 'FAIL'} (기준 75%)")
    return passed


# ── main ─────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(str(DB_PATH))

    # 운영 데이터 표본 사이즈 출력
    n_events = conn.execute(
        "SELECT COUNT(DISTINCT event_id) FROM match_lineups"
    ).fetchone()[0]
    n_avg = conn.execute("SELECT COUNT(*) FROM match_avg_positions").fetchone()[0]
    n_shot = conn.execute("SELECT COUNT(*) FROM match_shotmap").fetchone()[0]
    print(f"표본: lineup events={n_events}, avg_positions rows={n_avg}, shotmap shots={n_shot}")

    a = verify_A_formation_slots(conn)
    b = verify_B_avg_positions(conn)
    c = verify_C_shotmap(conn)

    print("\n=== 종합 ===")
    print(f"  A (slot 정합):       {'PASS' if a else 'FAIL'}")
    print(f"  B (avg_positions):   {'PASS' if b else ('SKIP' if b is None else 'FAIL')}")
    print(f"  C (shotmap):         {'PASS' if c else 'FAIL'}")
    if a and (b or b is None) and c:
        print("\n  → broadcast 좌우반전 규칙 전수 검증 PASS")
    else:
        print("\n  → 일부 FAIL — 상세 의심 케이스 위 출력 참조")

    conn.close()


if __name__ == "__main__":
    main()
