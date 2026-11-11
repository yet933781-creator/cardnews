import React from 'react';
import {
  AbsoluteFill, Audio, Img, OffthreadVideo, Series, interpolate, spring, staticFile,
  useCurrentFrame, useVideoConfig,
} from 'remotion';

export type Scene = {
  bg: string;          // 배경 PNG (영상 장면이면 투명 레이어: 태그·진행막대·광고 표시)
  clip?: string;       // 영상 장면 (장면 길이에 맞춰 미리 잘라 둔 mp4)
  audio: string;       // 장면 내레이션
  frames: number;
  headline?: string;
  caption?: string;
  top?: number;        // 제목·자막 시작 높이 (기본 1080, 사장님 장면은 사진에 맞춰 1190)
  cont?: boolean;      // 상황극: 앞 장면에 이어지는 대사 (페이드·제목 애니메이션 없이 이어 붙임)
  bubble?: {who: string; text: string; right: boolean} | null;  // 상황극 대사 말풍선
  punch?: boolean;     // 빠른 컷 형식 (script.json "style": "punch"): 바로 전환 + 위쪽 큰 글자 + 단어별 자막
  words?: string;      // 단어별 자막 문장. [강조] 로 감싼 단어는 노란색으로 크게
};
export type ShortProps = {scenes: Scene[]; fps: number};

const FONT = '"Noto Sans CJK KR", "Noto Sans KR", sans-serif';

const STROKE = [[-5, -5], [5, -5], [-5, 5], [5, 5], [0, -6], [0, 6], [-6, 0], [6, 0]]
  .map(([x, y]) => `${x}px ${y}px 0 #000`).join(', ') + ', 0 8px 16px rgba(0,0,0,0.7)';

// 빠른 컷 장면: 페이드 없이 바로 바뀌고, 처음 6프레임 동안 살짝 당겨졌다 돌아온다(스냅 줌).
const PunchView: React.FC<{s: Scene}> = ({s}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const snap = interpolate(frame, [0, 6], [1.09, 1], {extrapolateRight: 'clamp'});
  const head = spring({frame, fps, config: {damping: 10, mass: 0.6, stiffness: 240}});
  const lines = (s.headline || '').split('\n');
  let inside = false;  // [여러 단어] 처럼 대괄호가 여러 단어에 걸쳐도 전부 강조한다
  const words = (s.words || '').split(' ').filter(Boolean).map((w) => {
    const hl = inside || w.includes('[');
    if (w.includes('[')) inside = true;
    if (w.includes(']')) inside = false;
    return {text: w.replace(/[\[\]]/g, ''), hl};
  });
  return (
    <AbsoluteFill style={{backgroundColor: '#060814'}}>
      {s.clip ? (
        <AbsoluteFill style={{transform: `scale(${snap})`}}>
          <OffthreadVideo src={staticFile(s.clip)} muted
            style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill>
        <Img src={staticFile(s.bg)} style={{width: '100%', height: '100%'}} />
      </AbsoluteFill>
      {s.headline ? (
        <div style={{
          position: 'absolute', left: 50, right: 50, top: 200, textAlign: 'center', fontFamily: FONT,
          color: '#FFE812', fontWeight: 900, fontSize: 132, lineHeight: 1.12, textShadow: STROKE,
          transform: `scale(${0.5 + 0.5 * head})`, opacity: Math.min(1, head * 2), wordBreak: 'keep-all',
        }}>
          {lines.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      ) : null}
      <div style={{
        position: 'absolute', left: 80, right: 80, bottom: 440, display: 'flex', flexWrap: 'wrap',
        justifyContent: 'center', alignItems: 'center', gap: '10px 18px', fontFamily: FONT, lineHeight: 1.25,
      }}>
        {words.map((w, i) => {
          const spr = spring({frame: frame - 2 - i * 2.5, fps, config: {damping: 12, mass: 0.6, stiffness: 180}});
          const scale = interpolate(spr, [0, 1], [0.3, w.hl ? 1.14 : 1]);
          return (
            <span key={i} style={{
              display: 'inline-block', fontWeight: 900, fontSize: 74, color: w.hl ? '#FFE812' : '#fff',
              opacity: Math.min(1, spr * 2.5), textShadow: STROKE, transformOrigin: 'center bottom',
              transform: `scale(${scale}) rotate(${w.hl ? interpolate(spr, [0, 1], [-12, -3]) : 0}deg)`,
            }}>{w.text}</span>
          );
        })}
      </div>
      <Audio src={staticFile(s.audio)} />
    </AbsoluteFill>
  );
};

const SceneView: React.FC<{s: Scene; index: number}> = ({s, index}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fadeIn = s.cont ? 1 : interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});
  const zoom = interpolate(frame, [0, s.frames], index % 2 === 0 ? [1, 1.06] : [1.06, 1]);
  const head = s.cont ? 1 : spring({frame: frame - 2, fps, config: {damping: 14, stiffness: 160}});
  const pop = spring({frame: frame - 1, fps, config: {damping: 11, stiffness: 220}});
  const cap = spring({frame: frame - 8, fps, config: {damping: 12, stiffness: 180}});
  const lines = (s.headline || '').split('\n');
  return (
    <AbsoluteFill style={{backgroundColor: '#060814', opacity: fadeIn}}>
      {s.clip ? (
        <AbsoluteFill>
          <OffthreadVideo src={staticFile(s.clip)} muted
            style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={{transform: s.clip ? undefined : `scale(${zoom})`}}>
        <Img src={staticFile(s.bg)} style={{width: '100%', height: '100%'}} />
      </AbsoluteFill>
      <div style={{position: 'absolute', left: 70, right: 70, top: s.top ?? 1080, fontFamily: FONT}}>
        {s.headline ? (
          <div style={{
            color: '#fff', fontWeight: 900, fontSize: 86, lineHeight: 1.18,
            textShadow: '0 4px 18px rgba(0,0,0,0.55)',
            transform: `translateY(${(1 - head) * 60}px)`, opacity: head,
          }}>
            {lines.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        ) : null}
        {s.caption ? (
          <div style={{display: 'flex', justifyContent: 'center', marginTop: 40}}>
            <div style={{
              background: '#fff', color: '#10121e', fontWeight: 900, fontSize: 54,
              borderRadius: 28, padding: '20px 40px', maxWidth: 920, textAlign: 'center',
              transform: `scale(${0.6 + 0.4 * cap})`, opacity: cap,
              boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
            }}>{s.caption}</div>
          </div>
        ) : null}
        {s.bubble ? (
          <div style={{display: 'flex', flexDirection: 'column',
            alignItems: s.bubble.right ? 'flex-end' : 'flex-start', marginTop: 40}}>
            {!s.bubble.right ? (
              <div style={{color: '#fff', fontWeight: 700, fontSize: 36, marginLeft: 8, marginBottom: 8,
                textShadow: '0 2px 6px rgba(0,0,0,0.8)'}}>{s.bubble.who}</div>
            ) : null}
            <div style={{
              background: s.bubble.right ? '#fee500' : '#fff', color: '#191919', fontWeight: 700, fontSize: 54,
              lineHeight: 1.35, borderRadius: 34, padding: '22px 36px', maxWidth: 820,
              transform: `scale(${0.6 + 0.4 * pop})`, opacity: pop,
              transformOrigin: s.bubble.right ? 'right center' : 'left center',
              boxShadow: '0 8px 30px rgba(0,0,0,0.35)', wordBreak: 'keep-all',
            }}>{s.bubble.text}</div>
          </div>
        ) : null}
      </div>
      <Audio src={staticFile(s.audio)} />
    </AbsoluteFill>
  );
};

export const Short: React.FC<ShortProps> = ({scenes}) => (
  <AbsoluteFill style={{backgroundColor: '#060814'}}>
    <Series>
      {scenes.map((s, i) => (
        <Series.Sequence key={i} durationInFrames={s.frames}>
          {s.punch ? <PunchView s={s} /> : <SceneView s={s} index={i} />}
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
