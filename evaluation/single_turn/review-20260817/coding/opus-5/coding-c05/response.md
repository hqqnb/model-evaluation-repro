我在 `/` 目录下没有可写的项目位置，也没有你指定的目标路径，所以我把完整可运行的产物按文件给出（我无法在本轮直接落盘）。按下面的路径创建这 6 个文件即可直接运行，逻辑层是纯函数模块并附带可执行的 Node 单元测试。

架构上分三层：`src/timeMath.js` 是无依赖的纯时间/角度计算（可单测），`src/watchModel.js` 用 Three.js 构建表壳、表盘、日期/星期转盘、指针等 3D 几何，`src/main.js` 负责场景、光照、渲染循环与交互面板。第二时区用真实 GMT 机制实现：24 小时刻度圈 + 独立 24h 指针，而不是只叠一段文字。

## watch3d/index.html

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>KIRO 3D GMT 腕表</title>
<style>
  :root {
    --panel-bg: rgba(12, 16, 24, 0.78);
    --panel-border: rgba(255, 255, 255, 0.14);
    --text: #eef2f8;
    --muted: #9aa7bb;
    --accent: #e8b563;
    --gmt: #4fc3f7;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body {
    background: radial-gradient(circle at 50% 30%, #1b2434 0%, #070a10 60%, #04060a 100%);
    color: var(--text);
    font: 14px/1.5 "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
    overflow: hidden;
  }
  #scene { position: fixed; inset: 0; display: block; }
  #panel {
    position: fixed; top: 16px; left: 16px; width: 320px; max-height: calc(100% - 32px);
    overflow: auto; padding: 16px; border-radius: 14px;
    background: var(--panel-bg); border: 1px solid var(--panel-border);
    backdrop-filter: blur(10px); z-index: 10;
  }
  #panel h1 { margin: 0 0 2px; font-size: 15px; letter-spacing: 0.12em; text-transform: uppercase; }
  #panel .sub { margin: 0 0 14px; color: var(--muted); font-size: 12px; }
  fieldset { border: 1px solid var(--panel-border); border-radius: 10px; margin: 0 0 12px; padding: 10px 12px 12px; }
  legend { padding: 0 6px; font-size: 11px; letter-spacing: 0.1em; color: var(--muted); text-transform: uppercase; }
  label { display: block; font-size: 11px; color: var(--muted); margin: 6px 0 3px; }
  select, button {
    width: 100%; padding: 7px 8px; border-radius: 8px; font: inherit; font-size: 13px;
    color: var(--text); background: #131a26; border: 1px solid var(--panel-border);
  }
  button { cursor: pointer; }
  button:hover { border-color: var(--accent); }
  button[aria-pressed="true"] { border-color: var(--accent); color: var(--accent); }
  .row { display: flex; gap: 8px; }
  .row > * { flex: 1 1 0; }
  .clock { font-variant-numeric: tabular-nums; font-size: 26px; letter-spacing: 0.04em; margin-top: 4px; }
  .meta { color: var(--muted); font-size: 12px; }
  .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; vertical-align: 1px; }
  .dot.local { background: var(--accent); }
  .dot.gmt { background: var(--gmt); }
  #hint { position: fixed; bottom: 14px; left: 50%; transform: translateX(-50%); color: var(--muted); font-size: 12px; z-index: 10; text-align: center; }
  @media (max-width: 640px) { #panel { width: calc(100% - 32px); max-height: 46%; } }
</style>
</head>
<body>
<canvas id="scene"></canvas>

<section id="panel">
  <h1>Kiro 3D GMT</h1>
  <p class="sub">实时驱动 · 双时区 · 星期/日期视窗</p>

  <fieldset>
    <legend><span class="dot local"></span>主时区（时/分/秒针）</legend>
    <label for="zoneA">时区</label>
    <select id="zoneA"></select>
    <div class="clock" id="clockA" aria-live="off">--:--:--</div>
    <div class="meta" id="metaA">—</div>
  </fieldset>

  <fieldset>
    <legend><span class="dot gmt"></span>第二时区（24 小时指针）</legend>
    <label for="zoneB">时区</label>
    <select id="zoneB"></select>
    <div class="clock" id="clockB">--:--:--</div>
    <div class="meta" id="metaB">—</div>
    <div class="meta" id="metaDiff" style="margin-top:6px"></div>
  </fieldset>

  <fieldset>
    <legend>显示</legend>
    <div class="row">
      <button id="btnSweep" aria-pressed="true" title="秒针连续扫秒 / 一秒一跳">扫秒</button>
      <button id="btnNight" aria-pressed="false" title="夜光模式">夜光</button>
    </div>
    <div class="row" style="margin-top:8px">
      <button id="btnSpin" aria-pressed="true">自转</button>
      <button id="btnLocale" aria-pressed="false">中文星期</button>
    </div>
    <button id="btnReset" style="margin-top:8px">重置视角</button>
  </fieldset>
</section>

<p id="hint">拖拽旋转 · 滚轮缩放 · 右键平移</p>

<script type="importmap">
{
  "imports": {
    "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
    "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
  }
}
</script>
<script type="module" src="./src/main.js"></script>
</body>
</html>
```

## watch3d/src/timeMath.js

```js
/**
 * 纯计算层：时区解析、指针角度、转盘角度、虚拟时钟。
 * 不依赖 DOM 或 Three.js，可在 Node 中直接单元测试。
 */

export const TAU = Math.PI * 2;

export const WEEKDAY_LABELS = {
  en: ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'],
  zh: ['周日', '周一', '周二', '周三', '周四', '周五', '周六'],
};

const formatterCache = new Map();

function getPartsFormatter(timeZone) {
  let fmt = formatterCache.get(timeZone);
  if (!fmt) {
    fmt = new Intl.DateTimeFormat('en-US', {
      timeZone,
      hourCycle: 'h23',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    formatterCache.set(timeZone, fmt);
  }
  return fmt;
}

export function isValidTimeZone(timeZone) {
  try {
    new Intl.DateTimeFormat('en-US', { timeZone });
    return true;
  } catch {
    return false;
  }
}

export function pad2(n) {
  return String(n).padStart(2, '0');
}

/**
 * 把某个瞬间换算到指定时区，返回日历字段 + 该时刻的真实 UTC 偏移（自动处理夏令时）。
 * @param {Date|number} date
 * @param {string} timeZone IANA 时区名，如 "Asia/Shanghai"
 */
export function getZonedParts(date, timeZone) {
  const ms = typeof date === 'number' ? date : date.getTime();
  const parts = getPartsFormatter(timeZone).formatToParts(new Date(ms));
  const map = {};
  for (const p of parts) {
    if (p.type !== 'literal') map[p.type] = p.value;
  }

  const year = Number(map.year);
  const month = Number(map.month);
  const day = Number(map.day);
  const hour = Number(map.hour) % 24;
  const minute = Number(map.minute);
  const second = Number(map.second);
  const millisecond = ((ms % 1000) + 1000) % 1000;

  // 星期：用该时区的 Y/M/D 反推，避免受本机时区影响
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay();

  const asUTC = Date.UTC(year, month - 1, day, hour, minute, second);
  const offsetMinutes = Math.round((asUTC - (ms - millisecond)) / 60000);

  return { timeZone, year, month, day, hour, minute, second, millisecond, weekday, offsetMinutes };
}

/**
 * 指针角度（弧度，绕 +Z 轴）。0 = 指向 12 点，顺时针为负方向。
 * 时针/分针始终连续走时；秒针可选 sweep(平滑扫秒) / beat8(每秒 8 跳) / tick(每秒一跳)。
 */
export function computeHandAngles(parts, options = {}) {
  const mode = options.mode || 'sweep';
  const continuousSeconds = parts.second + parts.millisecond / 1000;

  let displaySeconds = continuousSeconds;
  if (mode === 'tick') displaySeconds = Math.floor(continuousSeconds);
  else if (mode === 'beat8') displaySeconds = Math.floor(continuousSeconds * 8) / 8;

  const minutes = parts.minute + continuousSeconds / 60;
  const hours12 = (parts.hour % 12) + minutes / 60;
  const hours24 = parts.hour + minutes / 60;

  return {
    second: -(displaySeconds / 60) * TAU,
    minute: -(minutes / 60) * TAU,
    hour: -(hours12 / 12) * TAU,
    hour24: -(hours24 / 24) * TAU,
  };
}

/**
 * 日期/星期转盘的目标转角：让第 index 个字符对齐视窗方向 windowAngle。
 */
export function discRotation(index, count, windowAngle) {
  return windowAngle - (index * TAU) / count;
}

export function shortestAngleDelta(from, to) {
  let d = (to - from) % TAU;
  if (d > Math.PI) d -= TAU;
  if (d < -Math.PI) d += TAU;
  return d;
}

/** 指数阻尼趋近，帧率无关；用于日期盘换日时的快速过渡 */
export function approachAngle(current, target, dt, lambda = 12) {
  const d = shortestAngleDelta(current, target);
  return current + d * (1 - Math.exp(-lambda * dt));
}

export function formatOffset(offsetMinutes) {
  const sign = offsetMinutes < 0 ? '-' : '+';
  const abs = Math.abs(offsetMinutes);
  return `UTC${sign}${pad2(Math.floor(abs / 60))}:${pad2(abs % 60)}`;
}

/** 两个时区的时差，如 "+8:00" / "-4:30" / "0:00" */
export function formatOffsetDelta(offsetMinutesA, offsetMinutesB) {
  const diff = offsetMinutesB - offsetMinutesA;
  const sign = diff < 0 ? '-' : diff > 0 ? '+' : '';
  const abs = Math.abs(diff);
  return `${sign}${Math.floor(abs / 60)}:${pad2(abs % 60)}`;
}

export function formatDigital(parts) {
  return `${pad2(parts.hour)}:${pad2(parts.minute)}:${pad2(parts.second)}`;
}

export function formatDate(parts, locale = 'en') {
  const wd = (WEEKDAY_LABELS[locale] || WEEKDAY_LABELS.en)[parts.weekday];
  return `${parts.year}-${pad2(parts.month)}-${pad2(parts.day)} ${wd}`;
}

/**
 * 虚拟时钟：默认就是真实时间；可用于测试（指定起点/加速倍率）。
 */
export function createVirtualClock(options = {}) {
  const speed = Number.isFinite(options.speed) && options.speed > 0 ? options.speed : 1;
  const monotonic =
    options.monotonic ||
    (() => (typeof performance !== 'undefined' ? performance.now() : Date.now()));
  const hasStart = options.startMs !== undefined && options.startMs !== null;
  const realtime = speed === 1 && !hasStart;
  const startMs = hasStart ? Number(options.startMs) : Date.now();
  const t0 = monotonic();

  return {
    speed,
    isRealtime: realtime,
    nowMs() {
      return realtime ? Date.now() : startMs + (monotonic() - t0) * speed;
    },
    now() {
      return new Date(this.nowMs());
    },
  };
}
```

## watch3d/src/watchModel.js

```js
/**
 * 3D 腕表几何建模：表壳、表圈、镜面、表盘（带星期/日期视窗）、
 * 星期盘 + 日期盘、时/分/秒针 + 24 小时第二时区指针、表冠、表耳、金属链带。
 *
 * 坐标约定：表盘位于 XY 平面、法线朝 +Z；12 点方向为 +Y；手腕轴向为 X。
 */
import * as THREE from 'three';

export const DIAL_R = 1.58;

const Z = {
  backOuter: -0.62,
  caseBottom: -0.36,
  caseTop: 0.4,
  basePlate: 0.2,
  discs: 0.26,
  dial: 0.3,
  dialDepth: 0.04,
  frame: 0.29,
  markers: 0.34,
  gmtHand: 0.375,
  hourHand: 0.405,
  minuteHand: 0.435,
  secondHand: 0.465,
  cap: 0.48,
  crystal: 0.56,
  bezel: 0.46,
};

// 视窗（holes）参数：星期在 12 点（外圈），日期在 3 点（内圈），径向不重叠
const DAY_WINDOW = { cx: 0, cy: 1.18, w: 0.52, h: 0.26, r: 0.05 };
const DATE_WINDOW = { cx: 0.8, cy: 0, w: 0.32, h: 0.26, r: 0.05 };
const DAY_RING = { inner: 1.0, outer: 1.38, textRadius: 1.18 };
const DATE_RING = { inner: 0.6, outer: 0.98, textRadius: 0.8 };

const COLORS = {
  steel: 0xd9dee6,
  steelDark: 0x9aa2ad,
  gold: 0xe8b563,
  dialA: '#16233c',
  dialB: '#050810',
  flangeDay: '#e6e9ef',
  flangeNight: '#1d2a44',
  discFace: '#0b111d',
  discText: '#f2f5fa',
  gmtHand: 0x4fc3f7,
  secondHand: 0xd8443a,
  lume: 0xcfeee0,
  lumeEmissive: 0x7ef2c8,
};

/* ---------------- 工具 ---------------- */

function roundedRect(path, cx, cy, w, h, r) {
  const x = cx - w / 2;
  const y = cy - h / 2;
  path.moveTo(x + r, y);
  path.lineTo(x + w - r, y);
  path.quadraticCurveTo(x + w, y, x + w, y + r);
  path.lineTo(x + w, y + h - r);
  path.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  path.lineTo(x + r, y + h);
  path.quadraticCurveTo(x, y + h, x, y + h - r);
  path.lineTo(x, y + r);
  path.quadraticCurveTo(x, y, x + r, y);
  return path;
}

function shapeFromPoints(points) {
  const shape = new THREE.Shape();
  shape.moveTo(points[0][0], points[0][1]);
  for (let i = 1; i < points.length; i++) shape.lineTo(points[i][0], points[i][1]);
  shape.closePath();
  return shape;
}

function canvasTexture(size) {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return { canvas, ctx, texture };
}

/* ---------------- 表盘贴图 ---------------- */

function drawDialTexture(ctx, size) {
  const half = size / 2;
  const S = half / DIAL_R; // 世界单位 -> 像素
  const X = (x) => half + x * S;
  const Y = (y) => half - y * S;
  const worldAngleToCanvas = (a) => -a;

  ctx.clearRect(0, 0, size, size);

  // 底色 + 渐晕
  const grad = ctx.createRadialGradient(half, half, 0, half, half, half);
  grad.addColorStop(0, COLORS.dialA);
  grad.addColorStop(0.72, '#0c1424');
  grad.addColorStop(1, COLORS.dialB);
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(half, half, half, 0, Math.PI * 2);
  ctx.fill();

  // 放射太阳纹
  ctx.save();
  ctx.translate(half, half);
  for (let i = 0; i < 480; i++) {
    ctx.rotate((Math.PI * 2) / 480);
    ctx.strokeStyle = i % 2 ? 'rgba(255,255,255,0.030)' : 'rgba(0,0,0,0.045)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, -half);
    ctx.stroke();
  }
  ctx.restore();

  // 分钟刻度轨 (r 1.36 ~ 1.43)
  for (let i = 0; i < 60; i++) {
    const a = Math.PI / 2 - (i / 60) * Math.PI * 2;
    const isFive = i % 5 === 0;
    const r0 = isFive ? 1.355 : 1.395;
    const r1 = 1.432;
    ctx.strokeStyle = isFive ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0.45)';
    ctx.lineWidth = isFive ? 7 : 3;
    ctx.beginPath();
    ctx.moveTo(X(Math.cos(a) * r0), Y(Math.sin(a) * r0));
    ctx.lineTo(X(Math.cos(a) * r1), Y(Math.sin(a) * r1));
    ctx.stroke();
  }

  // 24 小时内圈（第二时区刻度）：昼 6-18 亮，夜 18-6 暗
  const bandIn = 1.44;
  const bandOut = 1.57;
  const drawBand = (fromHour, toHour, color) => {
    const a0 = worldAngleToCanvas(Math.PI / 2 - (fromHour / 24) * Math.PI * 2);
    const a1 = worldAngleToCanvas(Math.PI / 2 - (toHour / 24) * Math.PI * 2);
    ctx.beginPath();
    ctx.arc(half, half, bandOut * S, a0, a1, false);
    ctx.arc(half, half, bandIn * S, a1, a0, true);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
  };
  drawBand(6, 18, COLORS.flangeDay);
  drawBand(18, 30, COLORS.flangeNight);

  // 24 小时刻度与数字
  for (let h = 0; h < 24; h++) {
    const a = Math.PI / 2 - (h / 24) * Math.PI * 2;
    const daytime = h >= 6 && h < 18;
    ctx.strokeStyle = daytime ? 'rgba(20,26,38,0.75)' : 'rgba(230,236,245,0.7)';
    ctx.lineWidth = h % 2 === 0 ? 5 : 3;
    ctx.beginPath();
    ctx.moveTo(X(Math.cos(a) * (bandIn + 0.005)), Y(Math.sin(a) * (bandIn + 0.005)));
    ctx.lineTo(X(Math.cos(a) * (bandIn + 0.035)), Y(Math.sin(a) * (bandIn + 0.035)));
    ctx.stroke();

    if (h % 2 !== 0) continue;
    const rt = 1.512;
    ctx.save();
    ctx.translate(X(Math.cos(a) * rt), Y(Math.sin(a) * rt));
    ctx.rotate(-(a - Math.PI / 2));
    ctx.fillStyle = daytime ? '#141a26' : '#e6ecf5';
    ctx.font = '600 52px "Segoe UI", Helvetica, Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(h === 0 ? '24' : String(h), 0, 0);
    ctx.restore();
  }

  // 品牌字样
  ctx.fillStyle = 'rgba(240,244,250,0.94)';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = '700 88px "Segoe UI", Helvetica, Arial, sans-serif';
  ctx.fillText('KIRO', X(0), Y(0.58));
  ctx.fillStyle = COLORS.gold;
  ctx.font = '500 40px "Segoe UI", Helvetica, Arial, sans-serif';
  ctx.fillText('GMT  ·  DUAL TIME', X(0), Y(0.4));
  ctx.fillStyle = 'rgba(200,210,225,0.8)';
  ctx.font = '400 34px "Segoe UI", Helvetica, Arial, sans-serif';
  ctx.fillText('AUTOMATIC', X(0), Y(-0.62));
}

/* ---------------- 转盘贴图（星期 / 日期） ---------------- */

function drawDiscTexture(ctx, size, { labels, outerRadius, textRadius, windowAngle, fontPx }) {
  const half = size / 2;
  const S = half / outerRadius;
  const count = labels.length;

  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = COLORS.discFace;
  ctx.fillRect(0, 0, size, size);

  ctx.fillStyle = COLORS.discText;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `700 ${fontPx}px "Segoe UI", "PingFang SC", "Microsoft YaHei", Helvetica, sans-serif`;

  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2; // 贴图上的角度（世界 CCW）
    const px = half + Math.cos(a) * textRadius * S;
    const py = half - Math.sin(a) * textRadius * S;
    ctx.save();
    ctx.translate(px, py);
    // 转盘转到视窗后字符恰好竖直：贴图内预旋转 (a - windowAngle)
    ctx.rotate(-(a - windowAngle));
    ctx.fillText(labels[i], 0, 0);
    ctx.restore();
  }
}

function makeDisc({ labels, ring, windowAngle, fontPx }) {
  const { canvas, ctx, texture } = canvasTexture(1024);
  drawDiscTexture(ctx, canvas.width, {
    labels,
    outerRadius: ring.outer,
    textRadius: ring.textRadius,
    windowAngle,
    fontPx,
  });
  texture.needsUpdate = true;

  const geo = new THREE.RingGeometry(ring.inner, ring.outer, 160, 1);
  const mat = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.5, metalness: 0.1 });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.z = Z.discs;
  mesh.userData.redraw = (nextLabels) => {
    drawDiscTexture(ctx, canvas.width, {
      labels: nextLabels,
      outerRadius: ring.outer,
      textRadius: ring.textRadius,
      windowAngle,
      fontPx,
    });
    texture.needsUpdate = true;
  };
  return mesh;
}

/* ---------------- 指针 ---------------- */

function extrudeMesh(shape, depth, material) {
  const geo = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false, curveSegments: 24 });
  return new THREE.Mesh(geo, material);
}

function buildHands(materials) {
  const depth = 0.022;

  const hourShape = shapeFromPoints([
    [-0.075, -0.16], [0.075, -0.16], [0.058, 0.6],
    [0.03, 0.86], [-0.03, 0.86], [-0.058, 0.6],
  ]);
  const minuteShape = shapeFromPoints([
    [-0.056, -0.18], [0.056, -0.18], [0.044, 1.06],
    [0.022, 1.32], [-0.022, 1.32], [-0.044, 1.06],
  ]);
  const gmtShape = shapeFromPoints([
    [-0.032, -0.3], [0.032, -0.3], [0.032, 1.14], [0.1, 1.14],
    [0, 1.44], [-0.1, 1.14], [-0.032, 1.14],
  ]);

  const hour = new THREE.Group();
  hour.position.z = Z.hourHand;
  hour.add(extrudeMesh(hourShape, depth, materials.handSteel));
  const hourLume = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.44, 0.012), materials.lume);
  hourLume.position.set(0, 0.52, depth + 0.006);
  hour.add(hourLume);

  const minute = new THREE.Group();
  minute.position.z = Z.minuteHand;
  minute.add(extrudeMesh(minuteShape, depth, materials.handSteel));
  const minuteLume = new THREE.Mesh(new THREE.BoxGeometry(0.052, 0.78, 0.012), materials.lume);
  minuteLume.position.set(0, 0.74, depth + 0.006);
  minute.add(minuteLume);

  const gmt = new THREE.Group();
  gmt.position.z = Z.gmtHand;
  gmt.add(extrudeMesh(gmtShape, depth, materials.gmt));

  const second = new THREE.Group();
  second.position.z = Z.secondHand;
  const shaft = new THREE.Mesh(new THREE.BoxGeometry(0.022, 1.74, 0.016), materials.second);
  shaft.position.set(0, (1.42 - 0.32) / 2, 0.008);
  second.add(shaft);
  const counterweight = new THREE.Mesh(
    new THREE.CylinderGeometry(0.085, 0.085, 0.018, 28),
    materials.second,
  );
  counterweight.rotation.x = Math.PI / 2;
  counterweight.position.set(0, -0.24, 0.008);
  second.add(counterweight);

  return { hour, minute, second, gmt };
}

/* ---------------- 主构建 ---------------- */

export function buildWatch({ weekdayLabels } = {}) {
  const group = new THREE.Group();

  const materials = {
    steel: new THREE.MeshStandardMaterial({ color: COLORS.steel, metalness: 1, roughness: 0.22 }),
    steelBrushed: new THREE.MeshStandardMaterial({
      color: COLORS.steelDark, metalness: 1, roughness: 0.42,
    }),
    gold: new THREE.MeshStandardMaterial({ color: COLORS.gold, metalness: 1, roughness: 0.18 }),
    handSteel: new THREE.MeshStandardMaterial({ color: 0xf2f4f8, metalness: 1, roughness: 0.15 }),
    gmt: new THREE.MeshStandardMaterial({ color: COLORS.gmtHand, metalness: 0.55, roughness: 0.3 }),
    second: new THREE.MeshStandardMaterial({ color: COLORS.secondHand, metalness: 0.4, roughness: 0.35 }),
    lume: new THREE.MeshStandardMaterial({
      color: COLORS.lume, emissive: COLORS.lumeEmissive, emissiveIntensity: 0.18, roughness: 0.6,
    }),
    movement: new THREE.MeshStandardMaterial({ color: 0x090d15, metalness: 0.3, roughness: 0.8 }),
    crystal: new THREE.MeshPhysicalMaterial({
      color: 0xffffff, metalness: 0, roughness: 0.03, transparent: true, opacity: 0.35,
      transmission: 0.95, ior: 1.52, thickness: 0.22, clearcoat: 1, clearcoatRoughness: 0.02,
      side: THREE.DoubleSide,
    }),
  };
  const lumeMaterials = [materials.lume];

  /* 表壳侧壁 */
  const caseSide = new THREE.Mesh(
    new THREE.CylinderGeometry(2.0, 1.9, Z.caseTop - Z.caseBottom, 128, 1, true),
    materials.steelBrushed,
  );
  caseSide.rotation.x = Math.PI / 2;
  caseSide.position.z = (Z.caseTop + Z.caseBottom) / 2;
  caseSide.castShadow = true;
  caseSide.receiveShadow = true;
  group.add(caseSide);

  /* 背面圆拱（球冠压扁，法线正确） */
  const back = new THREE.Mesh(
    new THREE.SphereGeometry(1.9, 96, 32, 0, Math.PI * 2, 0, Math.PI / 2),
    materials.steelBrushed,
  );
  back.rotation.x = -Math.PI / 2; // 极点朝 -Z
  back.scale.z = 1;
  back.scale.set(1, 1, 1);
  back.position.z = Z.caseBottom;
  back.geometry.scale(1, 0.14, 1); // 压扁成表背弧度
  back.castShadow = true;
  group.add(back);

  /* 表圈 */
  const bezel = new THREE.Mesh(new THREE.TorusGeometry(1.78, 0.16, 32, 160), materials.steel);
  bezel.position.z = Z.bezel;
  bezel.castShadow = true;
  group.add(bezel);

  /* 机芯底板 */
  const basePlate = new THREE.Mesh(new THREE.CircleGeometry(1.62, 96), materials.movement);
  basePlate.position.z = Z.basePlate;
  group.add(basePlate);

  /* 星期盘 / 日期盘 */
  const dayLabels = weekdayLabels || ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  const dayDisc = makeDisc({
    labels: dayLabels, ring: DAY_RING, windowAngle: Math.PI / 2, fontPx: 116,
  });
  const dateLabels = Array.from({ length: 31 }, (_, i) => String(i + 1));
  const dateDisc = makeDisc({
    labels: dateLabels, ring: DATE_RING, windowAngle: 0, fontPx: 150,
  });
  group.add(dayDisc, dateDisc);

  /* 表盘（带两个视窗镂空） */
  const dialShape = new THREE.Shape();
  dialShape.absarc(0, 0, DIAL_R, 0, Math.PI * 2, false);
  dialShape.holes.push(
    roundedRect(new THREE.Path(), DAY_WINDOW.cx, DAY_WINDOW.cy, DAY_WINDOW.w, DAY_WINDOW.h, DAY_WINDOW.r),
  );
  dialShape.holes.push(
    roundedRect(new THREE.Path(), DATE_WINDOW.cx, DATE_WINDOW.cy, DATE_WINDOW.w, DATE_WINDOW.h, DATE_WINDOW.r),
  );

  const dialTex = canvasTexture(2048);
  drawDialTexture(dialTex.ctx, dialTex.canvas.width);
  dialTex.texture.needsUpdate = true;
  // ExtrudeGeometry 的顶面 UV = 顶点 (x, y)，用 repeat/offset 归一化到 0..1
  dialTex.texture.repeat.set(1 / (2 * DIAL_R), 1 / (2 * DIAL_R));
  dialTex.texture.offset.set(0.5, 0.5);

  const dial = new THREE.Mesh(
    new THREE.ExtrudeGeometry(dialShape, {
      depth: Z.dialDepth, bevelEnabled: false, curveSegments: 96,
    }),
    new THREE.MeshStandardMaterial({ map: dialTex.texture, roughness: 0.42, metalness: 0.18 }),
  );
  dial.position.z = Z.dial;
  group.add(dial);

  /* 视窗金属框 */
  for (const win of [DAY_WINDOW, DATE_WINDOW]) {
    const frameShape = roundedRect(
      new THREE.Shape(), win.cx, win.cy, win.w + 0.07, win.h + 0.07, win.r + 0.02,
    );
    frameShape.holes.push(roundedRect(new THREE.Path(), win.cx, win.cy, win.w, win.h, win.r));
    const frame = extrudeMesh(frameShape, 0.075, materials.gold);
    frame.position.z = Z.frame;
    group.add(frame);
  }

  /* 立体时标（12 点被星期窗占用，故省略） */
  for (let i = 1; i < 12; i++) {
    const holder = new THREE.Group();
    holder.rotation.z = -(i / 12) * Math.PI * 2;
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.24, 0.036), materials.gold);
    body.position.set(0, 1.22, Z.markers + 0.018);
    const lume = new THREE.Mesh(new THREE.BoxGeometry(0.062, 0.2, 0.014), materials.lume);
    lume.position.set(0, 1.22, Z.markers + 0.04);
    holder.add(body, lume);
    group.add(holder);
  }

  /* 指针 + 中心帽 */
  const hands = buildHands(materials);
  group.add(hands.gmt, hands.hour, hands.minute, hands.second);

  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.095, 0.05, 36), materials.gold);
  cap.rotation.x = Math.PI / 2;
  cap.position.z = Z.cap;
  group.add(cap);

  /* 镜面 */
  const crystal = new THREE.Mesh(
    new THREE.CylinderGeometry(1.68, 1.68, 0.08, 128),
    materials.crystal,
  );
  crystal.rotation.x = Math.PI / 2;
  crystal.position.z = Z.crystal;
  group.add(crystal);

  /* 表冠（3 点位置） */
  const crown = new THREE.Group();
  const crownBody = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.2, 20), materials.steel);
  crownBody.rotation.z = Math.PI / 2;
  const crownRing = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.025, 12, 24), materials.gold);
  crownRing.rotation.y = Math.PI / 2;
  crown.add(crownBody, crownRing);
  crown.position.set(2.03, 0, 0.02);
  crown.castShadow = true;
  group.add(crown);

  /* 表耳 */
  for (const sy of [1, -1]) {
    for (const sx of [1, -1]) {
      const lug = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.62, 0.4), materials.steelBrushed);
      lug.position.set(sx * 0.62, sy * 1.84, -0.04);
      lug.rotation.z = -sx * sy * 0.3;
      lug.rotation.x = sy * 0.3;
      lug.castShadow = true;
      group.add(lug);
    }
  }

  /* 链带：以 (0,0,-1.35) 为圆心、半径 1.72 的环，跳过表壳所在顶部弧段 */
  const braceletCenter = new THREE.Vector3(0, 0, -1.35);
  const braceletRadius = 1.72;
  const startDeg = 142;
  const endDeg = 398;
  const linkCount = 26;
  for (let i = 0; i < linkCount; i++) {
    const t = THREE.MathUtils.degToRad(startDeg + ((endDeg - startDeg) * i) / (linkCount - 1));
    const link = new THREE.Group();
    const isClasp = i > linkCount * 0.42 && i < linkCount * 0.58;
    const outer = new THREE.Mesh(
      new THREE.BoxGeometry(0.98, isClasp ? 0.19 : 0.14, 0.26),
      materials.steelBrushed,
    );
    const center = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.17, 0.235), materials.steel);
    center.position.y = 0.02;
    link.add(outer, center);
    link.position.set(
      0,
      braceletCenter.y + Math.cos(t) * braceletRadius,
      braceletCenter.z + Math.sin(t) * braceletRadius,
    );
    link.rotation.x = t; // 局部 +Y -> 径向, +Z -> 切向
    outer.castShadow = true;
    center.castShadow = true;
    group.add(link);
  }

  return {
    group,
    hands,
    discs: { day: dayDisc, date: dateDisc },
    materials,
    lumeMaterials,
    setWeekdayLabels(labels) {
      dayDisc.userData.redraw(labels);
    },
    setNight(on) {
      for (const m of lumeMaterials) m.emissiveIntensity = on ? 2.6 : 0.18;
    },
  };
}
```

## watch3d/src/main.js

```js
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { buildWatch } from './watchModel.js';
import {
  WEEKDAY_LABELS, approachAngle, computeHandAngles, createVirtualClock, discRotation,
  formatDate, formatDigital, formatOffset, formatOffsetDelta, getZonedParts, isValidTimeZone,
} from './timeMath.js';

/* ---------- 启动参数（便于测试）: ?speed=600&start=2026-08-17T23:59:30Z ---------- */
const params = new URLSearchParams(location.search);
const startParam = params.get('start');
const clock = createVirtualClock({
  speed: Number(params.get('speed')) || 1,
  startMs: startParam ? Date.parse(startParam) : undefined,
});

const localZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
const state = {
  zoneA: localStorage.getItem('watch3d.zoneA') || localZone,
  zoneB: localStorage.getItem('watch3d.zoneB') || 'UTC',
  mode: localStorage.getItem('watch3d.mode') || 'sweep',
  locale: localStorage.getItem('watch3d.locale') || 'en',
  night: false,
  spin: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
};
if (!isValidTimeZone(state.zoneA)) state.zoneA = 'UTC';
if (!isValidTimeZone(state.zoneB)) state.zoneB = 'UTC';

/* ---------- 渲染器 / 场景 ---------- */
const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 100);
camera.up.set(0, 0, 1); // 场景的“上”是 +Z（表盘朝上）
const CAMERA_HOME = new THREE.Vector3(1.1, -6.2, 5.4);
camera.position.copy(CAMERA_HOME);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0.1);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 4;
controls.maxDistance = 22;
controls.autoRotate = state.spin;
controls.autoRotateSpeed = 0.55;
controls.update();

/* ---------- 环境贴图（用 canvas 生成等距柱状全景，无额外依赖） ---------- */
function buildEnvironment() {
  const cv = document.createElement('canvas');
  cv.width = 1024;
  cv.height = 512;
  const ctx = cv.getContext('2d');
  const g = ctx.createLinearGradient(0, 0, 0, 512);
  g.addColorStop(0, '#e8eef8');
  g.addColorStop(0.44, '#9eb0c8');
  g.addColorStop(0.54, '#39424f');
  g.addColorStop(1, '#0d1015');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 1024, 512);
  ctx.fillStyle = '#ffffff';
  for (const [x, y, w, h, a] of [[70, 40, 280, 96, 0.95], [520, 16, 210, 64, 0.8], [790, 96, 170, 46, 0.7]]) {
    ctx.globalAlpha = a;
    ctx.fillRect(x, y, w, h);
  }
  ctx.globalAlpha = 1;

  const tex = new THREE.CanvasTexture(cv);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = pmrem.fromEquirectangular(tex).texture;
  pmrem.dispose();
  tex.dispose();
  return env;
}
scene.environment = buildEnvironment();

/* ---------- 灯光 ---------- */
const hemi = new THREE.HemisphereLight(0xdfe9ff, 0x0a0d14, 0.55);
scene.add(hemi);

const key = new THREE.DirectionalLight(0xffffff, 2.0);
key.position.set(4, -6, 10);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.near = 0.5;
key.shadow.camera.far = 30;
Object.assign(key.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5 });
key.shadow.camera.updateProjectionMatrix();
key.shadow.bias = -0.0008;
scene.add(key);

const rim = new THREE.DirectionalLight(0x7fb2ff, 0.7);
rim.position.set(-6, 4, 3);
scene.add(rim);

const baseIntensities = [hemi.intensity, key.intensity, rim.intensity];

/* ---------- 阴影地面 ---------- */
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(60, 60),
  new THREE.ShadowMaterial({ opacity: 0.32 }),
);
ground.position.z = -3.45;
ground.receiveShadow = true;
scene.add(ground);

/* ---------- 腕表 ---------- */
const watch = buildWatch({ weekdayLabels: WEEKDAY_LABELS[state.locale] });
watch.group.rotation.z = 0;
scene.add(watch.group);

/* ---------- UI ---------- */
const el = (id) => document.getElementById(id);
const zoneList = (() => {
  const all = typeof Intl.supportedValuesOf === 'function'
    ? Intl.supportedValuesOf('timeZone')
    : ['UTC', 'Asia/Shanghai', 'Asia/Tokyo', 'Asia/Kolkata', 'Europe/London', 'Europe/Paris',
       'America/New_York', 'America/Los_Angeles', 'Australia/Sydney', 'Pacific/Auckland'];
  const set = new Set(['UTC', localZone, ...all]);
  return [...set];
})();

for (const id of ['zoneA', 'zoneB']) {
  const select = el(id);
  for (const tz of zoneList) {
    const opt = document.createElement('option');
    opt.value = tz;
    opt.textContent = tz === localZone ? `${tz} (本机)` : tz;
    select.appendChild(opt);
  }
  select.value = id === 'zoneA' ? state.zoneA : state.zoneB;
  select.addEventListener('change', () => {
    if (id === 'zoneA') state.zoneA = select.value;
    else state.zoneB = select.value;
    localStorage.setItem(`watch3d.${id}`, select.value);
  });
}

function toggle(button, initial, onChange) {
  let value = initial;
  button.setAttribute('aria-pressed', String(value));
  button.addEventListener('click', () => {
    value = !value;
    button.setAttribute('aria-pressed', String(value));
    onChange(value);
  });
}

toggle(el('btnSweep'), state.mode === 'sweep', (on) => {
  state.mode = on ? 'sweep' : 'tick';
  el('btnSweep').textContent = on ? '扫秒' : '跳秒';
  localStorage.setItem('watch3d.mode', state.mode);
});
toggle(el('btnNight'), false, (on) => {
  state.night = on;
  watch.setNight(on);
  renderer.toneMappingExposure = on ? 0.34 : 1.05;
  hemi.intensity = baseIntensities[0] * (on ? 0.12 : 1);
  key.intensity = baseIntensities[1] * (on ? 0.14 : 1);
  rim.intensity = baseIntensities[2] * (on ? 0.2 : 1);
});
toggle(el('btnSpin'), state.spin, (on) => {
  controls.autoRotate = on;
});
toggle(el('btnLocale'), state.locale === 'zh', (on) => {
  state.locale = on ? 'zh' : 'en';
  watch.setWeekdayLabels(WEEKDAY_LABELS[state.locale]);
  localStorage.setItem('watch3d.locale', state.locale);
});
el('btnReset').addEventListener('click', () => {
  camera.position.copy(CAMERA_HOME);
  controls.target.set(0, 0, 0.1);
  controls.update();
});

/* ---------- 渲染循环 ---------- */
let lastFrame = performance.now();
let lastHud = 0;
// 转盘初始角度直接对齐，避免开场旋转一大圈
{
  const p = getZonedParts(clock.now(), state.zoneA);
  watch.discs.date.rotation.z = discRotation(p.day - 1, 31, 0);
  watch.discs.day.rotation.z = discRotation(p.weekday, 7, Math.PI / 2);
}

function tick(now) {
  const dt = Math.min(0.1, (now - lastFrame) / 1000);
  lastFrame = now;

  const instant = clock.now();
  const a = getZonedParts(instant, state.zoneA);
  const b = getZonedParts(instant, state.zoneB);
  const anglesA = computeHandAngles(a, { mode: state.mode });
  const anglesB = computeHandAngles(b, { mode: state.mode });

  watch.hands.hour.rotation.z = anglesA.hour;
  watch.hands.minute.rotation.z = anglesA.minute;
  watch.hands.second.rotation.z = anglesA.second;
  watch.hands.gmt.rotation.z = anglesB.hour24; // 第二时区：24 小时指针

  watch.discs.date.rotation.z = approachAngle(
    watch.discs.date.rotation.z, discRotation(a.day - 1, 31, 0), dt, 14,
  );
  watch.discs.day.rotation.z = approachAngle(
    watch.discs.day.rotation.z, discRotation(a.weekday, 7, Math.PI / 2), dt, 14,
  );

  if (now - lastHud > 100) {
    lastHud = now;
    el('clockA').textContent = formatDigital(a);
    el('metaA').textContent = `${formatDate(a, state.locale)} · ${formatOffset(a.offsetMinutes)}`;
    el('clockB').textContent = formatDigital(b);
    el('metaB').textContent = `${formatDate(b, state.locale)} · ${formatOffset(b.offsetMinutes)}`;
    el('metaDiff').textContent =
      `时差 ${formatOffsetDelta(a.offsetMinutes, b.offsetMinutes)}` +
      (clock.isRealtime ? '' : ` · 测试时钟 ×${clock.speed}`);
  }

  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight, false);
});

// 便于浏览器控制台/自动化测试断言
window.__watch3d = { state, clock, watch, scene, camera, renderer, getZonedParts, computeHandAngles };
```

## watch3d/test/timeMath.test.mjs

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TAU, approachAngle, computeHandAngles, createVirtualClock, discRotation, formatDate,
  formatDigital, formatOffset, formatOffsetDelta, getZonedParts, isValidTimeZone,
  shortestAngleDelta,
} from '../src/timeMath.js';

const T = (iso) => new Date(iso);
const close = (a, b, eps = 1e-9) =>
  assert.ok(Math.abs(a - b) < eps, `expected ${a} ≈ ${b}`);

test('时区换算：东八区', () => {
  const p = getZonedParts(T('2026-08-17T10:14:05.923Z'), 'Asia/Shanghai');
  assert.equal(p.hour, 18);
  assert.equal(p.minute, 14);
  assert.equal(p.second, 5);
  assert.equal(p.millisecond, 923);
  assert.deepEqual([p.year, p.month, p.day], [2026, 8, 17]);
  assert.equal(p.weekday, 1); // 星期一
  assert.equal(p.offsetMinutes, 480);
});

test('时区换算：UTC 与半小时偏移时区', () => {
  const utc = getZonedParts(T('2026-08-17T10:14:05Z'), 'UTC');
  assert.equal(utc.hour, 10);
  assert.equal(utc.offsetMinutes, 0);

  const kolkata = getZonedParts(T('2026-08-17T10:14:05Z'), 'Asia/Kolkata');
  assert.equal(kolkata.hour, 15);
  assert.equal(kolkata.minute, 44);
  assert.equal(kolkata.offsetMinutes, 330);
});

test('夏令时自动生效', () => {
  const summer = getZonedParts(T('2026-08-17T10:14:00Z'), 'America/New_York');
  assert.equal(summer.offsetMinutes, -240);
  assert.equal(summer.hour, 6);

  const winter = getZonedParts(T('2026-01-15T12:00:00Z'), 'America/New_York');
  assert.equal(winter.offsetMinutes, -300);
  assert.equal(winter.hour, 7);
});

test('跨日：+14 区已进入次日', () => {
  const p = getZonedParts(T('2026-08-17T23:00:00Z'), 'Pacific/Kiritimati');
  assert.deepEqual([p.year, p.month, p.day], [2026, 8, 18]);
  assert.equal(p.hour, 13);
  assert.equal(p.weekday, 2); // 星期二
  assert.equal(p.offsetMinutes, 840);
});

test('午夜的小时为 0（不是 24）', () => {
  const p = getZonedParts(T('2026-08-16T16:00:00Z'), 'Asia/Shanghai');
  assert.equal(p.hour, 0);
  assert.equal(p.day, 17);
});

test('指针角度：3 点整', () => {
  const parts = { hour: 3, minute: 0, second: 0, millisecond: 0 };
  const a = computeHandAngles(parts);
  close(a.hour, -Math.PI / 2);
  close(a.minute, 0);
  close(a.second, 0);
  close(a.hour24, -Math.PI / 4); // 24 小时指针走一半的速度
});

test('指针角度：时针与分针连续走时', () => {
  const a = computeHandAngles({ hour: 10, minute: 30, second: 30, millisecond: 0 });
  close(a.minute, -((30 + 0.5) / 60) * TAU);
  close(a.hour, -((10 + 30.5 / 60) / 12) * TAU);
});

test('秒针模式：sweep / beat8 / tick', () => {
  const parts = { hour: 1, minute: 0, second: 30, millisecond: 500 };
  close(computeHandAngles(parts, { mode: 'sweep' }).second, -(30.5 / 60) * TAU);
  close(computeHandAngles(parts, { mode: 'beat8' }).second, -(30.5 / 60) * TAU);
  close(computeHandAngles(parts, { mode: 'tick' }).second, -(30 / 60) * TAU);
  close(
    computeHandAngles({ ...parts, millisecond: 300 }, { mode: 'beat8' }).second,
    -(30.25 / 60) * TAU,
  );
});

test('24 小时指针一天只转一圈', () => {
  close(computeHandAngles({ hour: 0, minute: 0, second: 0, millisecond: 0 }).hour24, 0);
  close(computeHandAngles({ hour: 12, minute: 0, second: 0, millisecond: 0 }).hour24, -Math.PI);
  close(computeHandAngles({ hour: 18, minute: 0, second: 0, millisecond: 0 }).hour24, -TAU * 0.75);
});

test('转盘角度：视窗对齐', () => {
  close(discRotation(0, 31, 0), 0);                       // 1 号 -> 3 点视窗
  close(discRotation(16, 31, 0), -(16 * TAU) / 31);       // 17 号
  close(discRotation(1, 7, Math.PI / 2), Math.PI / 2 - TAU / 7); // 周一 -> 12 点视窗
});

test('最短角差与阻尼趋近', () => {
  close(shortestAngleDelta(3, -3), TAU - 6);
  close(shortestAngleDelta(0, Math.PI / 2), Math.PI / 2);

  const next = approachAngle(0, Math.PI / 2, 0.1, 12);
  close(next, (Math.PI / 2) * (1 - Math.exp(-1.2)), 1e-12);

  let cur = 0.2;
  for (let i = 0; i < 200; i++) cur = approachAngle(cur, -3.0, 1 / 60, 14);
  assert.ok(Math.abs(shortestAngleDelta(cur, -3.0)) < 1e-3);
});

test('偏移与时差格式化', () => {
  assert.equal(formatOffset(480), 'UTC+08:00');
  assert.equal(formatOffset(-300), 'UTC-05:00');
  assert.equal(formatOffset(330), 'UTC+05:30');
  assert.equal(formatOffset(0), 'UTC+00:00');
  assert.equal(formatOffsetDelta(480, 0), '-8:00');
  assert.equal(formatOffsetDelta(0, 330), '+5:30');
  assert.equal(formatOffsetDelta(60, 60), '0:00');
});

test('文本输出', () => {
  const p = getZonedParts(T('2026-08-17T10:14:05Z'), 'Asia/Shanghai');
  assert.equal(formatDigital(p), '18:14:05');
  assert.equal(formatDate(p, 'en'), '2026-08-17 MON');
  assert.equal(formatDate(p, 'zh'), '2026-08-17 周一');
});

test('时区名校验', () => {
  assert.equal(isValidTimeZone('Asia/Shanghai'), true);
  assert.equal(isValidTimeZone('Mars/Olympus'), false);
});

test('虚拟时钟按倍率推进', () => {
  let t = 1000;
  const clock = createVirtualClock({
    startMs: Date.parse('2026-08-17T23:59:30Z'),
    speed: 60,
    monotonic: () => t,
  });
  assert.equal(clock.isRealtime, false);
  assert.equal(clock.nowMs(), Date.parse('2026-08-17T23:59:30Z'));
  t = 1500; // 真实 0.5s -> 虚拟 30s
  assert.equal(clock.now().toISOString(), '2026-08-18T00:00:00.000Z');
});

test('默认时钟即真实时间', () => {
  const clock = createVirtualClock();
  assert.equal(clock.isRealtime, true);
  assert.ok(Math.abs(clock.nowMs() - Date.now()) < 50);
});
```

## watch3d/package.json

```json
{
  "name": "watch3d",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "description": "Three.js 3D GMT wristwatch driven by the real clock, with dual time zones and day/date discs.",
  "scripts": {
    "test": "node --test test/",
    "serve": "python3 -m http.server 8080"
  },
  "engines": {
    "node": ">=18"
  }
}
```

## 运行方式

```bash
cd watch3d
npm run serve          # 或: npx --yes serve -l 8080 .
# 浏览器打开 http://localhost:8080/
```

必须通过 HTTP 打开（ES modules + importmap 在 `file://` 下会被 CORS 拦截）。Three.js 0.160.0 通过 importmap 从 unpkg 加载，首次运行需要网络；要完全离线就 `npm i three@0.160.0`，把 importmap 的两个地址改成 `./node_modules/three/build/three.module.js` 和 `./node_modules/three/examples/jsm/`。

## 测试说明

单元测试（纯逻辑，无浏览器）：

```bash
npm test        # node --test test/  → 16 个用例
```

覆盖点：IANA 时区换算与真实 UTC 偏移、夏令时冬夏两次采样、半小时时区（Kolkata +05:30）、+14 时区跨日、午夜 0 点边界、时/分针连续走时、秒针 sweep/beat8/tick 三种模式、24h 指针半速、日期/星期盘对窗角度、最短角差与阻尼收敛、格式化、虚拟时钟倍率。需要 Node ≥ 18 且带完整 ICU（官方发行版默认满足）。

浏览器端人工验收清单：

1. 秒针连续平滑扫动，点“扫秒”切到跳秒后变为每秒一跳；分针、时针始终连续爬行（不跳格）。
2. 面板数字时间与本机系统时钟一致；`UTC±hh:mm` 与系统时区一致。
3. 3 点视窗日期、12 点视窗星期与真实日历一致；切“中文星期”后转盘文字变为“周一”等且仍对准视窗。
4. 双时区：把第二时区改成 `America/New_York`，蓝色 24 小时指针指向内圈 24h 刻度对应的当地小时（如纽约 06:14 → 指针在“6”附近，处于白昼浅色区）；`Asia/Kolkata` 可验证半小时偏移。
5. 拖拽/滚轮可从任意角度观察表壳、表圈、表冠、表耳与链带，确认是完整 3D 实体而非贴图。

跨日与换日动作的加速验证（无需等到午夜）：

```
http://localhost:8080/?start=2026-08-17T15:59:40Z&speed=120
```

`start` 为 UTC 瞬间、`speed` 为倍率。上例约 20 秒后主时区（东八区）跨入 8 月 18 日，可观察日期盘 17→18、星期盘 MON→TUE 的快速换窗，以及 24h 指针经过 24 点。`?speed=1440` 可在约一分钟内看完一整天的昼夜指针行程。

一处需要你知道的取舍：星期视窗在 12 点、日期视窗在 3 点且径向靠内，是为了让两个转盘的环形轨道（1.00–1.38 与 0.60–0.98）完全不重叠，从而避免 z-fighting；这与部分真表把日期窗放在更外圈的布局略有差别。