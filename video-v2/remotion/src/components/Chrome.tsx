import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT} from './Graphics';
import type {RGB} from '../types';

const rgb = (c: RGB) => `rgb(${c[0]},${c[1]},${c[2]})`;
const pill: React.CSSProperties = {
  display: 'inline-block', background: 'rgba(16,18,30,0.92)', color: '#fff', fontFamily: FONT, fontWeight: 700,
  fontSize: 26, padding: '8px 16px', borderRadius: 999, marginRight: 10,
};

// 위쪽 고정 요소: 매장 태그 + 진행 막대 + 광고 표시 + 장면 표시(AI 생성 등)
export const TopBar: React.FC<{storeTag: [string, string]; index: number; total: number; accent: RGB; adLabel?: string | null; labels: string[]}> =
  ({storeTag, index, total, accent, adLabel, labels}) => (
    <>
      <div style={{position: 'absolute', left: 60, top: 64, fontFamily: FONT, display: 'flex', alignItems: 'center', gap: 10}}>
        <span style={{background: '#fff', color: '#10121e', fontWeight: 900, fontSize: 30, padding: '4px 14px', borderRadius: 999}}>{storeTag[0]}</span>
        <span style={{color: '#fff', fontWeight: 700, fontSize: 30, textShadow: '0 2px 8px rgba(0,0,0,0.6)'}}>{storeTag[1]}</span>
      </div>
      {adLabel ? <div style={{position: 'absolute', right: 60, top: 62, ...pill, marginRight: 0, fontSize: 30, fontWeight: 900}}>{adLabel}</div> : null}
      <div style={{position: 'absolute', left: 60, right: 60, top: 140, display: 'flex', gap: 8}}>
        {Array.from({length: total}).map((_, k) => (
          <div key={k} style={{flex: 1, height: 8, borderRadius: 4, background: k <= index ? rgb(accent) : 'rgba(80,90,140,0.8)'}} />
        ))}
      </div>
      <div style={{position: 'absolute', left: 60, top: 172}}>
        {labels.map((l, i) => <span key={i} style={pill}>{l}</span>)}
      </div>
    </>
  );

// 제목·자막: 앱 아래쪽 UI(캡션·버튼)에 가리지 않도록 y 1080~1600 안
export const SubtitleOverlay: React.FC<{headline?: string; caption?: string; top?: number}> = ({headline, caption, top = 1080}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const head = spring({frame: frame - 2, fps, config: {damping: 14, stiffness: 160}});
  const cap = spring({frame: frame - 8, fps, config: {damping: 12, stiffness: 180}});
  return (
    <div style={{position: 'absolute', left: 70, right: 70, top, fontFamily: FONT}}>
      {headline ? (
        <div style={{color: '#fff', fontWeight: 900, fontSize: 86, lineHeight: 1.18, textShadow: '0 4px 18px rgba(0,0,0,0.6)',
          transform: `translateY(${(1 - head) * 60}px)`, opacity: head}}>
          {headline.split('\n').map((l, i) => <div key={i}>{l}</div>)}
        </div>
      ) : null}
      {caption ? (
        <div style={{display: 'flex', justifyContent: 'center', marginTop: 40}}>
          <div style={{background: '#fff', color: '#10121e', fontWeight: 900, fontSize: 54, borderRadius: 28, padding: '20px 40px',
            maxWidth: 920, textAlign: 'center', transform: `scale(${0.6 + 0.4 * cap})`, opacity: cap, boxShadow: '0 8px 30px rgba(0,0,0,0.35)'}}>
            {caption}
          </div>
        </div>
      ) : null}
    </div>
  );
};

// 아래쪽을 어둡게 해 글자를 읽기 쉽게 (위쪽도 살짝)
export const ReadabilityShade: React.FC = () => (
  <div style={{position: 'absolute', inset: 0,
    background: 'linear-gradient(to bottom, rgba(6,8,20,0.55) 0%, rgba(6,8,20,0) 14%, rgba(6,8,20,0) 50%, rgba(6,8,20,0.78) 72%, rgba(6,8,20,0.9) 100%)'}} />
);
