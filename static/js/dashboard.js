// dashboard.js — K리그 인사이트 대시보드 (K1/K2)

(function () {
    /* ── 상태 ──────────────────────────────────────────────── */
    let currentYear   = null;   // null = 전체
    let currentLeague = "k1";   // 기본 K리그1
    let currentTab    = "ranking";
    let currentRank   = "scorers";
    let dashData      = null;

    // Chart 인스턴스 캐시
    const CHARTS = {};

    /* ── DOM refs ─────────────────────────────────────────── */
    const yearFilter = document.getElementById("ld-year-filter");

    // 탭 버튼
    document.querySelectorAll(".ld-tab").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".ld-tab").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentTab = btn.dataset.tab;
            document.querySelectorAll(".ld-panel").forEach(p => p.classList.add("hidden"));
            document.getElementById(`ld-panel-${currentTab}`).classList.remove("hidden");
            if (dashData) renderCurrentTab();
        });
    });

    // 랭킹 서브탭
    document.querySelectorAll(".ld-rank-tab").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".ld-rank-tab").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentRank = btn.dataset.rank;
            if (dashData) renderRanking();
        });
    });

    /* ── 데이터 로드 ──────────────────────────────────────── */
    function load(year) {
        currentYear = year || null;
        const params = new URLSearchParams({ league: currentLeague });
        if (year) params.set("year", year);
        const url = `/api/league-dashboard?${params.toString()}`;
        fetch(url)
            .then(r => r.json())
            .then(data => {
                dashData = data;
                buildYearFilter(data.available_years);
                renderCurrentTab();
            });
    }

    // 리그 탭 (선택): #ld-league-tabs가 존재하면 자동 바인딩
    const leagueTabsEl = document.getElementById("ld-league-tabs");
    if (leagueTabsEl) {
        leagueTabsEl.querySelectorAll("[data-league]").forEach(btn => {
            btn.addEventListener("click", () => {
                if (btn.classList.contains("active")) return;
                leagueTabsEl.querySelectorAll("[data-league]")
                    .forEach(b => b.classList.toggle("active", b === btn));
                currentLeague = btn.dataset.league;
                load(currentYear);
            });
        });
    }

    function buildYearFilter(years) {
        const items = ["전체", ...years];
        yearFilter.innerHTML = items.map(y => {
            const active = (y === "전체" && !currentYear) || y === currentYear;
            return `<button class="ld-year-btn${active ? " active" : ""}" data-year="${y}">${y}</button>`;
        }).join("");
        yearFilter.querySelectorAll(".ld-year-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const y = btn.dataset.year === "전체" ? null : btn.dataset.year;
                load(y);
            });
        });
    }

    function renderCurrentTab() {
        if (currentTab === "ranking")  renderRanking();
        if (currentTab === "position") renderPosition();
        if (currentTab === "team")     renderTeam();
        if (currentTab === "trend")    renderTrend();
    }

    /* ── 랭킹 테이블 ─────────────────────────────────────── */
    const RANK_CONF = {
        scorers:   { key: "goals",   label: "득점",  cols: ["games","goals","assists","rating","minutes"] },
        assists:   { key: "assists", label: "도움",  cols: ["games","assists","goals","rating","minutes"] },
        rated:     { key: "rating",  label: "평점",  cols: ["games","rating","goals","assists","minutes"] },
        dribbles:  { key: "dribbles",label: "드리블", cols: ["games","dribbles","goals","assists","minutes"] },
        defenders: { key: "duel_pct", label: "듀얼 성공률", cols: ["games","duel_pct","tackles_p90","ints_p90","minutes"] },
    };
    const COL_LABEL = {
        games:"경기", goals:"골", assists:"도움", rating:"평점",
        minutes:"출전분", dribbles:"드리블", tackles:"태클", interceptions:"인터셉트", yellows:"경고",
        duel_pct:"듀얼 성공률", tackles_p90:"태클/90", ints_p90:"인터셉트/90"
    };

    function renderRanking() {
        const conf = RANK_CONF[currentRank];
        let list = dashData[`top_${currentRank}`];
        if (!list) return;

        const rows = list.map((p, i) => {
            const mainVal = currentRank === "defenders"
                ? (p.duel_pct != null ? p.duel_pct + "%" : "-")
                : currentRank === "rated"
                    ? (p.rating ? p.rating.toFixed(2) : "-")
                    : p[conf.key];

            const posCls = { "F":"ld-pos-f","M":"ld-pos-m","D":"ld-pos-d","G":"ld-pos-g" }[p.pos] || "";
            const rankCls = i === 0 ? "ld-rank-gold" : i === 1 ? "ld-rank-silver" : i === 2 ? "ld-rank-bronze" : "";

            const cells = conf.cols.map(c => {
                let v;
                if (c === "rating")   v = p.rating ? p.rating.toFixed(2) : "-";
                else if (c === "minutes") v = p.minutes ? Math.round(p.minutes) + "'" : "-";
                else if (c === "duel_pct") v = p.duel_pct != null ? p.duel_pct + "%" : "-";
                else if (c === "tackles_p90") v = p.tackles_p90 != null ? p.tackles_p90 : "-";
                else if (c === "ints_p90")    v = p.ints_p90 != null ? p.ints_p90 : "-";
                else v = p[c] ?? "-";
                return `<td>${v}</td>`;
            }).join("");

            return `<tr class="ld-player-row" data-player-id="${p.id}">
                <td class="ld-rank-num ${rankCls}">${i+1}</td>
                <td><span class="ld-pos-badge ${posCls}">${p.pos||"?"}</span></td>
                <td class="ld-player-name">${p.name}</td>
                <td class="ld-team-name">${p.team}</td>
                <td class="ld-main-val">${mainVal}</td>
                ${cells}
            </tr>`;
        }).join("");

        const headers = conf.cols.map(c => `<th>${COL_LABEL[c]||c}</th>`).join("");

        document.getElementById("ld-ranking-body").innerHTML = `
        <div class="ld-table-wrap">
            <table class="ld-table">
                <thead><tr>
                    <th>#</th><th>포지션</th><th>선수</th><th>팀</th>
                    <th>${conf.label}</th>${headers}
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;

        // 선수 클릭 → 개인 분석 모달
        document.querySelectorAll(".ld-player-row").forEach(row => {
            row.addEventListener("click", () => {
                const pid = parseInt(row.dataset.playerId);
                if (pid) document.dispatchEvent(new CustomEvent("playerSelected", { detail: { playerId: pid } }));
            });
        });
    }

    /* ── 포지션 분석 ─────────────────────────────────────── */
    function renderPosition() {
        const pa = dashData.position_avg;
        const POS = ["GK","DF","MF","FW"];
        const colors = {
            GK: "rgba(251,191,36,",
            DF: "rgba(74,222,128,",
            MF: "rgba(78,164,248,",
            FW: "rgba(248,113,113,",
        };

        function makeDatasets(keys, alpha) {
            return POS.map(pos => ({
                label: pos,
                data: keys.map(k => pa[pos] ? pa[pos][k] ?? 0 : 0),
                backgroundColor: colors[pos] + alpha + ")",
                borderColor:     colors[pos] + "0.9)",
                borderWidth: 1,
                borderRadius: 4,
            }));
        }

        const baseOpts = {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: "#9ab", font: { size: 11 } } },
                tooltip: { backgroundColor: "rgba(10,15,30,0.92)", titleColor:"#c8d8f0", bodyColor:"#c8d8f0" }
            },
            scales: {
                x: { ticks: { color: "#778", font:{ size:11} }, grid:{ color:"rgba(255,255,255,0.05)" } },
                y: { ticks: { color: "#778", font:{ size:11} }, grid:{ color:"rgba(255,255,255,0.05)" } }
            }
        };

        // 공격 차트
        destroyChart("pos-attack");
        const ctxA = document.getElementById("ld-chart-pos-attack").getContext("2d");
        CHARTS["pos-attack"] = new Chart(ctxA, {
            type: "bar",
            data: {
                labels: ["득점(90분)", "도움(90분)", "슈팅(90분)", "키패스(90분)"],
                datasets: makeDatasets(["goals","assists","shots","key_passes"], "0.6"),
            },
            options: { ...baseOpts, plugins: { ...baseOpts.plugins } }
        });

        // 수비 차트
        destroyChart("pos-defense");
        const ctxD = document.getElementById("ld-chart-pos-defense").getContext("2d");
        CHARTS["pos-defense"] = new Chart(ctxD, {
            type: "bar",
            data: {
                labels: ["태클(90분)", "인터셉트(90분)", "드리블(90분)"],
                datasets: makeDatasets(["tackles","interceptions","dribbles"], "0.6"),
            },
            options: { ...baseOpts }
        });

        // 평점 차트
        destroyChart("pos-rating");
        const ctxR = document.getElementById("ld-chart-pos-rating").getContext("2d");
        CHARTS["pos-rating"] = new Chart(ctxR, {
            type: "bar",
            data: {
                labels: POS,
                datasets: [{
                    label: "평균 평점",
                    data: POS.map(pos => pa[pos] ? pa[pos].rating : null),
                    backgroundColor: POS.map(pos => colors[pos] + "0.6)"),
                    borderColor:     POS.map(pos => colors[pos] + "0.9)"),
                    borderWidth: 1,
                    borderRadius: 6,
                }]
            },
            options: {
                ...baseOpts,
                plugins: { ...baseOpts.plugins, legend: { display: false } },
                scales: {
                    ...baseOpts.scales,
                    y: { ...baseOpts.scales.y, min: 6, max: 8 }
                }
            }
        });
    }

    /* ── 팀별 공격력 ─────────────────────────────────────── */
    function renderTeam() {
        const ta = dashData.team_attack;
        const labels = ta.map(t => t.team);

        // 득점/도움 차트
        destroyChart("team-attack");
        const ctxA = document.getElementById("ld-chart-team-attack").getContext("2d");
        const gradG = ctxA.createLinearGradient(0,0,0,300);
        gradG.addColorStop(0,"rgba(78,164,248,0.8)"); gradG.addColorStop(1,"rgba(78,164,248,0.2)");
        const gradA = ctxA.createLinearGradient(0,0,0,300);
        gradA.addColorStop(0,"rgba(124,248,183,0.8)"); gradA.addColorStop(1,"rgba(124,248,183,0.2)");

        CHARTS["team-attack"] = new Chart(ctxA, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    { label:"득점", data: ta.map(t=>t.goals),   backgroundColor: gradG, borderRadius:3 },
                    { label:"도움", data: ta.map(t=>t.assists), backgroundColor: gradA, borderRadius:3 },
                ]
            },
            options: {
                responsive:true, maintainAspectRatio:false,
                plugins: {
                    legend: { labels:{ color:"#9ab", font:{size:11} } },
                    tooltip: { backgroundColor:"rgba(10,15,30,0.92)", titleColor:"#c8d8f0", bodyColor:"#c8d8f0" }
                },
                scales: {
                    x: { ticks:{ color:"#778", font:{size:10}, maxRotation:35 }, grid:{ color:"rgba(255,255,255,0.05)" } },
                    y: { ticks:{ color:"#778", font:{size:11} }, grid:{ color:"rgba(255,255,255,0.05)" } }
                }
            }
        });

        // 평균 평점 차트
        const taRating = [...ta].sort((a,b) => (b.rating||0)-(a.rating||0));
        destroyChart("team-rating");
        const ctxR = document.getElementById("ld-chart-team-rating").getContext("2d");
        CHARTS["team-rating"] = new Chart(ctxR, {
            type: "bar",
            data: {
                labels: taRating.map(t=>t.team),
                datasets: [{
                    label: "평균 평점",
                    data: taRating.map(t=>t.rating),
                    backgroundColor: taRating.map(t => {
                        const v = t.rating || 6.5;
                        const r = Math.round(220 - (v-6)*80);
                        const g = Math.round(60  + (v-6)*80);
                        return `rgba(${r},${g},80,0.7)`;
                    }),
                    borderRadius:4,
                }]
            },
            options: {
                responsive:true, maintainAspectRatio:false,
                plugins: {
                    legend:{ display:false },
                    tooltip: { backgroundColor:"rgba(10,15,30,0.92)", titleColor:"#c8d8f0", bodyColor:"#c8d8f0" }
                },
                scales: {
                    x: { ticks:{ color:"#778", font:{size:10}, maxRotation:35 }, grid:{ color:"rgba(255,255,255,0.05)" } },
                    y: { min:6, ticks:{ color:"#778", font:{size:11} }, grid:{ color:"rgba(255,255,255,0.05)" } }
                }
            }
        });
    }

    /* ── 월별 트렌드 ─────────────────────────────────────── */
    function renderTrend() {
        const mt = dashData.monthly_trend;
        const MONTHS = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"];
        const labels = mt.map(m => MONTHS[m.month-1]);

        // G/A 추이
        destroyChart("trend-ga");
        const ctxG = document.getElementById("ld-chart-trend-ga").getContext("2d");
        const gradGoal = ctxG.createLinearGradient(0,0,0,240);
        gradGoal.addColorStop(0,"rgba(248,113,113,0.6)"); gradGoal.addColorStop(1,"rgba(248,113,113,0.05)");
        const gradAst = ctxG.createLinearGradient(0,0,0,240);
        gradAst.addColorStop(0,"rgba(78,164,248,0.5)"); gradAst.addColorStop(1,"rgba(78,164,248,0.05)");

        CHARTS["trend-ga"] = new Chart(ctxG, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    { label:"경기당 득점", data: mt.map(m => m.games ? +(m.goals/m.games).toFixed(2) : 0),
                      backgroundColor: gradGoal, borderRadius:4 },
                    { label:"경기당 도움", data: mt.map(m => m.games ? +(m.assists/m.games).toFixed(2) : 0),
                      backgroundColor: gradAst, borderRadius:4 },
                ]
            },
            options: {
                responsive:true, maintainAspectRatio:false,
                plugins: {
                    legend: { labels:{ color:"#9ab", font:{size:11} } },
                    tooltip: { backgroundColor:"rgba(10,15,30,0.92)", titleColor:"#c8d8f0", bodyColor:"#c8d8f0" }
                },
                scales: {
                    x: { ticks:{ color:"#778", font:{size:11} }, grid:{ color:"rgba(255,255,255,0.05)" } },
                    y: { ticks:{ color:"#778", font:{size:11} }, grid:{ color:"rgba(255,255,255,0.05)" } }
                }
            }
        });

        // 평점 추이
        destroyChart("trend-rating");
        const ctxR = document.getElementById("ld-chart-trend-rating").getContext("2d");
        CHARTS["trend-rating"] = new Chart(ctxR, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "평균 평점",
                    data: mt.map(m=>m.rating),
                    borderColor: "rgba(251,191,36,0.9)",
                    backgroundColor: "rgba(251,191,36,0.1)",
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: "rgba(251,191,36,1)",
                    pointRadius: 5,
                    spanGaps: true,
                }]
            },
            options: {
                responsive:true, maintainAspectRatio:false,
                plugins: {
                    legend: { labels:{ color:"#9ab", font:{size:11} } },
                    tooltip: { backgroundColor:"rgba(10,15,30,0.92)", titleColor:"#c8d8f0", bodyColor:"#c8d8f0" }
                },
                scales: {
                    x: { ticks:{ color:"#778", font:{size:11} }, grid:{ color:"rgba(255,255,255,0.05)" } },
                    y: { min:6.3, max:7.5, ticks:{ color:"#778", font:{size:11} }, grid:{ color:"rgba(255,255,255,0.05)" } }
                }
            }
        });
    }

    /* ── 헬퍼 ────────────────────────────────────────────── */
    function destroyChart(key) {
        if (CHARTS[key]) { CHARTS[key].destroy(); delete CHARTS[key]; }
    }

    /* ── 초기 로드 ───────────────────────────────────────── */
    load(null);
})();
