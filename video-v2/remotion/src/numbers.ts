// 숫자 카운트업 계산 (순수 함수). 입력 문자열의 숫자만 0 → 값으로 올리고, 앞뒤 글자·소수 자릿수·쉼표는 그대로 둔다.
// 숫자가 없거나 여러 개면 애니메이션 없이 원문 그대로 보여준다(임의 숫자 생성 금지).

export type ParsedNumber = {prefix: string; value: number; decimals: number; comma: boolean; suffix: string};

export function parseNumber(text: string): ParsedNumber | null {
  const m = text.match(/-?\d[\d,]*(\.\d+)?/g);
  if (!m || m.length !== 1) return null;
  const raw = m[0];
  const i = text.indexOf(raw);
  const value = Number(raw.replace(/,/g, ''));
  if (!Number.isFinite(value)) return null;
  return {
    prefix: text.slice(0, i),
    value,
    decimals: raw.includes('.') ? raw.split('.')[1].length : 0,
    comma: raw.includes(','),
    suffix: text.slice(i + raw.length),
  };
}

export function formatAt(text: string, progress: number): string {
  const p = parseNumber(text);
  if (!p) return text;
  const t = Math.min(1, Math.max(0, progress));
  const eased = 1 - Math.pow(1 - t, 3);
  if (t >= 1) return text; // 끝나면 반드시 원문 그대로
  const v = p.value * eased;
  let s = v.toFixed(p.decimals);
  if (p.comma) {
    const [a, b] = s.split('.');
    s = a.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (b ? '.' + b : '');
  }
  return p.prefix + s + p.suffix;
}
