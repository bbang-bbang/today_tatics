# Backlog — Today Tactics

> 작업 끝나면 이 파일을 업데이트해 항목을 옮기거나 삭제. 시간순 기록은 `work-log-YYYY-MM-DD.md`.

---

## 🔴 P1 — 가치 큰 단기 작업

### [ ] update_data.py K1+K2 전체로 확장 + 자동화
**왜**: 현재 매주 신규 매치는 K리그 공식 API에서 스코어만 들어옴 → synthetic 90xxxxxx ID 생성 → lineup/incidents 누락. 사용자가 다음 라운드 보면 포메이션·카드 비어있음. 이번 세션에서 14건 수동 처리했으나 매주 반복됨.

**무엇**:
1. `update_data.py`의 `TEAM_ID = 7652` (수원 단일팀) → 전체 K1+K2 팀 또는 tournament 단위로 변경
2. `replace_synthetic_events.py` 로직을 `update_data.py` STEP 0으로 통합 (신규 event 들어오자마자 진짜 ID로)
3. lineup + incidents (carde) 둘 다 자동 수집
4. 서버 crontab 등록 (현재 매주 일요일 23시 backup만 등록되어 있음 — backup.sh 옆에 update.sh 추가)

**비용**: 1~2시간
**효과**: 매주 자동, 수동 개입 0

**시작 명령**:
```bash
# 로컬에서 실험
python -c "import sqlite3; c=sqlite3.connect('players.db'); print(c.execute('SELECT id FROM events WHERE id BETWEEN 90000000 AND 91000000').fetchall())"
# 만약 synthetic이 또 쌓여있으면 먼저 청소
python crawlers/replace_synthetic_events.py
```

---

### [ ] 5/22 K1 미래 매치 1건 매칭 실패 처리
**왜**: `replace_synthetic_events.py` 첫 실행에서 1건 매칭 실패 (Jeonbuk vs Daejeon, ts=1771642800 = 5/22). 미래 경기라 SofaScore에 아직 등록 안됨.

**무엇**: 5/22 이후 또는 경기 종료 후 `python crawlers/replace_synthetic_events.py` 재실행

**비용**: 30초
**효과**: 1건 정상화

---

## 🟡 P2 — 시간 날 때 처리

### [ ] 서버 authorized_keys Key 1 (4096-bit RSA) 정체 확인
**왜**: SSH 강화·fail2ban으로 위험 완화됐지만 정체 모르는 키 1개 여전히 등록됨.
- Key 1: `SHA256:guhz...nM` (4096-bit RSA, no comment)
- Key 2: `SHA256:ce7i...zM` = today-project.pem (✓ 본인 키)

**무엇**: 본인 키면 그대로 두고 코멘트 추가, 모르는 키면 제거
```bash
ssh -i today-project.pem rocky@<HOST> 'ssh-keygen -lf ~/.ssh/authorized_keys'
# 모르는 키면:
ssh -i today-project.pem rocky@<HOST> 'sed -i "1d" ~/.ssh/authorized_keys'
```

---

### [ ] 가비아 방화벽 SSH 화이트리스트
**왜**: 봇 트래픽 0으로 만들 수 있음. 단 본인 공인 IP가 고정이어야 함.

**무엇**: 가비아 콘솔 → 방화벽 → 22번 포트 inbound를 본인 IP만 허용

**조건**: 본인 IP 고정 여부 확인 필요. 동적이면 안 함 (외부 카페 등에서 락아웃)

---

### [ ] K1 xG 데이터 백필
**왜**: 현재 K1 `match_player_stats.expected_goals` 0건. SQL fallback으로 실제 골 사용 중. xG 있으면 모델 정확도 +6%p 추정.

**무엇**: `crawlers/build_k1_xg.py` 재실행

**비용**: 1~3시간 (Playwright 안정성 변수)
**효과**: K1 1X2 적중률 44% → 50%+ 가능성

---

### [ ] 매치 상세 보고서에 카드 통계 노출
**왜**: 현재 카드 데이터 6,962건이 인사이트 패널에만 노출. 매치 클릭 시 양 팀 카드 추세도 보여주면 유용 (특히 심판 카드 제거하고 빈 자리).

**무엇**: `prediction.js render()`에서 `home.cards` / `away.cards` 표시. `/api/match-prediction`에서 `card_events` JOIN해 추가.

**비용**: 30분

---

## ⚫ P3 — 의식적으로 안 함

- ❌ Git history rewrite (PM 권고: ROI 음수)
- ❌ history.md 과거 51회 노출 정리 (rewrite 없이 의미 X)

---

## 📌 운영 메모

- **서버 배포 워크플로**: 코드는 `git push` → 서버 `git pull` → `sudo systemctl restart today_tactics`. DB는 별도 `scp players.db rocky@<HOST>:/opt/today_tactics/`
- **민감 정보**: history.md 자동 로그에 SSH 명령 들어가면 push 전 마스킹 필수 (rocky@1.201.126.200, today-project.pem)
- **서버 path 주의**: deploy.sh의 `/opt/today_tactics`가 실제 위치 (history.md엔 `today_tatics` 오타가 누적됐었음)
- **포트 5000 점유 정리**: 로컬 Flask 종료 시 `Get-NetTCPConnection -LocalPort 5000 | Stop-Process -Id $_.OwningProcess -Force`
