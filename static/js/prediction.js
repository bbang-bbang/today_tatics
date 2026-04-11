// prediction.js — 경기 예측 보고서 + 다음 경기 일정

(function () {
    const section = document.getElementById("prediction-section");
    const report  = document.getElementById("prediction-report");

    // ── 라운드 일정 (페이지 로드 시 자동) ──────────────────
    let scheduleCache = null;
    let roundsCache   = null;
    let activeRound   = null;

    function loadSchedule() {
        Promise.all([
            fetch("/api/k2/schedule").then(r => r.json()),
            fetch("/api/k2/rounds").then(r => r.json()),
        ]).then(([sched, rounds]) => {
            scheduleCache = sched;
            roundsCache   = rounds;
            activeRound   = rounds.current_round;
            renderRoundsBanner(rounds, sched);
        }).catch(() => {});
    }

    function renderRoundsBanner(roundsData, schedData) {
        const wrap = document.getElementById("k2-schedule-banner-wrap");
        if (!wrap) return;

        const rounds = roundsData.rounds || [];
        if (!rounds.length) return;

        wrap.innerHTML = `
        <div id="k2-schedule-banner">
            <div class="ksb-header">
                <span class="ksb-title">K리그2 2026</span>
                <span class="ksb-sub">라운드 선택 후 경기 클릭 → 예측 보고서</span>
            </div>
            <div class="ksb-round-tabs" id="ksb-round-tabs">
                ${rounds.map(r => `
                <button class="ksb-round-btn${r.round === activeRound ? " active" : ""}" data-round="${r.round}">
                    R${r.round}
                    <span class="ksb-round-done">${r.finished}/${r.total}</span>
                </button>`).join("")}
            </div>
            <div class="ksb-list" id="ksb-game-list"></div>
        </div>`;

        renderRoundGames(activeRound, rounds);

        wrap.querySelectorAll(".ksb-round-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                wrap.querySelectorAll(".ksb-round-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                activeRound = parseInt(btn.dataset.round);
                renderRoundGames(activeRound, rounds);
            });
        });
    }

    function renderRoundGames(roundNum, rounds) {
        const list = document.getElementById("ksb-game-list");
        if (!list) return;
        const rndData = rounds.find(r => r.round === roundNum);
        if (!rndData) return;

        list.innerHTML = rndData.games.map(g => {
            const finished = g.finished;
            const scoreHtml = finished
                ? `<span class="ksb-score">${g.home_score} - ${g.away_score}</span>`
                : `<span class="ksb-time">${g.time}</span>`;
            const canPredict = !finished && g.home_id && g.away_id && g.home_id !== "null" && g.away_id !== "null";
            const finishedCls = finished ? " ksb-item-done" : (canPredict ? " ksb-item-upcoming" : "");
            return `
            <div class="ksb-item${finishedCls}"
                 data-home="${g.home_id}" data-away="${g.away_id}"
                 data-finished="${finished}">
                <span class="ksb-date">${g.date.replace(/\./g,"/").slice(5)}</span>
                <span class="ksb-match">
                    <span class="ksb-team ksb-home">${g.home_short}</span>
                    ${scoreHtml}
                    <span class="ksb-team ksb-away">${g.away_short}</span>
                </span>
                <span class="ksb-venue">${g.venue}</span>
                ${!finished && canPredict ? `<span class="ksb-pred-hint">예측 →</span>` : ""}
            </div>`;
        }).join("");

        list.querySelectorAll(".ksb-item").forEach(item => {
            item.addEventListener("click", () => {
                const homeId = item.dataset.home;
                const awayId = item.dataset.away;
                if (!homeId || !awayId || homeId === "null" || awayId === "null") return;
                section.classList.remove("hidden");
                loadPrediction(homeId, awayId);
                section.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        });
    }

    // ── 팀 선택 이벤트 수신 (기존 info.js 연동) ─────────────
    document.addEventListener("teamsSelected", (e) => {
        if (!e.detail || e.detail.home.id === e.detail.away.id) {
            section.classList.add("hidden");
            return;
        }
        section.classList.remove("hidden");
        loadPrediction(e.detail.home.id, e.detail.away.id);
        section.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    function loadPrediction(homeId, awayId) {
        report.innerHTML = `<div class="pred-loading">분석 중...</div>`;
        fetch(`/api/match-prediction?homeTeam=${homeId}&awayTeam=${awayId}`)
            .then(r => r.json())
            .then(data => render(data, homeId, awayId))
            .catch(() => { report.innerHTML = ""; });
    }

    // ── 순위 뱃지 ────────────────────────────────────────────
    function standingBadge(st) {
        if (!st) return "";
        return `<div class="pred-standing">
            <span class="pst-rank">${st.rank}위</span>
            <span class="pst-pts">${st.pts}pts</span>
            <span class="pst-record">${st.w}승 ${st.d}무 ${st.l}패</span>
            <span class="pst-gd" style="color:${st.gd>0?"#4ade80":st.gd<0?"#f87171":"#9ab"}">GD ${st.gd>0?"+":""}${st.gd}</span>
        </div>`;
    }

    // ── 예상 스코어 ───────────────────────────────────────────
    function predictedScore(home, away, predHome) {
        const hAvg = home.avg_gf || 0;
        const aAvg = away.avg_gf || 0;
        const hGA  = home.avg_ga || 0;
        const aGA  = away.avg_ga || 0;
        // 기대 득점 = (내 평균 득점 + 상대 평균 실점) / 2
        const expH = Math.max(0, (hAvg + aGA) / 2);
        const expA = Math.max(0, (aAvg + hGA) / 2);
        // 승률 기반 보정
        const bias = (predHome - 50) / 100;
        const adjH = Math.round((expH + bias * 0.5) * 10) / 10;
        const adjA = Math.round((expA - bias * 0.5) * 10) / 10;
        return { home: Math.max(0, adjH).toFixed(1), away: Math.max(0, adjA).toFixed(1) };
    }

    // ── 핵심 매치업 ───────────────────────────────────────────
    function keyMatchups(home, away) {
        const items = [];
        const hGF = home.avg_gf, aGF = away.avg_gf;
        const hGA = home.avg_ga, aGA = away.avg_ga;
        if (hGF && aGA) {
            const advantage = hGF - aGA;
            if (Math.abs(advantage) >= 0.3) {
                items.push(advantage > 0
                    ? `${home.name} 공격(${hGF.toFixed(1)}) > ${away.name} 수비(${aGA.toFixed(1)})`
                    : `${away.name} 수비(${aGA.toFixed(1)}) > ${home.name} 공격(${hGF.toFixed(1)})`);
            }
        }
        if (aGF && hGA) {
            const advantage = aGF - hGA;
            if (Math.abs(advantage) >= 0.3) {
                items.push(advantage > 0
                    ? `${away.name} 공격(${aGF.toFixed(1)}) > ${home.name} 수비(${hGA.toFixed(1)})`
                    : `${home.name} 수비(${hGA.toFixed(1)}) > ${away.name} 공격(${aGF.toFixed(1)})`);
            }
        }
        return items;
    }

    // ── 렌더링 ───────────────────────────────────────────────
    function render(d, homeId, awayId) {
        const { home, away, h2h, prediction } = d;
        const MONTHS = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"];
        const nowMonth = new Date().getMonth();
        const score = predictedScore(home, away, prediction.home);
        const matchups = keyMatchups(home, away);

        // 다음 경기 배너에서 이 매치의 정보 가져오기
        let nextInfo = null;
        if (scheduleCache) {
            nextInfo = (scheduleCache.upcoming || []).find(
                g => g.home_id === homeId && g.away_id === awayId
            );
        }

        report.innerHTML = `
        ${nextInfo ? `
        <div class="pred-match-header">
            <span class="pmh-round">R${nextInfo.round || "-"}</span>
            <span class="pmh-date">${nextInfo.date.replace(/\./g,"/")} ${nextInfo.time}</span>
            <span class="pmh-venue">${nextInfo.venue}</span>
        </div>` : ""}

        <div class="pred-grid">

            <!-- 홈팀 -->
            <div class="pred-team-panel pred-home">
                <div class="pred-team-name">${home.name}</div>
                ${standingBadge(home.standing)}
                <div class="pred-badges">${formBadges(home.form)}</div>
                <div class="pred-stats-row">
                    <div class="pred-stat"><span class="ps-val">${home.home_wr.toFixed(0)}%</span><span class="ps-lbl">홈 승률</span></div>
                    <div class="pred-stat"><span class="ps-val">${home.avg_gf.toFixed(1)}</span><span class="ps-lbl">경기당 득점</span></div>
                    <div class="pred-stat"><span class="ps-val">${home.avg_ga.toFixed(1)}</span><span class="ps-lbl">경기당 실점</span></div>
                    ${home.month_wr !== null ? `<div class="pred-stat"><span class="ps-val" style="color:${monthColor(home.month_wr)}">${home.month_wr.toFixed(0)}%</span><span class="ps-lbl">${MONTHS[nowMonth]} 승률</span></div>` : ""}
                </div>
                <div class="pred-notes">
                    ${home.notes.map(n => `<div class="pred-note">• ${n}</div>`).join("") || "<div class='pred-note pred-note-none'>특이사항 없음</div>"}
                </div>
                ${home.top_scorers.length ? `
                <div class="pred-scorers">
                    <div class="pred-scorers-title">이번 시즌 득점</div>
                    ${home.top_scorers.map(s => `<div class="pred-scorer-row"><span class="scorer-name scorer-link" data-player-id="${s.id}">${s.name}</span><span class="scorer-g">${s.goals}골</span></div>`).join("")}
                </div>` : ""}
            </div>

            <!-- 중앙 예측 -->
            <div class="pred-center">
                <div class="pred-center-title">예상 결과</div>
                <div class="pred-prob-bar">
                    <div class="ppb-home" style="width:${prediction.home}%">${prediction.home}%</div>
                    <div class="ppb-draw" style="width:${prediction.draw}%">${prediction.draw}%</div>
                    <div class="ppb-away" style="width:${prediction.away}%">${prediction.away}%</div>
                </div>
                <div class="pred-prob-labels">
                    <span style="color:#4ea4f8">홈 승</span>
                    <span style="color:#888">무승부</span>
                    <span style="color:#b87ef8">원정 승</span>
                </div>

                <div class="pred-score-est">
                    <span class="pse-label">예상 스코어</span>
                    <span class="pse-score">${score.home} - ${score.away}</span>
                </div>

                <div class="pred-h2h">
                    <div class="pred-h2h-title">직접 전적 (K2)</div>
                    ${h2h.games > 0 ? `
                    <div class="pred-h2h-row">
                        <span class="h2h-val" style="color:#4ea4f8">${h2h.home_w}승</span>
                        <span class="h2h-sep">${h2h.games}경기</span>
                        <span class="h2h-val" style="color:#b87ef8">${h2h.away_w}승</span>
                    </div>
                    <div class="pred-h2h-draw">${h2h.draw}무</div>
                    ` : `<div class="pred-note-none">전적 없음</div>`}
                </div>

                ${matchups.length ? `
                <div class="pred-matchup-keys">
                    <div class="pmk-title">핵심 지표</div>
                    ${matchups.map(m => `<div class="pmk-item">⚡ ${m}</div>`).join("")}
                </div>` : ""}
            </div>

            <!-- 원정팀 -->
            <div class="pred-team-panel pred-away">
                <div class="pred-team-name">${away.name}</div>
                ${standingBadge(away.standing)}
                <div class="pred-badges">${formBadges(away.form)}</div>
                <div class="pred-stats-row">
                    <div class="pred-stat"><span class="ps-val">${away.away_wr.toFixed(0)}%</span><span class="ps-lbl">원정 승률</span></div>
                    <div class="pred-stat"><span class="ps-val">${away.avg_gf.toFixed(1)}</span><span class="ps-lbl">경기당 득점</span></div>
                    <div class="pred-stat"><span class="ps-val">${away.avg_ga.toFixed(1)}</span><span class="ps-lbl">경기당 실점</span></div>
                    ${away.month_wr !== null ? `<div class="pred-stat"><span class="ps-val" style="color:${monthColor(away.month_wr)}">${away.month_wr.toFixed(0)}%</span><span class="ps-lbl">${MONTHS[nowMonth]} 승률</span></div>` : ""}
                </div>
                <div class="pred-notes">
                    ${away.notes.map(n => `<div class="pred-note">• ${n}</div>`).join("") || "<div class='pred-note pred-note-none'>특이사항 없음</div>"}
                </div>
                ${away.top_scorers.length ? `
                <div class="pred-scorers">
                    <div class="pred-scorers-title">이번 시즌 득점</div>
                    ${away.top_scorers.map(s => `<div class="pred-scorer-row"><span class="scorer-name scorer-link" data-player-id="${s.id}">${s.name}</span><span class="scorer-g">${s.goals}골</span></div>`).join("")}
                </div>` : ""}
            </div>

        </div>`;

        // 선수 클릭 → 모달
        report.addEventListener("click", (e) => {
            const el = e.target.closest(".scorer-link");
            if (!el) return;
            const pid = parseInt(el.dataset.playerId);
            if (!pid) return;
            document.dispatchEvent(new CustomEvent("playerSelected", {
                detail: { playerId: pid, playerName: el.textContent.trim() }
            }));
        });
    }

    function formBadges(form) {
        return (form || []).map(r => {
            const cls = r === "W" ? "fb-w" : r === "D" ? "fb-d" : "fb-l";
            const lbl = r === "W" ? "승" : r === "D" ? "무" : "패";
            return `<span class="form-badge ${cls}">${lbl}</span>`;
        }).join("");
    }

    function monthColor(pct) {
        if (pct >= 55) return "#7bed9f";
        if (pct <= 30) return "#f87171";
        return "#c8d8f0";
    }

    // 페이지 로드 시 K2 일정 불러오기
    loadSchedule();
})();
