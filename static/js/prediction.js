// prediction.js — 경기 예측 보고서

(function () {
    const section = document.getElementById("prediction-section");
    const report  = document.getElementById("prediction-report");

    // info.js가 발행하는 CustomEvent 수신
    document.addEventListener("teamsSelected", (e) => {
        if (!e.detail || e.detail.home.id === e.detail.away.id) {
            section.classList.add("hidden");
            return;
        }
        section.classList.remove("hidden");
        loadPrediction(e.detail.home.id, e.detail.away.id);
    });

    function loadPrediction(homeId, awayId) {
        report.innerHTML = `<div class="pred-loading">분석 중...</div>`;
        fetch(`/api/match-prediction?homeTeam=${homeId}&awayTeam=${awayId}`)
            .then(r => r.json())
            .then(data => render(data))
            .catch(() => { report.innerHTML = ""; });
    }

    function standingBadge(st) {
        if (!st) return "";
        return `<div class="pred-standing">
            <span class="pst-rank">${st.rank}위</span>
            <span class="pst-pts">${st.pts}pts</span>
            <span class="pst-record">${st.w}승 ${st.d}무 ${st.l}패</span>
            <span class="pst-gd" style="color:${st.gd>0?'#4ade80':st.gd<0?'#f87171':'#9ab'}">GD ${st.gd>0?"+":""}${st.gd}</span>
        </div>`;
    }

    function render(d) {
        const { home, away, h2h, prediction } = d;
        const MONTHS = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"];
        const nowMonth = new Date().getMonth();

        report.innerHTML = `
        <div class="pred-grid">

            <!-- 홈팀 패널 -->
            <div class="pred-team-panel pred-home">
                <div class="pred-team-name">${home.name}</div>
                ${standingBadge(home.standing)}
                <div class="pred-badges">
                    ${formBadges(home.form)}
                </div>
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
            </div>

            <!-- 원정팀 패널 -->
            <div class="pred-team-panel pred-away">
                <div class="pred-team-name">${away.name}</div>
                ${standingBadge(away.standing)}
                <div class="pred-badges">
                    ${formBadges(away.form)}
                </div>
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

    // 득점 선수 이름 클릭 → 선수 분석 모달
    report.addEventListener("click", (e) => {
        const el = e.target.closest(".scorer-link");
        if (!el) return;
        const pid = parseInt(el.dataset.playerId);
        if (!pid) return;
        document.dispatchEvent(new CustomEvent("playerSelected", {
            detail: { playerId: pid, playerName: el.textContent.trim() }
        }));
    });
})();
