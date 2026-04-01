(function () {
    "use strict";

    const RESULT_KO = { "승": "W", "패": "L", "무": "D", "W": "W", "L": "L", "D": "D" };

    function resultClass(raw) {
        const r = RESULT_KO[raw] || raw;
        if (r === "W") return "W";
        if (r === "L") return "L";
        return "D";
    }

    function buildTable(rows, containerId) {
        const wrap = document.getElementById(containerId);
        if (!wrap) return;

        const table = document.createElement("table");
        table.className = "standings-table";

        const thead = document.createElement("thead");
        thead.innerHTML = `
            <tr>
                <th class="col-rank">#</th>
                <th class="col-team">팀</th>
                <th class="col-num">경기</th>
                <th class="col-num">승</th>
                <th class="col-num">무</th>
                <th class="col-num">패</th>
                <th class="col-num">득</th>
                <th class="col-num">실</th>
                <th class="col-num">득실</th>
                <th class="col-pts">승점</th>
                <th class="col-recent">최근</th>
            </tr>`;
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        rows.forEach(row => {
            const tr = document.createElement("tr");

            // 순위 색상 처리 (1~3위 진출권, 하위권 강등)
            let rankClass = "";
            if (row.rank <= 2) rankClass = "rank-top";
            else if (row.rank <= 6) rankClass = "rank-mid";

            // 최근 결과 뱃지
            const recentHtml = (row.recent || []).map(r => {
                const cls = resultClass(r);
                return `<span class="st-badge ${cls}">${r}</span>`;
            }).join("");

            // 득실차 표시
            const gdStr = row.gd > 0 ? `+${row.gd}` : `${row.gd}`;

            tr.innerHTML = `
                <td class="col-rank ${rankClass}">${row.rank}</td>
                <td class="col-team">
                    <div class="st-team-cell">
                        ${row.emblem
                            ? `<img class="st-emblem" src="/static/img/emblems/${row.emblem}" alt="${row.short}">`
                            : `<span class="st-emblem-placeholder" style="background:${row.primary}">${row.short[0]}</span>`}
                        <span class="st-team-name">${row.short}</span>
                    </div>
                </td>
                <td class="col-num">${row.games}</td>
                <td class="col-num w">${row.w}</td>
                <td class="col-num d">${row.d}</td>
                <td class="col-num l">${row.l}</td>
                <td class="col-num">${row.gf}</td>
                <td class="col-num">${row.ga}</td>
                <td class="col-num gd">${gdStr}</td>
                <td class="col-pts">${row.pts}</td>
                <td class="col-recent">${recentHtml}</td>`;
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);

        wrap.innerHTML = "";
        wrap.appendChild(table);
    }

    // 드롭다운 토글
    const leagueSelect = document.getElementById("sidebar-league-select");
    if (leagueSelect) {
        leagueSelect.addEventListener("change", function () {
            const k1 = document.getElementById("sidebar-standings-k1");
            const k2 = document.getElementById("sidebar-standings-k2");
            if (this.value === "k1") {
                k1.style.display = "";
                k2.style.display = "none";
            } else {
                k1.style.display = "none";
                k2.style.display = "";
            }
        });
    }

    fetch("/api/standings")
        .then(r => r.json())
        .then(data => {
            buildTable(data.league1 || [], "sidebar-standings-k1");
            buildTable(data.league2 || [], "sidebar-standings-k2");
        })
        .catch(() => {
            ["sidebar-standings-k1", "sidebar-standings-k2"].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = `<div class="matchup-placeholder"><span>순위 불러오기 실패</span></div>`;
            });
        });
})();
