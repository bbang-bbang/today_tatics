(function () {
    "use strict";

    const matchupArea = document.getElementById("matchup-area");

    let teamsData = [];

    function getTeam(id) { return teamsData.find(t => t.id === id) || null; }

    function formatDate(dateStr) {
        const p = dateStr.split("-");
        return `${parseInt(p[1])}/${parseInt(p[2])}`;
    }

    function calcFormStats(results) {
        let w = 0, d = 0, l = 0;
        results.forEach(r => { if (r.result === "W") w++; else if (r.result === "D") d++; else l++; });
        return { w, d, l };
    }

    function pct(w, games) {
        if (!games) return 0;
        return Math.round((w / games) * 100);
    }

    // ── 홈/원정 승률 블록 ────────────────────────────────
    function buildWinrateSection(stats) {
        const section = document.createElement("div");
        section.className = "winrate-section";

        const { home, away } = stats;

        [
            { tag: "HOME", data: home, cls: "home" },
            { tag: "AWAY", data: away, cls: "away" },
        ].forEach(({ tag, data, cls }) => {
            const winPct = pct(data.w, data.games);
            const row = document.createElement("div");
            row.className = "winrate-row";

            const labelRow = document.createElement("div");
            labelRow.className = "winrate-label-row";

            const tagEl = document.createElement("span");
            tagEl.className = "winrate-tag";
            tagEl.textContent = tag;

            const detail = document.createElement("span");
            detail.style.cssText = "font-size:0.65rem;color:#4a6080;";
            detail.textContent = `${data.w}승 ${data.d}무 ${data.l}패`;

            const pctEl = document.createElement("span");
            pctEl.className = "winrate-pct";
            pctEl.textContent = `승률 ${winPct}%`;

            labelRow.appendChild(tagEl);
            labelRow.appendChild(detail);
            labelRow.appendChild(pctEl);

            const barWrap = document.createElement("div");
            barWrap.className = "winrate-bar-wrap";
            const bar = document.createElement("div");
            bar.className = `winrate-bar ${cls}`;
            bar.style.width = "0%";
            // 애니메이션을 위해 약간 지연 후 width 설정
            setTimeout(() => { bar.style.width = `${winPct}%`; }, 50);
            barWrap.appendChild(bar);

            row.appendChild(labelRow);
            row.appendChild(barWrap);
            section.appendChild(row);
        });

        return section;
    }

    // ── 최근 5경기 폼 뱃지 ────────────────────────────────
    function buildFormBadges(results) {
        const row = document.createElement("div");
        row.className = "matchup-form-row";
        results.forEach(r => {
            const badge = document.createElement("div");
            badge.className = `form-badge ${r.result}`;

            const resultSpan = document.createElement("span");
            resultSpan.textContent = r.result;

            const dateSpan = document.createElement("span");
            dateSpan.className = "form-badge-date";
            dateSpan.textContent = formatDate(r.date);

            badge.appendChild(resultSpan);
            badge.appendChild(dateSpan);

            const opp = getTeam(r.opponent);
            badge.title = `${r.home ? "홈" : "원정"} vs ${opp ? opp.short : r.opponent}  ${r.score}`;
            row.appendChild(badge);
        });
        return row;
    }

    // ── 팀 컬럼 (폼 + 승률) ─────────────────────────────
    function buildTeamCol(team, results, stats, isAway) {
        const col = document.createElement("div");
        col.className = `matchup-team-col${isAway ? " away" : ""}`;

        // 헤더
        const header = document.createElement("div");
        header.className = `matchup-team-header${isAway ? " away" : ""}`;

        const emblem = document.createElement("div");
        emblem.className = "matchup-team-emblem";
        emblem.style.borderColor = team.secondary || "#1c3a6e";
        if (team.emblem) {
            const img = document.createElement("img");
            img.src = `/static/img/emblems/${team.emblem}`;
            img.alt = team.short;
            emblem.appendChild(img);
        } else {
            emblem.style.background = team.primary;
            emblem.textContent = team.short;
        }

        const nameEl = document.createElement("div");
        nameEl.className = "matchup-team-name";
        nameEl.textContent = team.name;

        header.appendChild(emblem);
        header.appendChild(nameEl);
        col.appendChild(header);

        // 최근 5경기 폼
        const formLabel = document.createElement("div");
        formLabel.className = "matchup-form-label";
        formLabel.textContent = "최근 5경기";
        col.appendChild(formLabel);
        col.appendChild(buildFormBadges(results));

        // 통계 요약 (5경기 기준)
        const fiveStats = calcFormStats(results);
        const statsRow = document.createElement("div");
        statsRow.className = "matchup-stats-row";
        [
            { label: "승", val: fiveStats.w, cls: "record-w" },
            { label: "무", val: fiveStats.d, cls: "record-d" },
            { label: "패", val: fiveStats.l, cls: "record-l" },
        ].forEach(({ label, val, cls }) => {
            const pill = document.createElement("div");
            pill.className = "stat-pill";
            pill.innerHTML = `${label} <strong class="${cls}">${val}</strong>`;
            statsRow.appendChild(pill);
        });
        col.appendChild(statsRow);

        // 홈/원정 5년 승률
        if (stats && stats.home) {
            const hrLabel = document.createElement("div");
            hrLabel.className = "matchup-form-label";
            hrLabel.style.marginTop = "12px";
            hrLabel.textContent = "홈 · 원정 승률 (최근 5년)";
            col.appendChild(hrLabel);
            col.appendChild(buildWinrateSection(stats));
        }

        return col;
    }

    // ── 가운데 H2H 박스 ──────────────────────────────────
    function buildH2HBox(h2h, teamA, teamB) {
        const vsCol = document.createElement("div");
        vsCol.className = "matchup-vs-col";

        const vsText = document.createElement("div");
        vsText.className = "matchup-vs-text";
        vsText.textContent = "VS";
        vsCol.appendChild(vsText);

        const box = document.createElement("div");
        box.className = "matchup-record-box";

        const title = document.createElement("div");
        title.className = "matchup-record-title";
        title.textContent = "최근 10경기 맞대결";
        box.appendChild(title);

        const nums = document.createElement("div");
        nums.className = "matchup-record-nums";

        if (!h2h || h2h.total === 0) {
            nums.innerHTML = `<span style="font-size:0.75rem;color:#3a4a6a;">기록 없음</span>`;
        } else {
            nums.innerHTML =
                `<span class="record-w">${h2h.w}</span>` +
                `<span class="matchup-record-sep">-</span>` +
                `<span class="record-d">${h2h.d}</span>` +
                `<span class="matchup-record-sep">-</span>` +
                `<span class="record-l">${h2h.l}</span>`;

            const subLabel = document.createElement("div");
            subLabel.style.cssText = "font-size:0.82rem;color:#ffffff;margin-top:4px;";
            subLabel.textContent = `${teamA.short} 승 · 무 · ${teamB.short} 승`;
            box.appendChild(nums);
            box.appendChild(subLabel);

            const total = document.createElement("div");
            total.className = "matchup-record-total";
            total.textContent = `총 ${h2h.total}경기`;
            box.appendChild(total);

            vsCol.appendChild(box);
            return vsCol;
        }

        box.appendChild(nums);
        vsCol.appendChild(box);
        return vsCol;
    }

    // ── 메인 렌더 ────────────────────────────────────────
    async function renderMatchup(teamA, teamB) {
        matchupArea.innerHTML = `<div class="matchup-placeholder"><span>불러오는 중...</span></div>`;

        const [resultsA, resultsB, h2h, statsA, statsB] = await Promise.all([
            fetch(`/api/results?teamId=${teamA.id}`).then(r => r.json()),
            fetch(`/api/results?teamId=${teamB.id}`).then(r => r.json()),
            fetch(`/api/h2h?teamA=${teamA.id}&teamB=${teamB.id}`).then(r => r.json()),
            fetch(`/api/team-stats?teamId=${teamA.id}`).then(r => r.json()),
            fetch(`/api/team-stats?teamId=${teamB.id}`).then(r => r.json()),
        ]);

        matchupArea.innerHTML = "";

        const grid = document.createElement("div");
        grid.className = "matchup-grid";

        grid.appendChild(buildTeamCol(teamA, resultsA, statsA, false));
        grid.appendChild(buildH2HBox(h2h, teamA, teamB));
        grid.appendChild(buildTeamCol(teamB, resultsB, statsB, true));

        matchupArea.appendChild(grid);
    }

    function clearMatchup() {
        matchupArea.innerHTML = `<div class="matchup-placeholder"><span>위에서 HOME · AWAY 팀을 선택하면 전적이 표시됩니다</span></div>`;
    }

    // ── 팀 배너 변화 감지 ────────────────────────────────
    function watchBanner() {
        const nameA = document.getElementById("name-a");
        const nameB = document.getElementById("name-b");
        if (!nameA || !nameB) return;

        const observer = new MutationObserver(() => {
            const textA = nameA.textContent.trim();
            const textB = nameB.textContent.trim();
            if (textA === "HOME" || textB === "AWAY") { clearMatchup(); return; }
            const teamA = teamsData.find(t => t.name === textA);
            const teamB = teamsData.find(t => t.name === textB);
            if (teamA && teamB) renderMatchup(teamA, teamB);
        });

        observer.observe(nameA, { childList: true, characterData: true, subtree: true });
        observer.observe(nameB, { childList: true, characterData: true, subtree: true });
    }

    fetch("/api/teams").then(r => r.json()).then(t => {
        teamsData = t;
        watchBanner();
    });
})();
