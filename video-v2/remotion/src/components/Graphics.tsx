import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {formatAt} from '../numbers';
import type {Overlay, RGB} from '../types';

// 정보 그래픽: 화면 중앙 위쪽(안전 영역 y 280~1000)에만 그린다. 가독성 우선(작은 글씨 금지, 최소 34px).
export const FONT = '"Noto Sans CJK KR", "Noto Sans KR", sans-serif';
const rgb = (c: RGB, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
const GLASS: React.CSSProperties = {
  background: 'rgba(8,10,22,0.62)',
  border: '2px solid rgba(255,255,255,0.18)',
  borderRadius: 40,
  backdropFilter: 'blur(6px)',
  boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
};
const AREA: React.CSSProperties = {position: 'absolute', left: 70, right: 70, top: 300, fontFamily: FONT, color: '#fff'};

const usePop = (delay = 0) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: frame - delay, fps, config: {damping: 14, stiffness: 150}});
};

const Title: React.FC<{text?: string; accent: RGB}> = ({text, accent}) =>
  text ? <div style={{fontSize: 44, fontWeight: 900, color: rgb(accent), marginBottom: 22}}>{text}</div> : null;

// 1) 숫자 카운트업
export const AnimatedNumber: React.FC<{value: string; label?: string; color: RGB; frames: number}> = ({value, label, color, frames}) => {
  const frame = useCurrentFrame();
  const pop = usePop(2);
  const count = interpolate(frame, [4, Math.min(frames - 1, 34)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const size = value.length > 7 ? 120 : 170;
  return (
    <div style={{...AREA, top: 380, display: 'flex', justifyContent: 'center'}}>
      <div style={{...GLASS, padding: '34px 60px 38px', textAlign: 'center', transform: `scale(${0.7 + 0.3 * pop})`, opacity: pop}}>
        <div style={{fontSize: size, fontWeight: 900, lineHeight: 1.05, color: rgb(color), fontVariantNumeric: 'tabular-nums'}}>
          {formatAt(value, count)}
        </div>
        {label ? <div style={{fontSize: 40, fontWeight: 700, marginTop: 14}}>{label}</div> : null}
      </div>
    </div>
  );
};

// 2) 가격·요금제 비교 (조건 문구 필수, 같은 상자 안에 크게)
export const ComparisonGraphic: React.FC<{o: Extract<Overlay, {type: 'compare'}>; accent: RGB}> = ({o, accent}) => {
  const box = usePop(0);
  return (
    <div style={{...AREA, ...GLASS, padding: '34px 40px', opacity: box, transform: `translateY(${(1 - box) * 40}px)`}}>
      <Title text={o.title} accent={accent} />
      {o.items.map((it, i) => <CompareRow key={i} i={i} it={it} accent={accent} />)}
      <div style={{fontSize: 34, fontWeight: 700, lineHeight: 1.35, marginTop: 18, color: 'rgba(255,255,255,0.92)'}}>{o.conditions}</div>
    </div>
  );
};
const CompareRow: React.FC<{i: number; it: {label: string; value: string; highlight?: boolean}; accent: RGB}> = ({i, it, accent}) => {
  const p = usePop(6 + i * 7);
  return (
    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 26px', marginBottom: 14,
      borderRadius: 24, background: it.highlight ? rgb(accent, 0.22) : 'rgba(255,255,255,0.07)',
      border: it.highlight ? `3px solid ${rgb(accent)}` : '3px solid transparent', opacity: p, transform: `translateX(${(1 - p) * -60}px)`}}>
      <span style={{fontSize: 44, fontWeight: 800}}>{it.label}</span>
      <span style={{fontSize: 56, fontWeight: 900, color: it.highlight ? rgb(accent) : '#fff'}}>{it.value}</span>
    </div>
  );
};

// 3) 체크리스트 (하나씩 체크)
export const ChecklistGraphic: React.FC<{o: Extract<Overlay, {type: 'checklist'}>; accent: RGB}> = ({o, accent}) => {
  const box = usePop(0);
  return (
    <div style={{...AREA, ...GLASS, padding: '34px 40px', opacity: box}}>
      <Title text={o.title} accent={accent} />
      {o.items.slice(0, 4).map((t, i) => <CheckRow key={i} i={i} text={t} accent={accent} />)}
    </div>
  );
};
const CheckRow: React.FC<{i: number; text: string; accent: RGB}> = ({i, text, accent}) => {
  const p = usePop(8 + i * 12);
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 22, marginBottom: 20, opacity: 0.35 + 0.65 * p}}>
      <div style={{width: 64, height: 64, borderRadius: 18, flexShrink: 0, background: p > 0.5 ? rgb(accent) : 'rgba(255,255,255,0.15)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${0.6 + 0.4 * p})`}}>
        <svg width="40" height="40" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="#10121e"
          strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="24" strokeDashoffset={24 * (1 - p)} /></svg>
      </div>
      <span style={{fontSize: 46, fontWeight: 800, lineHeight: 1.25}}>{text}</span>
    </div>
  );
};

// 4) 타임라인 (유지 기간·조건)
export const TimelineGraphic: React.FC<{o: Extract<Overlay, {type: 'timeline'}>; accent: RGB; frames: number}> = ({o, accent, frames}) => {
  const frame = useCurrentFrame();
  const box = usePop(0);
  const n = Math.max(1, o.steps.length);
  const fill = interpolate(frame, [8, Math.min(frames - 1, 8 + n * 14)], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
  return (
    <div style={{...AREA, ...GLASS, padding: '34px 40px', opacity: box}}>
      <Title text={o.title} accent={accent} />
      <div style={{position: 'relative', paddingLeft: 56}}>
        <div style={{position: 'absolute', left: 22, top: 18, bottom: 18, width: 8, borderRadius: 4, background: 'rgba(255,255,255,0.15)'}} />
        <div style={{position: 'absolute', left: 22, top: 18, width: 8, borderRadius: 4, background: rgb(accent),
          height: `calc((100% - 36px) * ${fill})`}} />
        {o.steps.map((s, i) => {
          const on = fill >= (n === 1 ? 0 : i / (n - 1)) - 0.001;
          return (
            <div key={i} style={{position: 'relative', marginBottom: 26}}>
              <div style={{position: 'absolute', left: -50, top: 10, width: 36, height: 36, borderRadius: 18,
                background: on ? rgb(accent) : 'rgba(255,255,255,0.25)'}} />
              <div style={{fontSize: 40, fontWeight: 900, color: on ? rgb(accent) : 'rgba(255,255,255,0.6)'}}>{s.when}</div>
              <div style={{fontSize: 40, fontWeight: 700, opacity: on ? 1 : 0.6}}>{s.label}</div>
            </div>
          );
        })}
      </div>
      {o.note ? <div style={{fontSize: 34, fontWeight: 700, opacity: 0.9}}>{o.note}</div> : null}
    </div>
  );
};

// 5) 살림템 특징 강조 (최대 3개, 확인된 특징만)
export const FeatureHighlight: React.FC<{o: Extract<Overlay, {type: 'features'}>; accent: RGB}> = ({o, accent}) => (
  // 상품 사진(위쪽) 아래 공간에 표시. 이 장면은 제목·자막 대신 특징 카드를 쓴다.
  <div style={{...AREA, top: 1070}}>
    {o.items.slice(0, 3).map((f, i) => <FeatureRow key={i} i={i} f={f} accent={accent} />)}
  </div>
);
const FeatureRow: React.FC<{i: number; f: {title: string; desc?: string}; accent: RGB}> = ({i, f, accent}) => {
  const p = usePop(6 + i * 9);
  return (
    <div style={{...GLASS, borderRadius: 28, padding: '20px 30px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 22,
      opacity: p, transform: `translateX(${(1 - p) * (i % 2 ? 80 : -80)}px)`}}>
      <div style={{fontSize: 46, fontWeight: 900, color: '#10121e', background: rgb(accent), borderRadius: 16, width: 64, height: 64,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0}}>{i + 1}</div>
      <div>
        <div style={{fontSize: 44, fontWeight: 900}}>{f.title}</div>
        {f.desc ? <div style={{fontSize: 34, fontWeight: 600, opacity: 0.9}}>{f.desc}</div> : null}
      </div>
    </div>
  );
};

// 6) 상품 CTA (프로필 링크 → 번호)
export const ProductCTA: React.FC<{o: Extract<Overlay, {type: 'cta'}>; accent: RGB}> = ({o, accent}) => {
  const frame = useCurrentFrame();
  const p = usePop(2);
  const pulse = 1 + 0.04 * Math.sin(frame / 6);
  return (
    <div style={{...AREA, top: 420, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
      <div style={{...GLASS, padding: '30px 60px', textAlign: 'center', opacity: p, transform: `scale(${(0.7 + 0.3 * p) * pulse})`}}>
        <div style={{fontSize: 44, fontWeight: 800}}>프로필 링크에서</div>
        <div style={{fontSize: 190, fontWeight: 900, color: rgb(accent), lineHeight: 1.05}}>{o.number}</div>
        <div style={{fontSize: 40, fontWeight: 700}}>{o.text}</div>
      </div>
    </div>
  );
};

export const OverlayView: React.FC<{o: Overlay; accent: RGB; frames: number}> = ({o, accent, frames}) => {
  switch (o.type) {
    case 'number': return <AnimatedNumber value={o.value} label={o.label} color={o.color ?? accent} frames={frames} />;
    case 'compare': return <ComparisonGraphic o={o} accent={accent} />;
    case 'checklist': return <ChecklistGraphic o={o} accent={accent} />;
    case 'timeline': return <TimelineGraphic o={o} accent={accent} frames={frames} />;
    case 'features': return <FeatureHighlight o={o} accent={accent} />;
    case 'cta': return <ProductCTA o={o} accent={accent} />;
    default: return null;
  }
};
