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
