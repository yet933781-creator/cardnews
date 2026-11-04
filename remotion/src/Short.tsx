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
};
export type ShortProps = {scenes: Scene[]; fps: number};

const FONT = '"Noto Sans CJK KR", "Noto Sans KR", sans-serif';

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
          <SceneView s={s} index={i} />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
