# Backlog — Today Tactics

> 작업 끝나면 이 파일을 업데이트해 항목을 옮기거나 삭제. 시간순 기록은 `work-log-YYYY-MM-DD.md`.

---

## 🔴 P1 — 가치 큰 단기 작업

(없음 — 5/7 세션으로 자동화 + 데이터 정합성 + UI 핵심 처리됨)

---

## 🟡 P2 — 시간 날 때 처리

### [ ] 5/22 K1 미래 매치 1건 매칭 실패
**왜**: replace_synthetic_events.py 첫 실행 시 1건 매칭 실패 (Jeonbuk vs Daejeon, ts=1771642800). 미래 매치라 SofaScore 미등록.
**무엇**: 5/22 이후 또는 경기 종료 후 재실행
```bash
python crawlers/replace_synthetic_events.py
```
**비용**: 30초

---

### [ ] K1 xG 데이터 백필
**왜**: K1 `match_player_stats.expected_goals` 0건. SQL fallback으로 실제 골 사용 중. xG 보유 시 모델 정확도 +6%p 추정.
**무엇**: `crawlers/build_k1_xg.py` 재실행
**비용**: 1~3시간 (Playwright 안정성 변수)
**효과**: K1 1X2 적중률 44% → 50%+ 가능성

---

### [ ] 5/5 K1 R11 3매치 히트맵
**왜**: 강원-포항, 대전-인천, 김천-울산 — SofaScore 처리 지연으로 0 pts.
**무엇**: 다음 월요일 cron이 STEP 6에서 자동 재시도. 안 될 경우 수동:
```bash
python crawlers/fetch_event_heatmap.py 15372989 15372991 15372995
```
**비용**: 1분

---

### [ ] 가비아 방화벽 SSH 화이트리스트
**왜**: 봇 트래픽 0으로 만들 수 있음.
**조건**: 본인 공인 IP 고정 여부 확인 필요. 동적이면 안 함 (락아웃 위험).

---

### [ ] 매치 상세 — 카드 통계 노출
**왜**: 카드 데이터 6,988건이 인사이트 패널에만 노출. 매치 상세에 양 팀 카드 추세도 보여주면 유용.
**무엇**: prediction.js render()에서 home.cards / away.cards 표시. /api/match-prediction에서 card_events JOIN.
**비용**: 30분

---

### [ ] 라운드 변경/사이드바 메뉴 변경 시 매치 캐시 초기화
**왜**: 현재 K1↔K2 탭 전환 시만 자동 닫기. 같은 리그 내 라운드 탭 변경, 사이드바 다른 메뉴(인사이트/스쿼드 등) 클릭 시도 닫기 원할 가능성.
**무엇**: prediction.js `clearMatchContext()` 호출 지점 추가.
**비용**: 10분 (사용자 의향 확인 후)

---

## ⚫ P3 — 의식적으로 안 함

- ❌ Git history rewrite (PM 권고: ROI 음수)
- ❌ history.md 과거 노출 정리 (rewrite 없이 의미 X)
- ❌ 2020 시즌 17매치 avg_positions/shotmap/lineup 미보유 — SofaScore 자체 부재라 회복 불가
- ❌ 패스맵 (선수 간 패스 네트워크) — SofaScore + K리그 포털 둘 다 미공개

---

## 📌 운영 메모

- **서버 배포**: `git push` → 서버 `git pull` → `sudo systemctl restart today_tactics`. DB는 `scp players.db rocky@<HOST>:/opt/today_tactics/`
- **민감 정보**: history.md 자동 로그에 SSH 명령 들어가면 push 전 마스킹 필수
- **서버 path**: `/opt/today_tactics` (deploy.sh 기준)
- **포트 5000 점유 정리**: `Get-NetTCPConnection -LocalPort 5000 | Stop-Process -Id $_.OwningProcess -Force`
- **백업**: `/var/backups/today_tactics/players_YYYYMMDD.db.gz` (30일 보관, backup.sh chmod +x 필수)
- **자동화 cron**: 월 05:00 KST `update_data.py` (15 STEP, ~50분, K리그 공식 + SofaScore + 포털 종합)

---

## 🔧 자동 수집 파이프라인 (update_data.py 15 STEP)

| STEP | 작업 | 출처 |
|------|------|------|
| 0 | K리그 공식 일정·결과 | kleague.com |
| 1 | events 동기화 | DB ↔ JSON |
| 2 | synthetic → 실제 ID | SofaScore |
| 3 | 라인업 | SofaScore |
| 4~5 | mps K1+K2 | SofaScore |
| 6 | 히트맵 | SofaScore |
| 7~8 | incidents K1+K2 | SofaScore |
| 9 | venue 좌표 | SofaScore + Nominatim |
| 10 | weather | Open-Meteo |
| 11 | player master | SofaScore |
| 12 | K리그 포털 JSON | portal.kleague.com |
| 13 | name_ko + 신체정보 | K리그 포털 |
| 14 | avg_positions + shotmap | SofaScore |
| 15 | K리그 포털 formation | portal.kleague.com |
