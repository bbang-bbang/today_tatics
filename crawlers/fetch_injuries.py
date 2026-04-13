#!/usr/bin/env python3
"""
SofaScore 선수 부상/결장 정보 수집기
- 대상: K리그1/K리그2 전 팀 (--team, --league 옵션)
- 엔드포인트: /api/v1/team/{team_id}/players
- 저장: data/player_status.json
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_FILE = os.path.join(BASE_DIR, "data", "player_status.json")
DELAY       = 0.8

# K리그 팀 목록 (sofascore_id → (팀명, app_team_id))
K1_TEAMS = {
    7653: ("울산", "ulsan"), 7650: ("포항", "pohang"), 7649: ("제주", "jeju"),
    6908: ("전북", "jeonbuk"), 7646: ("서울", "fcseoul"), 7645: ("대전", "daejeon"),
    7648: ("인천", "incheon"), 34220: ("강원", "gangwon"), 48912: ("광주", "gwangju"),
    92539: ("부천", "bucheon"), 32675: ("안양", "anyang"), 7647: ("김천", "gimcheon"),
}
K2_TEAMS = {
    7652: ("수원삼성", "suwon"), 7642: ("부산", "busan"), 7643: ("전남", "jeonnam"),
    7651: ("성남", "seongnam"), 7644: ("대구", "daegu"), 22020: ("경남", "gyeongnam"),
    41261: ("수원FC", "suwon_fc"), 189422: ("이랜드", "seouland"), 248375: ("안산", "ansan"),
    339827: ("아산", "asan"), 195172: ("김포", "gimpo"), 314293: ("청주", "cheongju"),
    41263: ("천안", "cheonan"), 195174: ("화성", "hwaseong"), 314294: ("파주", "paju"),
    41260: ("김해", "gimhae"), 41266: ("용인", "yongin"),
}
ALL_TEAMS = {**K1_TEAMS, **K2_TEAMS}


def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


async def api_fetch(page, path, retries=2):
    for attempt in range(retries + 1):
        try:
            result = await page.evaluate(f"""() =>
                fetch('{path}')
                .then(r => r.ok ? r.json() : r.status)
                .catch(e => ({{error: e.message}}))
            """)
            return result
        except Exception as e:
            if attempt < retries:
                try:
                    await page.goto(
                        "https://www.sofascore.com/",
                        wait_until="domcontentloaded", timeout=60000
                    )
                    await asyncio.sleep(2)
                except Exception:
                    pass
            else:
                return {"error": str(e)}


async def fetch_team_injuries(page, ss_id, team_name, app_team_id):
    """한 팀의 선수 부상/결장 정보를 수집한다.
    SofaScore injury 객체 구조:
      { reason: "Hamstring Injury", status: "out"|"dayToDay"|"sideline",
        expectedReturn: int, startDateTimestamp, endDateTimestamp,
        expectedReturnDateData: {month, year} }
    """
    data = await api_fetch(page, f"/api/v1/team/{ss_id}/players")
    if not isinstance(data, dict):
        log(f"  [{team_name}] API 오류: {data}")
        return []

    players = data.get("players", [])
    injured = []

    for entry in players:
        player = entry.get("player", {})
        pid = player.get("id")
        name = player.get("shortName", "") or player.get("name", "")
        injury = player.get("injury")

        if not injury or not isinstance(injury, dict):
            continue

        # 상태 결정
        inj_status = injury.get("status", "")  # "out", "dayToDay", "sideline"
        reason = injury.get("reason", "")

        if "suspend" in reason.lower() or "red card" in reason.lower():
            status = "suspended"
        elif inj_status == "dayToDay":
            status = "doubtful"
        else:
            status = "injured"

        # 복귀 예정일
        return_date = ""
        ret_data = injury.get("expectedReturnDateData")
        if ret_data and ret_data.get("year") and ret_data.get("month"):
            return_date = f"{ret_data['year']}-{ret_data['month']:02d}"
        elif injury.get("endDateTimestamp"):
            from datetime import datetime as _dt
            try:
                end = _dt.fromtimestamp(injury["endDateTimestamp"])
                return_date = end.strftime("%Y-%m-%d")
            except Exception:
                pass

        injured.append({
            "playerId": str(pid),
            "teamId": app_team_id,
            "name": name,
            "status": status,
            "note": reason,
            "returnDate": return_date,
            "source": "sofascore",
            "updatedAt": datetime.now().isoformat(),
        })

    return injured


async def main():
    parser = argparse.ArgumentParser(description="K리그 선수 부상 정보 수집 (SofaScore)")
    parser.add_argument("--team", type=int, default=None,
                        help="특정 팀 sofascore_id")
    parser.add_argument("--league", choices=["K1", "K2", "all"], default="all",
                        help="리그 선택 (기본: all)")
    args = parser.parse_args()

    # 수집 대상
    if args.team:
        if args.team in ALL_TEAMS:
            targets = {args.team: ALL_TEAMS[args.team]}
        else:
            log(f"알 수 없는 팀 ID: {args.team}")
            return
    elif args.league == "K1":
        targets = K1_TEAMS
    elif args.league == "K2":
        targets = K2_TEAMS
    else:
        targets = ALL_TEAMS

    log(f"부상 정보 수집 시작 — {len(targets)}팀")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.sofascore.com/",
            }
        )
        page = await ctx.new_page()

        log("sofascore 접속 중...")
        await page.goto(
            "https://www.sofascore.com/",
            wait_until="domcontentloaded", timeout=60000
        )
        await asyncio.sleep(3)
        log("세션 준비 완료\n")

        # 기존 상태 파일 로드 (수동 등록분 보존)
        existing = {}
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)

        # 수동 등록(source 없음)은 보존, sofascore 수집분은 갱신
        manual_entries = {k: v for k, v in existing.items() if v.get("source") != "sofascore"}
        auto_entries = {}

        total_injured = 0
        for ss_id, (team_name, app_team_id) in targets.items():
            injured = await fetch_team_injuries(page, ss_id, team_name, app_team_id)
            for entry in injured:
                auto_entries[entry["playerId"]] = entry
            count = len(injured)
            total_injured += count
            mark = f"({count}명 부상/결장)" if count > 0 else "(전원 정상)"
            log(f"  [{team_name:6s}] {mark}")
            await asyncio.sleep(DELAY)

        await browser.close()

    # 수동 + 자동 병합 (수동이 우선)
    merged = {**auto_entries, **manual_entries}

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    log(f"\n완료! 총 {total_injured}명 부상/결장 수집")
    log(f"  자동(SofaScore): {len(auto_entries)}명")
    log(f"  수동(유지): {len(manual_entries)}명")
    log(f"  저장: {STATUS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
