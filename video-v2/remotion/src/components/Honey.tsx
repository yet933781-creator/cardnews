import React from 'react';
import {AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {CameraMotion} from './CameraMotion';
import {FONT} from './Graphics';
import type {RGB, SceneV2} from '../types';

// 유튜브 '꿀템' 쇼츠식 화면 요소
// - 꽉 찬 화면에서 컷이 빠르게 넘어간다 (사진 여러 장이면 장면 안에서 나눠 보여줌)
// - 말하는 대로 바뀌는 큰 자막 (화면 중앙 아래, 앱 UI 위)
// - 영상 내내 위에 고정된 제목 (예: "창가 냉기 잡는 꿀템")

const rgb = (c: RGB) => `rgb(${c[0]},${c[1]},${c[2]})`;
const BOX = {top: 360, height: 840}; // 상품 사진: 위 제목(236~)과 아래 자막(1230~) 사이

export const HoneyVisual: React.FC<{s: SceneV2}> = ({s}) => {
  const imgs = s.images && s.images.length ? s.images : null;
  if (!imgs) {
    return <CameraMotion image={s.image} clip={s.clip} preset={s.camera} frames={s.frames} focus={s.focus} productFit={s.productFit} box={BOX} />;
  }
  const per = Math.max(1, Math.floor(s.frames / imgs.length));
  return (
    <AbsoluteFill>
      {imgs.map((im, k) => {
        const from = k * per;
        const dur = k === imgs.length - 1 ? s.frames - from : per;
        return (
          <Sequence key={k} from={from} durationInFrames={dur}>
            <CutIn>
              {im.clip ? (
                <CameraMotion clip={im.src} preset={im.camera} frames={dur} clipStart={im.start ?? 0} />
              ) : (
                <CameraMotion image={im.src} preset={im.camera} frames={dur} productFit={im.fit ?? s.productFit} box={BOX} />
              )}
            </CutIn>
            {im.label ? <CutLabel text={im.label} /> : null}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

// 컷마다 출처 표시 (AI 연출 장면 / 실제 상품 사진 등) — 진행 막대 아래 왼쪽
const CutLabel: React.FC<{text: string}> = ({text}) => (
  <div style={{position: 'absolute', left: 60, top: 172, fontFamily: FONT, background: 'rgba(16,18,30,0.92)', color: '#fff',
    fontWeight: 700, fontSize: 26, padding: '8px 16px', borderRadius: 999}}>{text}</div>
);

// 컷 전환: 아주 짧게 살짝 확대되며 들어옴 (번쩍임 없이)
const CutIn: React.FC<{children: React.ReactNode}> = ({children}) => {
  const frame = useCurrentFrame();
  const z = interpolate(frame, [0, 5], [1.06, 1], {extrapolateRight: 'clamp'});
  const o = interpolate(frame, [0, 3], [0.4, 1], {extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{transform: `scale(${z})`, opacity: o}}>{children}</AbsoluteFill>;
};

// 말자막: 지금 읽는 구절만 크게. 숫자가 든 낱말은 강조색.
export const HoneySubs: React.FC<{subs?: SceneV2['subs']; accent: RGB; top?: number; plain?: boolean}> = ({subs, accent, top = 1230, plain = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!subs || !subs.length) return null;
  const cur = subs.find((c) => frame >= c.from && frame < c.to) ?? (frame >= subs[subs.length - 1].from ? subs[subs.length - 1] : null);
  if (!cur) return null;
  const pop = spring({frame: frame - cur.from, fps, config: {damping: 13, stiffness: 220}});
  return (
    <div style={{position: 'absolute', left: 60, right: 60, top, display: 'flex', justifyContent: 'center', fontFamily: FONT}}>
      <div style={{background: plain ? 'transparent' : 'rgba(0,0,0,0.62)', borderRadius: 18, padding: '14px 30px', maxWidth: 960, textAlign: 'center',
        transform: `scale(${0.85 + 0.15 * pop})`}}>
        <span style={{color: '#fff', fontSize: plain ? 64 : 68, fontWeight: 900, lineHeight: 1.25, wordBreak: 'keep-all',
          ...(plain ? {WebkitTextStroke: '6px rgba(0,0,0,0.85)', paintOrder: 'stroke fill', textShadow: '0 3px 14px rgba(0,0,0,0.6)'} : {})}}>
          {cur.text.split(' ').map((w, i) => (
            <span key={i} style={{color: /\d/.test(w) ? rgb(accent) : '#fff'}}>{(i ? ' ' : '') + w}</span>
          ))}
        </span>
      </div>
    </div>
  );
};

// 위에 고정되는 제목 (영상 전체)
export const HoneyHeader: React.FC<{text?: string; small?: boolean}> = ({text, small}) =>
  text ? (
    <div style={{position: 'absolute', left: 60, right: 60, top: 236, display: 'flex', justifyContent: 'center', fontFamily: FONT}}>
      <div style={{background: 'rgba(0,0,0,0.78)', color: '#fff', fontSize: small ? 38 : 50, fontWeight: small ? 700 : 900, lineHeight: 1.3,
        padding: '12px 26px', borderRadius: 14, textAlign: 'center', whiteSpace: 'pre-line', wordBreak: 'keep-all'}}>{text}</div>
    </div>
  ) : null;

// 첫 장면 후킹 문구 (크고 굵게, 노란 강조)
export const HoneyHook: React.FC<{text?: string; accent: RGB}> = ({text, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!text) return null;
  const p = spring({frame: frame - 3, fps, config: {damping: 12, stiffness: 170}});
  return (
    <div style={{position: 'absolute', left: 60, right: 60, top: 930, textAlign: 'center', fontFamily: FONT,
      transform: `scale(${0.7 + 0.3 * p})`, opacity: p}}>
      {text.split('\n').map((l, i) => (
        <div key={i} style={{fontSize: 92, fontWeight: 900, lineHeight: 1.18, color: i === 0 ? '#fff' : rgb(accent),
          textShadow: '0 0 4px #000, 0 6px 22px rgba(0,0,0,0.85)', WebkitTextStroke: '3px rgba(0,0,0,0.85)', paintOrder: 'stroke fill'}}>{l}</div>
      ))}
    </div>
  );
};

export const HoneyShade: React.FC = () => (
  <div style={{position: 'absolute', inset: 0,
    background: 'linear-gradient(to bottom, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0) 18%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 80%, rgba(0,0,0,0.6) 100%)'}} />
);
