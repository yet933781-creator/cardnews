import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseNumber, formatAt} from '../src/numbers.ts';

test('끝나면 원문과 정확히 같다', () => {
  for (const s of ['1.6%', '18,700원', '93일', '1.2조', '5번', '0.8%']) assert.equal(formatAt(s, 1), s);
});

test('중간값은 소수 자릿수·쉼표·단위를 유지', () => {
  assert.match(formatAt('1.6%', 0.5), /^\d\.\d%$/);
  assert.match(formatAt('18,700원', 0.5), /^[\d,]+원$/);
  assert.equal(formatAt('93일', 0), '0일');
});

test('숫자가 없거나 2개 이상이면 애니메이션 없이 원문', () => {
  assert.equal(parseNumber('유심 교체'), null);
  assert.equal(formatAt('990원 → 9,900원', 0.3), '990원 → 9,900원');
});
