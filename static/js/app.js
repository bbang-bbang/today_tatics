(function () {
    "use strict";

    const PITCH_RATIO = 105 / 68;
    const DEFAULT_A_COLOR = "BLUE";
    const DEFAULT_B_COLOR = "RED";
    const PLAYER_RADIUS = 16;
    const FIELD_GREEN = "#2d8a4e";
    const LINE_COLOR = "#ffffffcc";

    // ── State ──────────────────────────────────────────────
    const state = {
        mode: "select",         // "select" | "draw"
        drawStyle: "arrow",     // "arrow" | "dashedArrow" | "line" | "dashedLine"
        drawColor: "rgba(255,255,255,0.85)",
        players: [],            // {id, team, x, y, name, number}
        lines: [],              // {sx,sy,ex,ey, style, color}
        dragging: null,
        dragOffset: { dx: 0, dy: 0 },
        drawingLine: null,
        formations: {},
        formationA: "4-4-2",
        formationB: "4-4-2",
        teams: [],
        teamA: null,
        teamB: null,
        kitA: "home",           // "home" | "away"
        kitB: "home",
        nextId: 100,
    };

    const canvas = document.getElementById("field");
    const ctx = canvas.getContext("2d");

    // ── Coordinate helpers ─────────────────────────────────
    const pad = 12;
    function fieldRect() { return { x: pad, y: pad, w: canvas.width - 2 * pad, h: canvas.height - 2 * pad }; }
    function fieldToCanvas(fx, fy) { const r = fieldRect(); return { px: r.x + fx * r.w, py: r.y + fy * r.h }; }
    function canvasToField(px, py) {
        const r = fieldRect();
        return { fx: Math.max(0, Math.min(1, (px - r.x) / r.w)), fy: Math.max(0, Math.min(1, (py - r.y) / r.h)) };
    }

    // ── Resize ─────────────────────────────────────────────
    function resize() {
        const container = document.getElementById("canvas-container");
        const maxW = container.clientWidth - 32;
        const maxH = container.clientHeight - 32;
        let w = maxW, h = w / PITCH_RATIO;
        if (h > maxH) { h = maxH; w = h * PITCH_RATIO; }
        canvas.width = Math.floor(w);
        canvas.height = Math.floor(h);
        render();
    }

    // ── Draw field ─────────────────────────────────────────
    function drawField() {
        const r = fieldRect();
        ctx.fillStyle = FIELD_GREEN;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        const stripeCount = 12;
        for (let i = 0; i < stripeCount; i++) {
            if (i % 2 === 0) continue;
            ctx.fillStyle = "rgba(255,255,255,0.03)";
            ctx.fillRect(r.x + i * (r.w / stripeCount), r.y, r.w / stripeCount, r.h);
        }
        ctx.strokeStyle = LINE_COLOR; ctx.lineWidth = 2;
        ctx.strokeRect(r.x, r.y, r.w, r.h);
        const cx = r.x + r.w / 2;
        ctx.beginPath(); ctx.moveTo(cx, r.y); ctx.lineTo(cx, r.y + r.h); ctx.stroke();
        const ccr = (9.15 / 105) * r.w;
        ctx.beginPath(); ctx.arc(cx, r.y + r.h / 2, ccr, 0, Math.PI * 2); ctx.stroke();
        ctx.fillStyle = LINE_COLOR; ctx.beginPath(); ctx.arc(cx, r.y + r.h / 2, 3, 0, Math.PI * 2); ctx.fill();
        const paW = (16.5 / 105) * r.w, paH = (40.32 / 68) * r.h, paY = r.y + (r.h - paH) / 2;
        ctx.strokeRect(r.x, paY, paW, paH); ctx.strokeRect(r.x + r.w - paW, paY, paW, paH);
        const gaW = (5.5 / 105) * r.w, gaH = (18.32 / 68) * r.h, gaY = r.y + (r.h - gaH) / 2;
        ctx.strokeRect(r.x, gaY, gaW, gaH); ctx.strokeRect(r.x + r.w - gaW, gaY, gaW, gaH);
        const psD = (11 / 105) * r.w;
        ctx.fillStyle = LINE_COLOR;
        for (const px of [r.x + psD, r.x + r.w - psD]) { ctx.beginPath(); ctx.arc(px, r.y + r.h / 2, 3, 0, Math.PI * 2); ctx.fill(); }
        const arcR = (9.15 / 105) * r.w, arcAngle = Math.acos(paW / arcR);
        ctx.beginPath(); ctx.arc(r.x + psD, r.y + r.h / 2, arcR, -arcAngle, arcAngle); ctx.stroke();
        ctx.beginPath(); ctx.arc(r.x + r.w - psD, r.y + r.h / 2, arcR, Math.PI - arcAngle, Math.PI + arcAngle); ctx.stroke();
        const car = (1 / 105) * r.w;
        [[r.x, r.y, 0, Math.PI / 2], [r.x + r.w, r.y, Math.PI / 2, Math.PI],
         [r.x + r.w, r.y + r.h, Math.PI, Math.PI * 1.5], [r.x, r.y + r.h, Math.PI * 1.5, Math.PI * 2]].forEach(([x, y, sa, ea]) => {
            ctx.beginPath(); ctx.arc(x, y, car, sa, ea); ctx.stroke();
        });
        const goalH = (7.32 / 68) * r.h, goalW = 6, goalY = r.y + (r.h - goalH) / 2;
        ctx.fillStyle = "rgba(255,255,255,0.15)";
        ctx.fillRect(r.x - goalW, goalY, goalW, goalH); ctx.fillRect(r.x + r.w, goalY, goalW, goalH);
        ctx.strokeRect(r.x - goalW, goalY, goalW, goalH); ctx.strokeRect(r.x + r.w, goalY, goalW, goalH);
    }

    // ── Draw lines/arrows ─────────────────────────────────
    function drawArrowHead(fromX, fromY, toX, toY, color) {
        const angle = Math.atan2(toY - fromY, toX - fromX), headLen = 12;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(toX, toY);
        ctx.lineTo(toX - headLen * Math.cos(angle - 0.4), toY - headLen * Math.sin(angle - 0.4));
        ctx.lineTo(toX - headLen * Math.cos(angle + 0.4), toY - headLen * Math.sin(angle + 0.4));
        ctx.closePath(); ctx.fill();
    }

    function drawOneLine(sx, sy, ex, ey, style, color, isPreview) {
        const from = fieldToCanvas(sx, sy), to = fieldToCanvas(ex, ey);
        const isDashed = style === "dashedArrow" || style === "dashedLine";
        const hasArrow = style === "arrow" || style === "dashedArrow";

        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 2.5;
        ctx.setLineDash(isDashed ? [10, 7] : []);
        if (isPreview) ctx.globalAlpha = 0.6;

        ctx.beginPath(); ctx.moveTo(from.px, from.py); ctx.lineTo(to.px, to.py); ctx.stroke();
        ctx.setLineDash([]);

        if (hasArrow) drawArrowHead(from.px, from.py, to.px, to.py, color);
        ctx.globalAlpha = 1.0;
    }

    function drawLines() {
        for (const l of state.lines) drawOneLine(l.sx, l.sy, l.ex, l.ey, l.style, l.color, false);
        if (state.drawingLine) {
            const l = state.drawingLine;
            drawOneLine(l.sx, l.sy, l.ex, l.ey, l.style, l.color, true);
        }
    }

    // ── Team color helpers ────────────────────────────────
    function isAway(side) {
        return side === "A" ? state.kitA === "away" : state.kitB === "away";
    }
    function getTeamColor(side) {
        const team = side === "A" ? state.teamA : state.teamB;
        if (!team) return side === "A" ? DEFAULT_A_COLOR : DEFAULT_B_COLOR;
        return isAway(side) ? "#ffffff" : team.primary;
    }
    function getTeamStroke(side) {
        const team = side === "A" ? state.teamA : state.teamB;
        if (!team) return isAway(side) ? "#888888" : "#ffffff";
        return isAway(side)
            ? (team.border_away || team.primary)
            : (team.border_home || team.secondary);
    }
    function getTeamTextColor(side) {
        return isAway(side) ? "#222222" : "#ffffff";
    }

    // ── Draw players ───────────────────────────────────────
    function drawPlayers() {
        for (const p of state.players) {
            const { px, py } = fieldToCanvas(p.x, p.y);
            const color = getTeamColor(p.team);
            const isDragging = state.dragging === p;
            const r = isDragging ? PLAYER_RADIUS + 3 : PLAYER_RADIUS;
            if (isDragging) { ctx.shadowColor = color; ctx.shadowBlur = 16; }
            ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI * 2);
            ctx.fillStyle = color; ctx.fill();
            ctx.strokeStyle = getTeamStroke(p.team); ctx.lineWidth = 2.5; ctx.stroke();
            ctx.shadowColor = "transparent"; ctx.shadowBlur = 0;
            const txtCol = getTeamTextColor(p.team);
            ctx.fillStyle = txtCol; ctx.font = "bold 11px 'Segoe UI', sans-serif";
            ctx.textAlign = "center"; ctx.textBaseline = "middle";
            ctx.fillText(p.number, px, py);
            ctx.font = "bold 10px 'Segoe UI', sans-serif";
            ctx.fillStyle = "#fff";
            ctx.shadowColor = "rgba(0,0,0,0.8)"; ctx.shadowBlur = 3;
            ctx.fillText(p.name, px, py + r + 12);
            ctx.shadowColor = "transparent"; ctx.shadowBlur = 0;
        }
    }

    // ── Render ─────────────────────────────────────────────
    function render() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawField(); drawLines(); drawPlayers();
    }

    // ── Formation loading ──────────────────────────────────
    function loadFormationSide(side, name) {
        const f = state.formations[name];
        if (!f) return;
        if (side === "A") state.formationA = name;
        else state.formationB = name;
        state.players = state.players.filter((p) => p.team !== side);
        const positions = side === "A" ? f.teamA : f.teamB;
        const labels = side === "A" ? f.labelsA : f.labelsB;
        for (let i = 0; i < positions.length; i++) {
            state.players.push({ id: state.nextId++, team: side, x: positions[i].x, y: positions[i].y, name: labels[i] || "", number: i + 1 });
        }
        render();
        renderBench();
    }

    function loadFormation(name) {
        state.formationA = name;
        state.formationB = name;
        state.players = [];
        const f = state.formations[name];
        if (!f) return;
        for (let i = 0; i < f.teamA.length; i++) {
            state.players.push({ id: state.nextId++, team: "A", x: f.teamA[i].x, y: f.teamA[i].y, name: f.labelsA[i] || "", number: i + 1 });
        }
        for (let i = 0; i < f.teamB.length; i++) {
            state.players.push({ id: state.nextId++, team: "B", x: f.teamB[i].x, y: f.teamB[i].y, name: f.labelsB[i] || "", number: i + 1 });
        }
        document.querySelectorAll(".formation-select-team").forEach((sel) => { sel.value = name; });
        render();
        renderBench();
    }

    // ── Hit test ───────────────────────────────────────────
    function hitTest(px, py) {
        for (let i = state.players.length - 1; i >= 0; i--) {
            const p = state.players[i];
            const { px: cx, py: cy } = fieldToCanvas(p.x, p.y);
            if (Math.sqrt((px - cx) ** 2 + (py - cy) ** 2) <= PLAYER_RADIUS + 4) return p;
        }
        return null;
    }

    // ── Pointer events ─────────────────────────────────────
    function getPointerPos(e) {
        const rect = canvas.getBoundingClientRect();
        return { px: (e.clientX - rect.left) * (canvas.width / rect.width), py: (e.clientY - rect.top) * (canvas.height / rect.height) };
    }

    canvas.addEventListener("pointerdown", (e) => {
        if (editingPlayer) return;
        const { px, py } = getPointerPos(e);
        const { fx, fy } = canvasToField(px, py);
        if (state.mode === "select") {
            const player = hitTest(px, py);
            if (player) {
                state.dragging = player;
                const { px: cx, py: cy } = fieldToCanvas(player.x, player.y);
                state.dragOffset = { dx: cx - px, dy: cy - py };
                canvas.setPointerCapture(e.pointerId);
            }
        } else if (state.mode === "draw") {
            state.drawingLine = { sx: fx, sy: fy, ex: fx, ey: fy, style: state.drawStyle, color: state.drawColor };
            canvas.setPointerCapture(e.pointerId);
        }
    });

    canvas.addEventListener("pointermove", (e) => {
        const { px, py } = getPointerPos(e);
        if (state.mode === "select" && state.dragging) {
            const { fx, fy } = canvasToField(px + state.dragOffset.dx, py + state.dragOffset.dy);
            state.dragging.x = fx; state.dragging.y = fy; render();
        } else if (state.mode === "draw" && state.drawingLine) {
            const { fx, fy } = canvasToField(px, py);
            state.drawingLine.ex = fx; state.drawingLine.ey = fy; render();
        } else if (state.mode === "select") {
            canvas.style.cursor = hitTest(px, py) ? "grab" : "default";
        }
    });

    canvas.addEventListener("pointerup", () => {
        if (state.mode === "select") { state.dragging = null; }
        else if (state.mode === "draw" && state.drawingLine) {
            const l = state.drawingLine;
            if (Math.sqrt((l.ex - l.sx) ** 2 + (l.ey - l.sy) ** 2) > 0.01) {
                state.lines.push({ sx: l.sx, sy: l.sy, ex: l.ex, ey: l.ey, style: l.style, color: l.color });
            }
            state.drawingLine = null; render();
        }
    });

    // ── Player edit popup (double-click) ───────────────────
    const editPopup = document.getElementById("player-edit-popup");
    const editNumber = document.getElementById("player-edit-number");
    const editName = document.getElementById("player-edit-name");
    const editConfirm = document.getElementById("player-edit-confirm");
    const editClose = document.getElementById("player-edit-close");
    const editTeamLabel = document.getElementById("player-edit-team-label");
    let editingPlayer = null;

    function openEditPopup(player, screenX, screenY) {
        editingPlayer = player;
        editNumber.value = player.number;
        editName.value = player.name;
        editTeamLabel.style.background = getTeamColor(player.team);
        editTeamLabel.textContent = player.team === "A" ? (state.teamA ? state.teamA.short : "HOME") : (state.teamB ? state.teamB.short : "AWAY");
        let left = screenX + 12, top = screenY - 20;
        if (left + 200 > window.innerWidth) left = screenX - 212;
        if (top + 160 > window.innerHeight) top = window.innerHeight - 168;
        if (top < 8) top = 8;
        editPopup.style.left = left + "px"; editPopup.style.top = top + "px";
        editPopup.classList.remove("hidden"); editName.focus(); editName.select();
    }
    function closeEditPopup() { editPopup.classList.add("hidden"); editingPlayer = null; }
    function confirmEdit() {
        if (!editingPlayer) return;
        const num = parseInt(editNumber.value, 10);
        if (!isNaN(num) && num >= 1 && num <= 99) editingPlayer.number = num;
        editingPlayer.name = editName.value.trim() || editingPlayer.name;
        closeEditPopup(); render(); renderBench();
    }
    editConfirm.addEventListener("click", confirmEdit);
    editClose.addEventListener("click", closeEditPopup);
    editPopup.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); confirmEdit(); } if (e.key === "Escape") closeEditPopup(); });
    document.addEventListener("pointerdown", (e) => { if (editingPlayer && !editPopup.contains(e.target) && e.target !== canvas) closeEditPopup(); });
    canvas.addEventListener("dblclick", (e) => {
        if (state.mode !== "select") return;
        const { px, py } = getPointerPos(e);
        const player = hitTest(px, py);
        if (player) openEditPopup(player, e.clientX, e.clientY);
    });

    // ── Right-click to remove player ──────────────────────
    canvas.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        const { px, py } = getPointerPos(e);
        const player = hitTest(px, py);
        if (player) {
            state.players = state.players.filter((p) => p !== player);
            render(); renderBench();
        }
    });

    // ── Mode & draw style ─────────────────────────────────
    const btnSelect = document.getElementById("btn-select");
    const drawModeBtns = document.querySelectorAll(".draw-mode-btn");

    function setMode(mode, drawStyle) {
        state.mode = mode;
        if (drawStyle) state.drawStyle = drawStyle;
        btnSelect.classList.toggle("active", mode === "select");
        drawModeBtns.forEach((b) => b.classList.toggle("active", mode === "draw" && b.dataset.draw === state.drawStyle));
        canvas.style.cursor = mode === "draw" ? "crosshair" : "default";
    }

    btnSelect.addEventListener("click", () => setMode("select"));
    drawModeBtns.forEach((btn) => btn.addEventListener("click", () => setMode("draw", btn.dataset.draw)));

    // ── Color swatches ────────────────────────────────────
    const swatches = document.querySelectorAll(".color-swatch");
    swatches.forEach((sw) => sw.addEventListener("click", () => {
        swatches.forEach((s) => s.classList.remove("active"));
        sw.classList.add("active");
        state.drawColor = sw.dataset.color;
    }));

    // ── Toolbar actions ───────────────────────────────────
    document.getElementById("btn-clear-lines").addEventListener("click", () => { state.lines = []; render(); });
    document.getElementById("btn-undo-line").addEventListener("click", () => { state.lines.pop(); render(); });
    document.getElementById("btn-reset").addEventListener("click", () => { state.lines = []; loadFormationSide("A", state.formationA); loadFormationSide("B", state.formationB); });
    document.querySelectorAll(".formation-select-team").forEach((sel) => {
        sel.addEventListener("change", (e) => { loadFormationSide(sel.dataset.side, e.target.value); });
    });

    // ── Toast ─────────────────────────────────────────────
    let toastEl = document.createElement("div"); toastEl.className = "toast"; document.body.appendChild(toastEl);
    let toastTimer = null;
    function showToast(msg) { toastEl.textContent = msg; toastEl.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => toastEl.classList.remove("show"), 2000); }

    // ── Bench panel ───────────────────────────────────────
    const benchListA = document.getElementById("bench-list-a");
    const benchListB = document.getElementById("bench-list-b");
    const benchNameA = document.getElementById("bench-name-a");
    const benchNameB = document.getElementById("bench-name-b");

    function renderBench() {
        benchNameA.textContent = state.teamA ? state.teamA.short : "HOME";
        benchNameB.textContent = state.teamB ? state.teamB.short : "AWAY";
        renderBenchList("A", benchListA);
        renderBenchList("B", benchListB);
    }

    function renderBenchList(side, container) {
        container.innerHTML = "";
        const teamPlayers = state.players.filter((p) => p.team === side);
        if (teamPlayers.length === 0) {
            container.innerHTML = '<div style="color:#555;font-size:0.72rem;padding:8px;text-align:center">선수 없음</div>';
            return;
        }
        for (const p of teamPlayers) {
            const item = document.createElement("div");
            item.className = "bench-player-item";

            const dot = document.createElement("div");
            dot.className = "bench-player-dot";
            dot.style.background = getTeamColor(side);
            dot.textContent = p.number;

            const name = document.createElement("span");
            name.className = "bench-player-name";
            name.textContent = p.name;

            const editBtn = document.createElement("button");
            editBtn.className = "bench-player-edit";
            editBtn.textContent = "✎";
            editBtn.title = "이름/등번호 수정";
            editBtn.addEventListener("click", (e) => {
                const rect = editBtn.getBoundingClientRect();
                openEditPopup(p, rect.left - 210, rect.top);
            });

            const removeBtn = document.createElement("button");
            removeBtn.className = "bench-player-remove";
            removeBtn.innerHTML = "&times;";
            removeBtn.title = "필드에서 제거";
            removeBtn.addEventListener("click", () => {
                state.players = state.players.filter((pl) => pl !== p);
                render(); renderBench();
            });

            item.appendChild(dot); item.appendChild(name); item.appendChild(editBtn); item.appendChild(removeBtn);
            container.appendChild(item);
        }
    }

    function addPlayer(side) {
        const teamPlayers = state.players.filter((p) => p.team === side);
        const num = teamPlayers.length + 1;
        const defaultX = side === "A" ? 0.25 : 0.75;
        state.players.push({
            id: state.nextId++, team: side,
            x: defaultX + (Math.random() - 0.5) * 0.1,
            y: 0.3 + Math.random() * 0.4,
            name: "선수" + num, number: num,
        });
        render(); renderBench();
    }

    document.querySelectorAll(".bench-add-btn").forEach((btn) => btn.addEventListener("click", () => addPlayer(btn.dataset.side)));

    // ── Save / Load helpers ───────────────────────────────
    function getStateSnapshot() {
        return {
            formation: state.formationA,
            formationA: state.formationA,
            formationB: state.formationB,
            players: state.players.map((p) => ({ id: p.id, team: p.team, x: p.x, y: p.y, name: p.name, number: p.number })),
            lines: state.lines.map((l) => ({ sx: l.sx, sy: l.sy, ex: l.ex, ey: l.ey, style: l.style, color: l.color })),
            teamAId: state.teamA ? state.teamA.id : null,
            teamBId: state.teamB ? state.teamB.id : null,
        };
    }

    function applySnapshot(data) {
        if (data.teamAId && state.teams.length) state.teamA = state.teams.find((t) => t.id === data.teamAId) || null;
        if (data.teamBId && state.teams.length) state.teamB = state.teams.find((t) => t.id === data.teamBId) || null;
        updateBanner(); updateLegend();
        state.formationA = data.formationA || data.formation || "4-4-2";
        state.formationB = data.formationB || data.formation || "4-4-2";
        document.querySelector('.formation-select-team[data-side="A"]').value = state.formationA;
        document.querySelector('.formation-select-team[data-side="B"]').value = state.formationB;
        state.players = data.players || [];
        // backward compat: old saves use "arrows"
        state.lines = (data.lines || data.arrows || []).map((l) => ({
            sx: l.sx, sy: l.sy, ex: l.ex, ey: l.ey,
            style: l.style || "arrow", color: l.color || "rgba(255,255,255,0.85)",
        }));
        render(); renderBench();
    }

    function formatDate(iso) {
        if (!iso) return "";
        const d = new Date(iso), p = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    }

    // ── Save modal ────────────────────────────────────────
    const saveModal = document.getElementById("save-modal");
    const saveModalTitle = document.getElementById("save-modal-title");
    const saveNameInput = document.getElementById("save-name-input");
    const saveModalCancel = document.getElementById("save-modal-cancel");
    const saveModalConfirm = document.getElementById("save-modal-confirm");
    let saveOverwriteId = null;

    function openSaveModal(overwriteId, defaultName) {
        saveOverwriteId = overwriteId || null;
        saveModalTitle.textContent = overwriteId ? "전술 덮어쓰기" : "전술 저장";
        saveModalConfirm.textContent = overwriteId ? "덮어쓰기" : "저장";
        saveNameInput.value = defaultName || "";
        saveModal.classList.remove("hidden"); saveNameInput.focus();
    }
    function closeSaveModal() { saveModal.classList.add("hidden"); saveOverwriteId = null; }
    saveModal.querySelector(".modal-backdrop").addEventListener("click", closeSaveModal);
    saveModalCancel.addEventListener("click", closeSaveModal);
    saveNameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") saveModalConfirm.click(); if (e.key === "Escape") closeSaveModal(); });

    saveModalConfirm.addEventListener("click", async () => {
        const name = saveNameInput.value.trim();
        if (!name) { saveNameInput.focus(); return; }
        const snap = getStateSnapshot(); snap.name = name;
        if (saveOverwriteId) {
            await fetch(`/api/saves/${saveOverwriteId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(snap) });
            showToast("전술이 덮어쓰기 되었습니다.");
        } else {
            await fetch("/api/saves", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(snap) });
            showToast("전술이 저장되었습니다.");
        }
        closeSaveModal();
    });
    document.getElementById("btn-save").addEventListener("click", () => openSaveModal(null, ""));

    // ── Load modal ────────────────────────────────────────
    const loadModal = document.getElementById("load-modal");
    const savesList = document.getElementById("saves-list");
    const loadModalClose = document.getElementById("load-modal-close");
    function closeLoadModal() { loadModal.classList.add("hidden"); }
    loadModal.querySelector(".modal-backdrop").addEventListener("click", closeLoadModal);
    loadModalClose.addEventListener("click", closeLoadModal);

    function escapeHtml(str) { const d = document.createElement("div"); d.textContent = str; return d.innerHTML; }
    function escapeAttr(str) { return str.replace(/"/g, "&quot;").replace(/'/g, "&#39;"); }

    async function openLoadModal() {
        loadModal.classList.remove("hidden");
        savesList.innerHTML = '<p class="empty-msg">불러오는 중...</p>';
        const res = await fetch("/api/saves"); const saves = await res.json();
        if (saves.length === 0) { savesList.innerHTML = '<p class="empty-msg">저장된 전술이 없습니다.</p>'; return; }
        savesList.innerHTML = "";
        for (const s of saves) {
            const item = document.createElement("div"); item.className = "save-item";
            item.innerHTML = `<div class="save-item-info"><div class="save-item-name">${escapeHtml(s.name)}</div><div class="save-item-meta">${s.formation} &middot; ${formatDate(s.updatedAt)}</div></div>
            <div class="save-item-actions"><button class="btn-load-item" data-id="${s.id}">불러오기</button><button class="btn-overwrite-item" data-id="${s.id}" data-name="${escapeAttr(s.name)}">덮어쓰기</button><button class="btn-delete-item" data-id="${s.id}">삭제</button></div>`;
            savesList.appendChild(item);
        }
        savesList.onclick = async (e) => {
            const btn = e.target.closest("button"); if (!btn) return;
            const id = btn.dataset.id;
            if (btn.classList.contains("btn-load-item")) { const r = await fetch(`/api/saves/${id}`); applySnapshot(await r.json()); closeLoadModal(); showToast("전술을 불러왔습니다."); }
            else if (btn.classList.contains("btn-overwrite-item")) { closeLoadModal(); openSaveModal(id, btn.dataset.name); }
            else if (btn.classList.contains("btn-delete-item")) { if (!confirm("정말 삭제하시겠습니까?")) return; await fetch(`/api/saves/${id}`, { method: "DELETE" }); showToast("삭제되었습니다."); openLoadModal(); }
        };
    }
    document.getElementById("btn-load").addEventListener("click", openLoadModal);

    // ── Team selection ────────────────────────────────────
    const teamModal = document.getElementById("team-modal");
    const teamModalTitle = document.getElementById("team-modal-title");
    const teamGrid = document.getElementById("team-grid");
    const teamModalClose = document.getElementById("team-modal-close");
    const leagueTabs = document.querySelectorAll(".league-tab");
    let pickingSide = "A", currentLeague = "K1";

    function createLogoBadge(team, size) {
        const el = document.createElement("div");
        Object.assign(el.style, { width: size+"px", height: size+"px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: "0", overflow: "hidden", background: "#1a1a2e", border: `2px solid ${team.secondary}` });
        if (team.emblem) {
            const img = document.createElement("img");
            img.src = `/static/img/emblems/${team.emblem}`; img.alt = team.short;
            Object.assign(img.style, { width: "90%", height: "90%", objectFit: "contain" });
            img.onerror = () => { img.remove(); el.textContent = team.short; Object.assign(el.style, { fontWeight: "800", fontSize: (size*0.28)+"px", color: team.accent==="#000000"?"#000":"#fff", background: `linear-gradient(135deg,${team.primary} 60%,${team.accent} 100%)` }); };
            el.appendChild(img);
        } else {
            el.textContent = team.short;
            Object.assign(el.style, { fontWeight: "800", fontSize: (size*0.28)+"px", color: team.accent==="#000000"?"#000":"#fff", background: `linear-gradient(135deg,${team.primary} 60%,${team.accent} 100%)` });
        }
        return el;
    }

    function renderTeamGrid() {
        teamGrid.innerHTML = "";
        const filtered = state.teams.filter((t) => t.league === currentLeague);
        const cur = pickingSide === "A" ? state.teamA : state.teamB;
        for (const team of filtered) {
            const card = document.createElement("div"); card.className = "team-card";
            if (cur && cur.id === team.id) card.classList.add("selected");
            const logo = createLogoBadge(team, 36); logo.classList.add("team-card-logo");
            const nm = document.createElement("span"); nm.className = "team-card-name"; nm.textContent = team.name;
            card.appendChild(logo); card.appendChild(nm);
            card.addEventListener("click", () => selectTeam(team));
            teamGrid.appendChild(card);
        }
    }

    function selectTeam(team) {
        console.log("selectTeam:", team.id, team.name, "league:", team.league, "primary:", team.primary, "side:", pickingSide);
        if (pickingSide === "A") state.teamA = team; else state.teamB = team;
        updateBanner(); updateLegend(); render(); renderBench();
        closeTeamModal(); showToast(`${team.name} 선택 완료`);
    }

    function setBannerBadge(badgeEl, team, fallbackColor, fallbackLetter) {
        badgeEl.innerHTML = "";
        if (team) {
            badgeEl.style.background = "#1a1a2e"; badgeEl.style.borderColor = team.secondary;
            if (team.emblem) {
                const img = document.createElement("img"); img.src = `/static/img/emblems/${team.emblem}`; img.alt = team.short;
                Object.assign(img.style, { width: "85%", height: "85%", objectFit: "contain" });
                badgeEl.appendChild(img);
            } else {
                const txt = document.createElement("span"); txt.className = "badge-letter"; txt.textContent = team.short; txt.style.fontSize = "0.85rem";
                badgeEl.style.background = `linear-gradient(135deg,${team.primary} 60%,${team.accent} 100%)`;
                badgeEl.appendChild(txt);
            }
        } else {
            badgeEl.style.background = fallbackColor; badgeEl.style.borderColor = "rgba(255,255,255,0.2)";
            badgeEl.innerHTML = `<span class="badge-letter">${fallbackLetter}</span>`;
        }
    }

    function updateBanner() {
        setBannerBadge(document.getElementById("badge-a"), state.teamA, DEFAULT_A_COLOR, "H");
        document.getElementById("name-a").textContent = state.teamA ? state.teamA.name : "HOME";
        setBannerBadge(document.getElementById("badge-b"), state.teamB, DEFAULT_B_COLOR, "A");
        document.getElementById("name-b").textContent = state.teamB ? state.teamB.name : "AWAY";
    }

    function updateLegend() {
        const la = document.querySelector(".legend-item.team-a"), lb = document.querySelector(".legend-item.team-b");
        la.textContent = state.teamA ? state.teamA.short : "HOME";
        lb.textContent = state.teamB ? state.teamB.short : "AWAY";
        la.style.setProperty("--team-color", getTeamColor("A"));
        lb.style.setProperty("--team-color", getTeamColor("B"));
    }

    function openTeamModal(side) { pickingSide = side; teamModalTitle.textContent = side === "A" ? "HOME 팀 선택" : "AWAY 팀 선택"; teamModal.classList.remove("hidden"); renderTeamGrid(); }
    function closeTeamModal() { teamModal.classList.add("hidden"); }
    teamModal.querySelector(".modal-backdrop").addEventListener("click", closeTeamModal);
    teamModalClose.addEventListener("click", closeTeamModal);
    leagueTabs.forEach((tab) => tab.addEventListener("click", () => { leagueTabs.forEach((t) => t.classList.remove("active")); tab.classList.add("active"); currentLeague = tab.dataset.league; renderTeamGrid(); }));
    document.querySelectorAll(".team-pick-btn").forEach((btn) => btn.addEventListener("click", () => openTeamModal(btn.dataset.side)));
    document.getElementById("slot-a").addEventListener("click", (e) => { if (!e.target.closest(".team-pick-btn") && !e.target.closest(".formation-select-team") && !e.target.closest(".kit-toggle-btn")) openTeamModal("A"); });
    document.getElementById("slot-b").addEventListener("click", (e) => { if (!e.target.closest(".team-pick-btn") && !e.target.closest(".formation-select-team") && !e.target.closest(".kit-toggle-btn")) openTeamModal("B"); });

    // ── HOME / AWAY kit toggle ──────────────────────────
    document.querySelectorAll(".kit-toggle-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const side = btn.dataset.side;
            const kit = btn.dataset.kit;
            if (side === "A") state.kitA = kit; else state.kitB = kit;
            // update button states
            document.querySelectorAll(`.kit-toggle-btn[data-side="${side}"]`).forEach((b) => {
                b.classList.toggle("active", b.dataset.kit === kit);
            });
            render(); renderBench();
        });
    });

    // ── Squad save / load ─────────────────────────────────
    const squadModal = document.getElementById("squad-modal");
    const squadModalTitle = document.getElementById("squad-modal-title");
    const squadList = document.getElementById("squad-list");
    const squadModalClose = document.getElementById("squad-modal-close");
    let squadLoadSide = "A";

    function closeSquadModal() { squadModal.classList.add("hidden"); }
    squadModal.querySelector(".modal-backdrop").addEventListener("click", closeSquadModal);
    squadModalClose.addEventListener("click", closeSquadModal);

    document.querySelectorAll(".squad-save-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const side = btn.dataset.side;
            const team = side === "A" ? state.teamA : state.teamB;
            const teamPlayers = state.players.filter((p) => p.team === side);
            if (teamPlayers.length === 0) { showToast("저장할 선수가 없습니다."); return; }

            const teamName = team ? team.short : (side === "A" ? "HOME" : "AWAY");
            const name = prompt(`스쿼드 이름을 입력하세요:`, teamName + " 스쿼드");
            if (!name) return;

            await fetch("/api/squads", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    teamId: team ? team.id : "",
                    name: name,
                    players: teamPlayers.map((p) => ({ number: p.number, name: p.name })),
                }),
            });
            showToast("스쿼드가 저장되었습니다.");
        });
    });

    document.querySelectorAll(".squad-load-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            squadLoadSide = btn.dataset.side;
            const team = squadLoadSide === "A" ? state.teamA : state.teamB;
            squadModalTitle.textContent = (team ? team.short : (squadLoadSide === "A" ? "HOME" : "AWAY")) + " 스쿼드 불러오기";
            squadModal.classList.remove("hidden");
            squadList.innerHTML = '<p class="empty-msg">불러오는 중...</p>';

            const url = team ? `/api/squads?teamId=${team.id}` : "/api/squads";
            const res = await fetch(url);
            const squads = await res.json();
            if (squads.length === 0) { squadList.innerHTML = '<p class="empty-msg">저장된 스쿼드가 없습니다.</p>'; return; }

            squadList.innerHTML = "";
            for (const s of squads) {
                const item = document.createElement("div"); item.className = "save-item";
                const teamObj = state.teams.find((t) => t.id === s.teamId);
                const teamLabel = teamObj ? teamObj.short : "";
                item.innerHTML = `<div class="save-item-info"><div class="save-item-name">${escapeHtml(s.name)}</div><div class="save-item-meta">${teamLabel} &middot; ${s.playerCount}명</div></div>
                <div class="save-item-actions"><button class="btn-load-item" data-id="${s.id}">적용</button><button class="btn-delete-item" data-id="${s.id}">삭제</button></div>`;
                squadList.appendChild(item);
            }
            squadList.onclick = async (e) => {
                const btn2 = e.target.closest("button"); if (!btn2) return;
                const id = btn2.dataset.id;
                if (btn2.classList.contains("btn-load-item")) {
                    const r = await fetch(`/api/squads/${id}`);
                    const data = await r.json();
                    applySquad(squadLoadSide, data);
                    closeSquadModal();
                    showToast("스쿼드를 적용했습니다.");
                } else if (btn2.classList.contains("btn-delete-item")) {
                    if (!confirm("정말 삭제하시겠습니까?")) return;
                    await fetch(`/api/squads/${id}`, { method: "DELETE" });
                    showToast("삭제되었습니다.");
                    btn.click(); // re-open
                }
            };
        });
    });

    function applySquad(side, squadData) {
        // Remove existing players of this side
        state.players = state.players.filter((p) => p.team !== side);
        // Get formation positions for this side
        const f = state.formations[side === "A" ? state.formationA : state.formationB];
        const positions = side === "A" ? f.teamA : f.teamB;
        const squadPlayers = squadData.players || [];
        for (let i = 0; i < squadPlayers.length; i++) {
            const pos = positions[i] || { x: side === "A" ? 0.25 : 0.75, y: 0.3 + (i * 0.04) };
            state.players.push({
                id: state.nextId++, team: side,
                x: pos.x, y: pos.y,
                name: squadPlayers[i].name, number: squadPlayers[i].number,
            });
        }
        // Also set the team from squad if not already set
        if (squadData.teamId) {
            const team = state.teams.find((t) => t.id === squadData.teamId);
            if (team) {
                if (side === "A") state.teamA = team; else state.teamB = team;
                updateBanner(); updateLegend();
            }
        }
        render(); renderBench();
    }

    // ── Snapshot: include kit + icon color state ─────────
    const _origSnapshot = getStateSnapshot;
    getStateSnapshot = function () {
        const snap = _origSnapshot();
        snap.kitA = state.kitA;
        snap.kitB = state.kitB;
        return snap;
    };
    const _origApply = applySnapshot;
    applySnapshot = function (data) {
        state.kitA = data.kitA || "home";
        state.kitB = data.kitB || "home";
        document.querySelectorAll('.kit-toggle-btn[data-side="A"]').forEach((b) => b.classList.toggle("active", b.dataset.kit === state.kitA));
        document.querySelectorAll('.kit-toggle-btn[data-side="B"]').forEach((b) => b.classList.toggle("active", b.dataset.kit === state.kitB));
        _origApply(data);
    };

    // ── Init ───────────────────────────────────────────────
    window.addEventListener("resize", resize);
    Promise.all([
        fetch("/api/formations").then((r) => r.json()),
        fetch("/api/teams").then((r) => r.json()),
    ]).then(([formData, teamData]) => {
        state.formations = formData; state.teams = teamData;
        resize(); loadFormation("4-4-2");
    });
})();
