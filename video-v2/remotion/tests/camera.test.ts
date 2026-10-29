// 실행: node --experimental-strip-types --test video-v2/remotion/tests/
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {PRESETS, cameraTransform, maxShift, autoPreset, parallaxForeground} from '../src/camera.ts';

const steps = Array.from({length: 101}, (_, i) => i / 100);

test('모든 프리셋: 검은 여백 없음 (이동량 <= (배율-1)/2, 배율 >= 1)', () => {
  for (const p of PRESETS) {
    for (const t of steps) {
      for (const focus of [{x: 0, y: 0}, {x: 1, y: 1}, {x: 0.5, y: 0.3}]) {
        const tr = cameraTransform(p, t, focus);
        assert.ok(tr.scale >= 1 - 1e-9, `${p} t=${t} scale=${tr.scale}`);
        assert.ok(Math.abs(tr.tx) <= maxShift(tr.scale) + 1e-9, `${p} t=${t} tx=${tr.tx}`);
        assert.ok(Math.abs(tr.ty) <= maxShift(tr.scale) + 1e-9, `${p} t=${t} ty=${tr.ty}`);
      }
    }
  }
});

test('배율 범위: 줌은 1.0~1.12, push_in 은 1.18 이하', () => {
  for (const t of steps) {
    assert.ok(cameraTransform('slow_zoom_in', t).scale <= 1.12 + 1e-9);
    assert.ok(cameraTransform('slow_zoom_out', t).scale <= 1.12 + 1e-9);
    assert.ok(cameraTransform('push_in', t).scale <= 1.18 + 1e-9);
  }
  assert.equal(cameraTransform('slow_zoom_in', 0).scale, 1);
  assert.ok(Math.abs(cameraTransform('slow_zoom_in', 1).scale - 1.12) < 1e-9);
  assert.ok(Math.abs(cameraTransform('slow_zoom_out', 1).scale - 1) < 1e-9);
});

test('흔들림 없음: 움직임이 한 방향으로만 (단조)', () => {
  for (const p of PRESETS) {
    let prevS = cameraTransform(p, 0).scale, prevX = cameraTransform(p, 0).tx;
    let dirS = 0, dirX = 0;
    for (const t of steps.slice(1)) {
      const tr = cameraTransform(p, t);
      const ds = Math.sign(Math.round((tr.scale - prevS) * 1e9));
      const dx = Math.sign(Math.round((tr.tx - prevX) * 1e9));
      if (ds) { assert.ok(dirS === 0 || dirS === ds, `${p} 배율 방향 바뀜`); dirS = ds; }
      if (dx) { assert.ok(dirX === 0 || dirX === dx, `${p} 이동 방향 바뀜`); dirX = dx; }
      prevS = tr.scale; prevX = tr.tx;
    }
  }
});

test('static 은 움직임 없음, 진행률 범위 밖도 안전', () => {
  assert.deepEqual(cameraTransform('static', 0.7), {scale: 1, tx: 0, ty: 0});
  const a = cameraTransform('pan_left', -1), b = cameraTransform('pan_left', 2);
  assert.ok(Math.abs(a.tx) <= maxShift(a.scale) + 1e-9 && Math.abs(b.tx) <= maxShift(b.scale) + 1e-9);
});

test('자동 프리셋: 같은 움직임 연속 없음, 영상은 static', () => {
  for (let i = 0; i < 10; i++) assert.notEqual(autoPreset(i, false), autoPreset(i + 1, false));
  assert.equal(autoPreset(3, true), 'static');
});

test('전경 시차는 작게 (±24px 이내)', () => {
  for (const t of steps) assert.ok(Math.abs(parallaxForeground(t)) <= 24);
});
