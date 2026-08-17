已创建可运行的弓箭射击竞速游戏（纯前端 + 无依赖单元测试）。文件布局：

```
archery-game/
├── index.html
├── package.json
├── src/core.js          # 纯逻辑：弹道、命中判定、计时格式化、排行榜
├── src/game.js          # 渲染与交互
└── test/core.test.mjs   # node:test 单元测试
```

### src/core.js

```js
// 纯逻辑模块：不依赖 DOM，可直接被 Node 测试
export const GRAVITY = 900;          // px/s^2
export const MAX_POWER = 1250;       // px/s
export const MIN_POWER_RATIO = 0.28; // 最小蓄力比例
export const CHARGE_TIME = 0.85;     // 秒，蓄满所需时间

/** 蓄力时长 -> 初速度（超过 CHARGE_TIME 后维持满力） */
export function chargePower(heldSeconds, maxPower = MAX_POWER) {
  const t = Math.max(0, Math.min(1, heldSeconds / CHARGE_TIME));
  return maxPower * (MIN_POWER_RATIO + (1 - MIN_POWER_RATIO) * t);
}

/** 从弓位指向准星的角度（canvas 坐标系，y 向下） */
export function aimAngle(bow, pointer) {
  return Math.atan2(pointer.y - bow.y, pointer.x - bow.x);
}

/** 生成一支箭的初始状态 */
export function launch(origin, angle, power) {
  return {
    x: origin.x,
    y: origin.y,
    vx: Math.cos(angle) * power,
    vy: Math.sin(angle) * power,
  };
}

/** 显式欧拉积分一步（返回新对象，便于做线段碰撞） */
export function integrate(arrow, dt, gravity = GRAVITY) {
  return {
    x: arrow.x + arrow.vx * dt,
    y: arrow.y + arrow.vy * dt,
    vx: arrow.vx,
    vy: arrow.vy + gravity * dt,
  };
}

/** 预测弹道，用于瞄准辅助线，也便于测试 */
export function simulatePath(origin, angle, power, opts = {}) {
  const { steps = 90, dt = 1 / 60, groundY = Infinity, gravity = GRAVITY } = opts;
  let a = launch(origin, angle, power);
  const pts = [{ x: a.x, y: a.y }];
  for (let i = 0; i < steps; i++) {
    a = integrate(a, dt, gravity);
    pts.push({ x: a.x, y: a.y });
    if (a.y >= groundY) break;
  }
  return pts;
}

/** 点到线段的最短距离：避免高速箭矢“穿透”靶子 */
export function segmentPointDistance(ax, ay, bx, by, px, py) {
  const dx = bx - ax;
  const dy = by - ay;
  const len2 = dx * dx + dy * dy;
  let t = len2 === 0 ? 0 : ((px - ax) * dx + (py - ay) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  const cx = ax + t * dx;
  const cy = ay + t * dy;
  return Math.hypot(px - cx, py - cy);
}

export function segmentCircleHit(a, b, center, radius) {
  return segmentPointDistance(a.x, a.y, b.x, b.y, center.x, center.y) <= radius;
}

/** 靶心随时间做确定性往复运动：所有玩家条件一致，排行榜可比 */
export function targetCenter(target, t) {
  if (!target.amp) return { x: target.x, y: target.y };
  const off = Math.sin((2 * Math.PI * t) / target.period) * target.amp;
  return target.axis === 'x'
    ? { x: target.x + off, y: target.y }
    : { x: target.x, y: target.y + off };
}

/** 环数（仅作展示，排名只看时间） */
export function ringScore(distance, radius) {
  const r = distance / radius;
  if (r <= 0.2) return 10;
  if (r <= 0.45) return 8;
  if (r <= 0.7) return 5;
  if (r <= 1) return 2;
  return 0;
}

export function formatTime(ms) {
  if (!Number.isFinite(ms) || ms < 0) return '--';
  const total = ms / 1000;
  const m = Math.floor(total / 60);
  const s = total - m * 60;
  return m > 0
    ? `${m}:${s.toFixed(2).padStart(5, '0')}`
    : `${s.toFixed(2)}s`;
}

/** 插入成绩：按用时升序，同分先到先得，截断到 limit */
export function insertScore(board, entry, limit = 10) {
  const next = [...board, entry].sort(
    (a, b) => a.time - b.time || (a.ts ?? 0) - (b.ts ?? 0)
  );
  return next.slice(0, limit);
}

/** 该用时在榜单中的名次（1 起） */
export function rank(board, time) {
  return board.filter((e) => e.time < time).length + 1;
}
```

### src/game.js

```js
import {
  MAX_POWER, CHARGE_TIME, GRAVITY,
  chargePower, aimAngle, launch, integrate, simulatePath,
  segmentPointDistance, segmentCircleHit, targetCenter, ringScore,
  formatTime, insertScore, rank,
} from './core.js';

const STORAGE_KEY = 'archery.leaderboard.v1';
const MAX_FLYING = 3;      // 同时在空中的箭数上限
const MAX_DEBRIS = 14;     // 保留的落地/命中箭矢数量

const canvas = document.getElementById('stage');
const ctx = canvas.getContext('2d');
const W = canvas.width;
const H = canvas.height;
const GROUND_Y = 470;
const BOW = { x: 120, y: 392 };

const TARGET_DEFS = [
  { x: 520, y: 372, r: 44, amp: 0,  axis: 'y', period: 1 },
  { x: 668, y: 250, r: 38, amp: 62, axis: 'y', period: 3.2 },
  { x: 792, y: 402, r: 32, amp: 0,  axis: 'y', period: 1 },
  { x: 872, y: 176, r: 28, amp: 46, axis: 'x', period: 2.6 },
];

const el = {
  time: document.getElementById('hud-time'),
  shots: document.getElementById('hud-shots'),
  hits: document.getElementById('hud-hits'),
  score: document.getElementById('hud-score'),
  power: document.getElementById('power-fill'),
  board: document.getElementById('board'),
  result: document.getElementById('result'),
  resultText: document.getElementById('result-text'),
  name: document.getElementById('player-name'),
  save: document.getElementById('save-score'),
  restart: document.getElementById('restart'),
  live: document.getElementById('live'),
};

let board = loadBoard();
let state;
let lastFrame = 0;

function loadBoard() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveBoard(next) {
  board = next;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* 隐私模式下忽略写入失败 */
  }
  renderBoard();
}

function renderBoard() {
  el.board.innerHTML = '';
  if (board.length === 0) {
    const li = document.createElement('li');
    li.className = 'empty';
    li.textContent = '暂无成绩，快来创造纪录！';
    el.board.append(li);
    return;
  }
  board.forEach((entry, i) => {
    const li = document.createElement('li');
    li.innerHTML =
      `<span class="pos">${i + 1}</span>` +
      `<span class="who"></span>` +
      `<span class="t">${formatTime(entry.time)}</span>` +
      `<span class="sc">${entry.score ?? 0} 环</span>`;
    li.querySelector('.who').textContent = entry.name; // 防止 XSS
    el.board.append(li);
  });
}

function reset() {
  state = {
    phase: 'ready',           // ready | running | done
    elapsed: 0,               // 毫秒
    shots: 0,
    score: 0,
    arrows: [],
    targets: TARGET_DEFS.map((d, i) => ({ ...d, index: i, hit: false, ring: 0 })),
    aim: { angle: -0.45, pointer: null },
    holding: false,
    holdStart: 0,
    finalTime: null,
  };
  el.result.hidden = true;
  el.save.disabled = false;
  announce('准备就绪：按住鼠标或空格蓄力，松开发射。');
  updateHud();
}

function announce(msg) {
  el.live.textContent = msg;
}

function updateHud() {
  el.time.textContent = state.phase === 'ready' ? '0.00s' : formatTime(state.elapsed);
  el.shots.textContent = String(state.shots);
  el.hits.textContent = `${state.targets.filter((t) => t.hit).length}/4`;
  el.score.textContent = `${state.score} 环`;
}

/* ---------- 输入 ---------- */

function pointerPos(evt) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: ((evt.clientX - rect.left) / rect.width) * W,
    y: ((evt.clientY - rect.top) / rect.height) * H,
  };
}

function startHold() {
  if (state.phase === 'done' || state.holding) return;
  if (state.arrows.filter((a) => !a.stuck).length >= MAX_FLYING) return;
  state.holding = true;
  state.holdStart = performance.now();
}

function releaseHold() {
  if (!state.holding) return;
  const held = (performance.now() - state.holdStart) / 1000;
  state.holding = false;
  shoot(chargePower(held));
}

function shoot(power) {
  if (state.phase === 'ready') {
    state.phase = 'running';
    state.elapsed = 0;
  }
  if (state.phase !== 'running') return;
  const a = launch(BOW, state.aim.angle, power);
  state.arrows.push({ ...a, stuck: false, host: -1, ox: 0, oy: 0, angle: state.aim.angle });
  state.shots += 1;
  updateHud();
}

canvas.addEventListener('pointerdown', (e) => {
  e.preventDefault();
  canvas.focus();
  state.aim.pointer = pointerPos(e);
  state.aim.angle = aimAngle(BOW, state.aim.pointer);
  startHold();
});
canvas.addEventListener('pointermove', (e) => {
  state.aim.pointer = pointerPos(e);
  state.aim.angle = aimAngle(BOW, state.aim.pointer);
});
window.addEventListener('pointerup', releaseHold);
canvas.addEventListener('pointerleave', releaseHold);

const keys = new Set();
canvas.addEventListener('keydown', (e) => {
  if (e.key === ' ' || e.key === 'Enter') {
    e.preventDefault();
    startHold();
    return;
  }
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
    e.preventDefault();
    keys.add(e.key);
  }
  if (e.key.toLowerCase() === 'r') reset();
});
canvas.addEventListener('keyup', (e) => {
  if (e.key === ' ' || e.key === 'Enter') releaseHold();
  keys.delete(e.key);
});

el.restart.addEventListener('click', () => {
  reset();
  canvas.focus();
});

el.save.addEventListener('click', () => {
  if (state.finalTime == null) return;
  const name = (el.name.value || '匿名弓手').trim().slice(0, 16);
  const entry = { name, time: state.finalTime, score: state.score, ts: Date.now() };
  saveBoard(insertScore(board, entry, 10));
  el.save.disabled = true;
  announce(`成绩已保存，第 ${rank(board, state.finalTime)} 名。`);
});

/* ---------- 更新 ---------- */

function step(dt) {
  // 键盘微调瞄准
  const rate = 1.1 * dt;
  if (keys.has('ArrowUp')) state.aim.angle -= rate;
  if (keys.has('ArrowDown')) state.aim.angle += rate;
  if (keys.has('ArrowLeft')) state.aim.angle -= rate * 0.4;
  if (keys.has('ArrowRight')) state.aim.angle += rate * 0.4;
  state.aim.angle = Math.max(-Math.PI / 2, Math.min(Math.PI / 3, state.aim.angle));

  if (state.phase === 'running') state.elapsed += dt * 1000;
  const t = state.elapsed / 1000;

  const sub = 1 / 240;
  let remain = dt;
  while (remain > 0) {
    const h = Math.min(sub, remain);
    remain -= h;
    for (const arrow of state.arrows) {
      if (arrow.stuck) continue;
      const prev = { x: arrow.x, y: arrow.y };
      const next = integrate(arrow, h);
      arrow.angle = Math.atan2(next.vy, next.vx);

      let landed = false;
      for (const target of state.targets) {
        if (target.hit) continue;
        const c = targetCenter(target, t);
        if (segmentCircleHit(prev, next, c, target.r)) {
          const d = segmentPointDistance(prev.x, prev.y, next.x, next.y, c.x, c.y);
          target.hit = true;
          target.ring = ringScore(d, target.r);
          state.score += target.ring;
          arrow.stuck = true;
          arrow.host = target.index;
          arrow.ox = next.x - c.x;
          arrow.oy = next.y - c.y;
          arrow.x = next.x;
          arrow.y = next.y;
          landed = true;
          announce(`命中第 ${target.index + 1} 个靶子，${target.ring} 环。`);
          break;
        }
      }
      if (landed) continue;

      if (next.y >= GROUND_Y) {
        arrow.stuck = true;
        arrow.x = next.x;
        arrow.y = GROUND_Y;
      } else {
        Object.assign(arrow, next);
      }
    }
  }

  // 清理越界与过多残留
  state.arrows = state.arrows.filter(
    (a) => a.stuck || (a.x < W + 120 && a.y < H + 200)
  );
  const debris = state.arrows.filter((a) => a.stuck);
  if (debris.length > MAX_DEBRIS) {
    const drop = new Set(debris.slice(0, debris.length - MAX_DEBRIS));
    state.arrows = state.arrows.filter((a) => !drop.has(a));
  }

  if (state.phase === 'running' && state.targets.every((tg) => tg.hit)) {
    state.phase = 'done';
    state.finalTime = state.elapsed;
    const place = rank(board, state.finalTime);
    el.resultText.textContent =
      `全部命中！用时 ${formatTime(state.finalTime)}，${state.shots} 箭，${state.score} 环。` +
      `当前可排第 ${place} 名。`;
    el.result.hidden = false;
    el.name.focus();
    announce(`完成！用时 ${formatTime(state.finalTime)}。`);
  }
  updateHud();
}

/* ---------- 渲染 ---------- */

function draw() {
  const t = state.elapsed / 1000;

  const sky = ctx.createLinearGradient(0, 0, 0, GROUND_Y);
  sky.addColorStop(0, '#12213a');
  sky.addColorStop(1, '#2b4a6b');
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, W, GROUND_Y);

  ctx.fillStyle = '#1d3524';
  ctx.fillRect(0, GROUND_Y, W, H - GROUND_Y);
  ctx.strokeStyle = '#2f5c3a';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(0, GROUND_Y);
  ctx.lineTo(W, GROUND_Y);
  ctx.stroke();

  // 距离刻度
  ctx.fillStyle = 'rgba(255,255,255,.25)';
  ctx.font = '12px system-ui, sans-serif';
  for (let x = 200; x < W; x += 200) {
    ctx.fillRect(x, GROUND_Y, 1, 10);
    ctx.fillText(`${x - BOW.x}px`, x + 4, GROUND_Y + 20);
  }

  state.targets.forEach((target, i) => drawTarget(target, t, i));

  // 瞄准辅助线
  if (state.holding && state.phase !== 'done') {
    const held = (performance.now() - state.holdStart) / 1000;
    const power = chargePower(held);
    const path = simulatePath(BOW, state.aim.angle, power, {
      steps: 70, dt: 1 / 60, groundY: GROUND_Y,
    });
    ctx.fillStyle = 'rgba(255,225,140,.55)';
    path.forEach((p, i) => {
      if (i % 4) return;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2.2, 0, Math.PI * 2);
      ctx.fill();
    });
    el.power.style.width = `${(power / MAX_POWER) * 100}%`;
  } else {
    el.power.style.width = '0%';
  }

  drawArcher();
  state.arrows.forEach((a) => drawArrow(a, t));
}

function drawTarget(target, t, i) {
  const c = targetCenter(target, t);
  ctx.save();
  ctx.translate(c.x, c.y);
  // 支架
  ctx.strokeStyle = '#6b4a2a';
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(0, target.r);
  ctx.lineTo(0, GROUND_Y - c.y);
  ctx.stroke();

  const rings = [
    [1, '#f4f4f4'], [0.7, '#1b2a3a'], [0.45, '#2f7fd0'], [0.2, '#e2483c'],
  ];
  rings.forEach(([k, color]) => {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(0, 0, target.r * k, 0, Math.PI * 2);
    ctx.fill();
  });

  if (target.hit) {
    ctx.strokeStyle = '#7dffa0';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.arc(0, 0, target.r + 7, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.fillStyle = 'rgba(255,255,255,.85)';
  ctx.font = 'bold 13px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(String(i + 1), 0, -target.r - 12);
  ctx.restore();
}

function drawArcher() {
  ctx.save();
  ctx.strokeStyle = '#e8e8e8';
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(BOW.x - 10, GROUND_Y);
  ctx.lineTo(BOW.x - 10, BOW.y - 6);      // 身体
  ctx.moveTo(BOW.x - 10, GROUND_Y);
  ctx.lineTo(BOW.x - 26, GROUND_Y);       // 腿
  ctx.stroke();
  ctx.fillStyle = '#e8e8e8';
  ctx.beginPath();
  ctx.arc(BOW.x - 10, BOW.y - 16, 9, 0, Math.PI * 2);
  ctx.fill();

  // 弓随瞄准方向旋转
  ctx.translate(BOW.x, BOW.y);
  ctx.rotate(state.aim.angle);
  ctx.strokeStyle = '#d9a04a';
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(0, 0, 26, -Math.PI / 2.2, Math.PI / 2.2);
  ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,.7)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(26 * Math.cos(-Math.PI / 2.2), 26 * Math.sin(-Math.PI / 2.2));
  ctx.lineTo(state.holding ? -12 : -2, 0);
  ctx.lineTo(26 * Math.cos(Math.PI / 2.2), 26 * Math.sin(Math.PI / 2.2));
  ctx.stroke();
  ctx.restore();
}

function drawArrow(a, t) {
  let x = a.x;
  let y = a.y;
  if (a.stuck && a.host >= 0) {
    const c = targetCenter(state.targets[a.host], t);
    x = c.x + a.ox;
    y = c.y + a.oy;
  }
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(a.angle);
  ctx.strokeStyle = '#f0e6d2';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(-30, 0);
  ctx.lineTo(0, 0);
  ctx.stroke();
  ctx.fillStyle = '#ffd166';
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(-8, -4);
  ctx.lineTo(-8, 4);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = '#8ecae6';
  ctx.beginPath();
  ctx.moveTo(-30, 0);
  ctx.lineTo(-38, -4);
  ctx.moveTo(-30, 0);
  ctx.lineTo(-38, 4);
  ctx.stroke();
  ctx.restore();
}

function frame(now) {
  const dt = Math.min(0.05, lastFrame ? (now - lastFrame) / 1000 : 0);
  lastFrame = now;
  step(dt);
  draw();
  requestAnimationFrame(frame);
}

reset();
renderBoard();
requestAnimationFrame(frame);
```

### index.html

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>弓箭射击竞速 · Archery Time Trial</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px; min-height: 100vh;
    background: #0b1220; color: #e9eef6;
    font-family: system-ui, "Noto Sans SC", sans-serif;
    display: flex; justify-content: center;
  }
  .wrap { width: min(1360px, 100%); display: grid; gap: 18px; grid-template-columns: minmax(0,1fr) 320px; }
  h1 { margin: 0 0 6px; font-size: 20px; }
  p.sub { margin: 0 0 14px; color: #93a4bd; font-size: 14px; }
  canvas { width: 100%; aspect-ratio: 960 / 540; background: #101a2c; border-radius: 12px; display: block; touch-action: none; }
  canvas:focus-visible { outline: 3px solid #ffd166; outline-offset: 3px; }
  .hud { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
  .chip { background: #16233c; border: 1px solid #24365a; border-radius: 999px; padding: 6px 14px; font-size: 14px; }
  .chip b { color: #ffd166; font-variant-numeric: tabular-nums; }
  .power { height: 10px; background: #16233c; border: 1px solid #24365a; border-radius: 999px; overflow: hidden; }
  .power i { display: block; height: 100%; width: 0; background: linear-gradient(90deg,#7dffa0,#ffd166,#ff6b6b); transition: width .05s linear; }
  aside { background: #101a2c; border: 1px solid #1f2f4d; border-radius: 12px; padding: 16px; }
  aside h2 { font-size: 16px; margin: 0 0 10px; }
  ol#board { list-style: none; margin: 0 0 16px; padding: 0; display: grid; gap: 6px; }
  #board li { display: grid; grid-template-columns: 26px 1fr auto auto; gap: 8px; align-items: center;
    background: #16233c; border-radius: 8px; padding: 7px 10px; font-size: 14px; }
  #board li.empty { display: block; color: #93a4bd; background: none; padding: 0; }
  #board .pos { color: #ffd166; font-weight: 700; }
  #board .t { font-variant-numeric: tabular-nums; }
  #board .sc { color: #93a4bd; font-size: 12px; }
  #result { background: #16233c; border: 1px solid #2f7fd0; border-radius: 10px; padding: 12px; margin-bottom: 14px; }
  label { display: block; font-size: 13px; margin: 10px 0 4px; color: #93a4bd; }
  input, button { font: inherit; border-radius: 8px; }
  input { width: 100%; padding: 8px 10px; background: #0b1220; border: 1px solid #24365a; color: inherit; }
  button { padding: 9px 14px; margin-top: 10px; border: 0; background: #2f7fd0; color: #fff; cursor: pointer; width: 100%; }
  button:hover:not(:disabled) { background: #3d92e6; }
  button:disabled { opacity: .5; cursor: default; }
  #restart { background: #24365a; }
  .keys { font-size: 13px; color: #93a4bd; line-height: 1.7; margin-top: 14px; }
  kbd { background: #16233c; border: 1px solid #24365a; border-radius: 4px; padding: 1px 6px; font-size: 12px; }
  .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  @media (max-width: 900px) { .wrap { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="wrap">
  <main>
    <h1>弓箭射击竞速</h1>
    <p class="sub">击中全部 4 个靶子，用时越短排名越高。计时从第一箭射出开始。</p>
    <canvas id="stage" width="960" height="540" tabindex="0"
      aria-label="弓箭射击场地：左侧为弓手，右侧有四个靶子。使用方向键瞄准，空格键蓄力发射。"></canvas>
    <div class="hud">
      <span class="chip">用时 <b id="hud-time">0.00s</b></span>
      <span class="chip">命中 <b id="hud-hits">0/4</b></span>
      <span class="chip">射出 <b id="hud-shots">0</b> 箭</span>
      <span class="chip">环数 <b id="hud-score">0 环</b></span>
    </div>
    <div class="power" aria-hidden="true"><i id="power-fill"></i></div>
  </main>

  <aside>
    <div id="result" hidden>
      <strong>本局成绩</strong>
      <p id="result-text" style="margin:6px 0 0;font-size:14px"></p>
      <label for="player-name">你的名字</label>
      <input id="player-name" maxlength="16" placeholder="匿名弓手" />
      <button id="save-score">保存到排行榜</button>
    </div>

    <h2>排行榜 · 最快 10 名</h2>
    <ol id="board"></ol>
    <button id="restart">重新开始（R）</button>

    <p class="keys">
      <strong>操作</strong><br />
      鼠标：移动瞄准，按住蓄力，松开发射<br />
      键盘：<kbd>↑</kbd><kbd>↓</kbd> 调整角度，<kbd>←</kbd><kbd>→</kbd> 微调，<kbd>空格</kbd> 蓄力发射，<kbd>R</kbd> 重开<br />
      最多同时 3 箭在空中；2 号、4 号靶会按固定节奏移动，对所有玩家一致。
    </p>
  </aside>
</div>
<div id="live" class="sr" role="status" aria-live="polite"></div>
<script type="module" src="./src/game.js"></script>
</body>
</html>
```

### package.json

```json
{
  "name": "archery-time-trial",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test test/",
    "start": "python3 -m http.server 8000"
  }
}
```

### test/core.test.mjs

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  GRAVITY, MAX_POWER, MIN_POWER_RATIO, CHARGE_TIME,
  chargePower, aimAngle, launch, integrate, simulatePath,
  segmentPointDistance, segmentCircleHit, targetCenter, ringScore,
  formatTime, insertScore, rank,
} from '../src/core.js';

test('chargePower 从最小值线性增长并在满力处夹紧', () => {
  assert.equal(chargePower(0), MAX_POWER * MIN_POWER_RATIO);
  assert.equal(chargePower(CHARGE_TIME), MAX_POWER);
  assert.equal(chargePower(99), MAX_POWER);
  assert.ok(chargePower(0.3) < chargePower(0.6));
});

test('aimAngle 使用 canvas 坐标系（y 向下）', () => {
  const bow = { x: 0, y: 0 };
  assert.equal(aimAngle(bow, { x: 10, y: 0 }), 0);
  assert.ok(aimAngle(bow, { x: 10, y: -10 }) < 0, '向上瞄准角度为负');
});

test('launch 分解初速度，integrate 施加重力', () => {
  const a = launch({ x: 0, y: 0 }, 0, 100);
  assert.ok(Math.abs(a.vx - 100) < 1e-9);
  assert.ok(Math.abs(a.vy) < 1e-9);
  const b = integrate(a, 0.5);
  assert.equal(b.x, 50);
  assert.ok(Math.abs(b.vy - GRAVITY * 0.5) < 1e-9);
  assert.equal(a.x, 0, 'integrate 不修改入参');
});

test('simulatePath 在触地处停止且轨迹先升后降', () => {
  const path = simulatePath({ x: 0, y: 100 }, -Math.PI / 4, 600, { groundY: 100, steps: 500 });
  assert.ok(path.length > 2);
  assert.ok(path.at(-1).y >= 100);
  const minY = Math.min(...path.map((p) => p.y));
  assert.ok(minY < 100, '箭矢应先上升');
});

test('线段碰撞可拦截高速穿透', () => {
  const prev = { x: 0, y: 0 };
  const next = { x: 400, y: 0 };   // 单帧跨越整个靶子
  const center = { x: 200, y: 10 };
  assert.equal(segmentCircleHit(prev, next, center, 20), true);
  assert.equal(segmentCircleHit(prev, next, { x: 200, y: 80 }, 20), false);
  assert.equal(segmentPointDistance(0, 0, 400, 0, 200, 30), 30);
});

test('targetCenter 确定性运动且不超过振幅', () => {
  const still = { x: 100, y: 100, amp: 0, axis: 'y', period: 1 };
  assert.deepEqual(targetCenter(still, 7.3), { x: 100, y: 100 });

  const mover = { x: 100, y: 100, amp: 50, axis: 'y', period: 4 };
  assert.deepEqual(targetCenter(mover, 0), { x: 100, y: 100 });
  assert.ok(Math.abs(targetCenter(mover, 1).y - 150) < 1e-9);
  for (let t = 0; t < 10; t += 0.13) {
    assert.ok(Math.abs(targetCenter(mover, t).y - 100) <= 50 + 1e-9);
  }
  assert.deepEqual(targetCenter(mover, 2.5), targetCenter(mover, 6.5), '同相位结果一致');
});

test('ringScore 按命中距离分档', () => {
  assert.equal(ringScore(0, 40), 10);
  assert.equal(ringScore(16, 40), 8);
  assert.equal(ringScore(27, 40), 5);
  assert.equal(ringScore(40, 40), 2);
  assert.equal(ringScore(41, 40), 0);
});

test('formatTime 输出稳定可比较的格式', () => {
  assert.equal(formatTime(1234), '1.23s');
  assert.equal(formatTime(62345), '1:02.35');
  assert.equal(formatTime(NaN), '--');
});

test('insertScore 升序、限长，同分先到先得', () => {
  let board = [];
  board = insertScore(board, { name: 'A', time: 9000, ts: 1 });
  board = insertScore(board, { name: 'B', time: 4000, ts: 2 });
  board = insertScore(board, { name: 'C', time: 4000, ts: 3 });
  assert.deepEqual(board.map((e) => e.name), ['B', 'C', 'A']);

  let big = [];
  for (let i = 0; i < 15; i++) big = insertScore(big, { name: `P${i}`, time: 15000 - i * 100, ts: i }, 10);
  assert.equal(big.length, 10);
  assert.equal(big[0].name, 'P14');
  assert.ok(big.every((e, i, arr) => i === 0 || arr[i - 1].time <= e.time));
});

test('rank 返回名次（1 起）', () => {
  const board = [{ time: 3000 }, { time: 5000 }, { time: 8000 }];
  assert.equal(rank(board, 2000), 1);
  assert.equal(rank(board, 6000), 3);
  assert.equal(rank(board, 9000), 4);
});
```

## 运行方式

ES 模块需要通过 HTTP 提供（`file://` 会被 CORS 阻止）：

```bash
cd archery-game
python3 -m http.server 8000    # 或 npx serve .
# 浏览器打开 http://localhost:8000/
```

服务器仅监听本地、无鉴权，属于本地开发用途；排行榜存于浏览器 `localStorage`，无网络请求、无后端。若要暴露到公网，需要另加访问控制和服务端存储。

## 测试说明

单元测试（无第三方依赖，需 Node 18+）：

```bash
node --test test/        # 或 npm test
```

覆盖蓄力曲线、瞄准角度、重力积分与不可变性、弹道触地终止、高速箭矢的线段碰撞（防穿透）、移动靶的确定性与振幅边界、环数分档、时间格式化、排行榜排序/截断/同分次序、名次计算。

手动验收要点：
1. 按住鼠标出现黄色预测弹道，功率条随蓄力增长；松开发射，计时器从第一箭开始走。
2. 命中靶子后出现绿色高亮、箭矢钉在靶上并随移动靶一起移动，命中数递增。
3. 4 靶全中即停表，右侧出现成绩面板；保存后进入排行榜并按用时升序排列，刷新页面仍保留。
4. 键盘路径：Tab 聚焦画布 → 方向键调角度 → 空格蓄力发射 → R 重开；屏幕阅读器可听到命中与完成播报。
5. 空中最多 3 箭，落地箭矢累积到上限后自动清理，长时间连射不掉帧。

设计取舍：靶子位置固定、移动靶采用与计时同源的正弦函数，所以每位玩家面对完全相同的条件，排行榜时间才可比；环数只作展示，排名只看用时。