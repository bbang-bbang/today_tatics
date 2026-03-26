(function () {
    "use strict";

    const PITCH_RATIO = 105 / 68;
    const TEAM_A_COLOR = "#2563eb";
    const TEAM_B_COLOR = "#dc2626";
    const PLAYER_RADIUS = 16;
    const FIELD_GREEN = "#2d8a4e";
    const LINE_COLOR = "#ffffffcc";

    // ── State ──────────────────────────────────────────────
    const state = {
        mode: "select",       // "select" | "draw"
        players: [],          // {id, team, x, y, name, number}
        arrows: [],           // {sx, sy, ex, ey}
        dragging: null,
        dragOffset: { dx: 0, dy: 0 },
        drawingArrow: null,
        formations: {},
        currentFormation: "4-4-2",
    };

    const canvas = document.getElementById("field");
    const ctx = canvas.getContext("2d");

    // ── Coordinate helpers ─────────────────────────────────
    const pad = 12;

    function fieldRect() {
        return { x: pad, y: pad, w: canvas.width - 2 * pad, h: canvas.height - 2 * pad };
    }

    function fieldToCanvas(fx, fy) {
        const r = fieldRect();
        return { px: r.x + fx * r.w, py: r.y + fy * r.h };
    }

    function canvasToField(px, py) {
        const r = fieldRect();
        return {
            fx: Math.max(0, Math.min(1, (px - r.x) / r.w)),
            fy: Math.max(0, Math.min(1, (py - r.y) / r.h)),
        };
    }

    // ── Resize ─────────────────────────────────────────────
    function resize() {
        const container = document.getElementById("canvas-container");
        const maxW = container.clientWidth - 32;
        const maxH = container.clientHeight - 32;
        let w = maxW;
        let h = w / PITCH_RATIO;
        if (h > maxH) {
            h = maxH;
            w = h * PITCH_RATIO;
        }
        canvas.width = Math.floor(w);
        canvas.height = Math.floor(h);
        render();
    }

    // ── Draw field ─────────────────────────────────────────
    function drawField() {
        const r = fieldRect();
        // grass
        ctx.fillStyle = FIELD_GREEN;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // grass stripes
        const stripeCount = 12;
        for (let i = 0; i < stripeCount; i++) {
            if (i % 2 === 0) continue;
            ctx.fillStyle = "rgba(255,255,255,0.03)";
            const sw = r.w / stripeCount;
            ctx.fillRect(r.x + i * sw, r.y, sw, r.h);
        }

        ctx.strokeStyle = LINE_COLOR;
        ctx.lineWidth = 2;

        // outer boundary
        ctx.strokeRect(r.x, r.y, r.w, r.h);

        // halfway line
        const cx = r.x + r.w / 2;
        ctx.beginPath();
        ctx.moveTo(cx, r.y);
        ctx.lineTo(cx, r.y + r.h);
        ctx.stroke();

        // center circle
        const ccr = (9.15 / 105) * r.w;
        ctx.beginPath();
        ctx.arc(cx, r.y + r.h / 2, ccr, 0, Math.PI * 2);
        ctx.stroke();

        // center spot
        ctx.fillStyle = LINE_COLOR;
        ctx.beginPath();
        ctx.arc(cx, r.y + r.h / 2, 3, 0, Math.PI * 2);
        ctx.fill();

        // penalty areas
        const paW = (16.5 / 105) * r.w;
        const paH = (40.32 / 68) * r.h;
        const paY = r.y + (r.h - paH) / 2;
        ctx.strokeRect(r.x, paY, paW, paH);
        ctx.strokeRect(r.x + r.w - paW, paY, paW, paH);

        // goal areas
        const gaW = (5.5 / 105) * r.w;
        const gaH = (18.32 / 68) * r.h;
        const gaY = r.y + (r.h - gaH) / 2;
        ctx.strokeRect(r.x, gaY, gaW, gaH);
        ctx.strokeRect(r.x + r.w - gaW, gaY, gaW, gaH);

        // penalty spots
        const psD = (11 / 105) * r.w;
        ctx.fillStyle = LINE_COLOR;
        for (const px of [r.x + psD, r.x + r.w - psD]) {
            ctx.beginPath();
            ctx.arc(px, r.y + r.h / 2, 3, 0, Math.PI * 2);
            ctx.fill();
        }

        // penalty arcs
        const arcR = (9.15 / 105) * r.w;
        const arcAngle = Math.acos(paW / arcR);
        // left arc
        ctx.beginPath();
        ctx.arc(r.x + psD, r.y + r.h / 2, arcR, -arcAngle, arcAngle);
        ctx.stroke();
        // right arc
        ctx.beginPath();
        ctx.arc(r.x + r.w - psD, r.y + r.h / 2, arcR, Math.PI - arcAngle, Math.PI + arcAngle);
        ctx.stroke();

        // corner arcs
        const car = (1 / 105) * r.w;
        const corners = [
            [r.x, r.y, 0, Math.PI / 2],
            [r.x + r.w, r.y, Math.PI / 2, Math.PI],
            [r.x + r.w, r.y + r.h, Math.PI, Math.PI * 1.5],
            [r.x, r.y + r.h, Math.PI * 1.5, Math.PI * 2],
        ];
        for (const [x, y, sa, ea] of corners) {
            ctx.beginPath();
            ctx.arc(x, y, car, sa, ea);
            ctx.stroke();
        }

        // goals (behind goal lines)
        const goalH = (7.32 / 68) * r.h;
        const goalW = 6;
        const goalY = r.y + (r.h - goalH) / 2;
        ctx.fillStyle = "rgba(255,255,255,0.15)";
        ctx.fillRect(r.x - goalW, goalY, goalW, goalH);
        ctx.fillRect(r.x + r.w, goalY, goalW, goalH);
        ctx.strokeRect(r.x - goalW, goalY, goalW, goalH);
        ctx.strokeRect(r.x + r.w, goalY, goalW, goalH);
    }

    // ── Draw arrows ────────────────────────────────────────
    function drawArrowHead(fromX, fromY, toX, toY) {
        const angle = Math.atan2(toY - fromY, toX - fromX);
        const headLen = 12;
        ctx.beginPath();
        ctx.moveTo(toX, toY);
        ctx.lineTo(toX - headLen * Math.cos(angle - 0.4), toY - headLen * Math.sin(angle - 0.4));
        ctx.lineTo(toX - headLen * Math.cos(angle + 0.4), toY - headLen * Math.sin(angle + 0.4));
        ctx.closePath();
        ctx.fill();
    }

    function drawArrow(sx, sy, ex, ey, dashed) {
        const from = fieldToCanvas(sx, sy);
        const to = fieldToCanvas(ex, ey);

        ctx.strokeStyle = "rgba(255,255,255,0.85)";
        ctx.fillStyle = "rgba(255,255,255,0.85)";
        ctx.lineWidth = 2.5;
        if (dashed) ctx.setLineDash([8, 6]);
        else ctx.setLineDash([]);

        ctx.beginPath();
        ctx.moveTo(from.px, from.py);
        ctx.lineTo(to.px, to.py);
        ctx.stroke();
        ctx.setLineDash([]);

        drawArrowHead(from.px, from.py, to.px, to.py);
    }

    function drawArrows() {
        for (const a of state.arrows) {
            drawArrow(a.sx, a.sy, a.ex, a.ey, false);
        }
        if (state.drawingArrow) {
            const a = state.drawingArrow;
            drawArrow(a.sx, a.sy, a.ex, a.ey, true);
        }
    }

    // ── Draw players ───────────────────────────────────────
    function drawPlayers() {
        for (const p of state.players) {
            const { px, py } = fieldToCanvas(p.x, p.y);
            const color = p.team === "A" ? TEAM_A_COLOR : TEAM_B_COLOR;
            const isDragging = state.dragging === p;
            const r = isDragging ? PLAYER_RADIUS + 3 : PLAYER_RADIUS;

            // glow when dragging
            if (isDragging) {
                ctx.shadowColor = color;
                ctx.shadowBlur = 16;
            }

            // circle
            ctx.beginPath();
            ctx.arc(px, py, r, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;

            // number
            ctx.fillStyle = "#fff";
            ctx.font = "bold 11px 'Segoe UI', sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(p.number, px, py);

            // label
            ctx.font = "bold 10px 'Segoe UI', sans-serif";
            ctx.fillStyle = "#fff";
            ctx.shadowColor = "rgba(0,0,0,0.8)";
            ctx.shadowBlur = 3;
            ctx.fillText(p.name, px, py + r + 12);
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
        }
    }

    // ── Render ─────────────────────────────────────────────
    function render() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawField();
        drawArrows();
        drawPlayers();
    }

    // ── Formation loading ──────────────────────────────────
    function loadFormation(name) {
        const f = state.formations[name];
        if (!f) return;
        state.currentFormation = name;
        state.players = [];

        for (let i = 0; i < f.teamA.length; i++) {
            state.players.push({
                id: i,
                team: "A",
                x: f.teamA[i].x,
                y: f.teamA[i].y,
                name: f.labelsA[i] || "",
                number: i + 1,
            });
        }
        for (let i = 0; i < f.teamB.length; i++) {
            state.players.push({
                id: 11 + i,
                team: "B",
                x: f.teamB[i].x,
                y: f.teamB[i].y,
                name: f.labelsB[i] || "",
                number: i + 1,
            });
        }
        render();
    }

    // ── Hit test ───────────────────────────────────────────
    function hitTest(px, py) {
        for (let i = state.players.length - 1; i >= 0; i--) {
            const p = state.players[i];
            const { px: cx, py: cy } = fieldToCanvas(p.x, p.y);
            const dist = Math.sqrt((px - cx) ** 2 + (py - cy) ** 2);
            if (dist <= PLAYER_RADIUS + 4) return p;
        }
        return null;
    }

    // ── Pointer events ─────────────────────────────────────
    function getPointerPos(e) {
        const rect = canvas.getBoundingClientRect();
        return {
            px: (e.clientX - rect.left) * (canvas.width / rect.width),
            py: (e.clientY - rect.top) * (canvas.height / rect.height),
        };
    }

    canvas.addEventListener("pointerdown", (e) => {
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
            state.drawingArrow = { sx: fx, sy: fy, ex: fx, ey: fy };
            canvas.setPointerCapture(e.pointerId);
        }
    });

    canvas.addEventListener("pointermove", (e) => {
        const { px, py } = getPointerPos(e);

        if (state.mode === "select" && state.dragging) {
            const adjPx = px + state.dragOffset.dx;
            const adjPy = py + state.dragOffset.dy;
            const { fx, fy } = canvasToField(adjPx, adjPy);
            state.dragging.x = fx;
            state.dragging.y = fy;
            render();
        } else if (state.mode === "draw" && state.drawingArrow) {
            const { fx, fy } = canvasToField(px, py);
            state.drawingArrow.ex = fx;
            state.drawingArrow.ey = fy;
            render();
        } else if (state.mode === "select") {
            // cursor hint
            const player = hitTest(px, py);
            canvas.style.cursor = player ? "grab" : "default";
        }
    });

    canvas.addEventListener("pointerup", (e) => {
        if (state.mode === "select") {
            state.dragging = null;
        } else if (state.mode === "draw" && state.drawingArrow) {
            const a = state.drawingArrow;
            const dist = Math.sqrt((a.ex - a.sx) ** 2 + (a.ey - a.sy) ** 2);
            if (dist > 0.01) {
                state.arrows.push({ sx: a.sx, sy: a.sy, ex: a.ex, ey: a.ey });
            }
            state.drawingArrow = null;
            render();
        }
    });

    // ── Toolbar wiring ─────────────────────────────────────
    const btnSelect = document.getElementById("btn-select");
    const btnDraw = document.getElementById("btn-draw");
    const btnClear = document.getElementById("btn-clear-arrows");
    const btnReset = document.getElementById("btn-reset");
    const formationSelect = document.getElementById("formation-select");

    function setMode(mode) {
        state.mode = mode;
        btnSelect.classList.toggle("active", mode === "select");
        btnDraw.classList.toggle("active", mode === "draw");
        canvas.style.cursor = mode === "draw" ? "crosshair" : "default";
    }

    btnSelect.addEventListener("click", () => setMode("select"));
    btnDraw.addEventListener("click", () => setMode("draw"));

    btnClear.addEventListener("click", () => {
        state.arrows = [];
        render();
    });

    btnReset.addEventListener("click", () => {
        state.arrows = [];
        loadFormation(state.currentFormation);
    });

    formationSelect.addEventListener("change", (e) => {
        state.arrows = [];
        loadFormation(e.target.value);
    });

    // ── Init ───────────────────────────────────────────────
    window.addEventListener("resize", resize);

    fetch("/api/formations")
        .then((r) => r.json())
        .then((data) => {
            state.formations = data;
            resize();
            loadFormation("4-4-2");
        });
})();
