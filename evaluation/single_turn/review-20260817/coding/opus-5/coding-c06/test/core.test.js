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
