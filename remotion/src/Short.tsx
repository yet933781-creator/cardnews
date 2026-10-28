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
};
export type ShortProps = {scenes: Scene[]; fps: number};

const FONT = '"Noto Sans CJK KR", "Noto Sans KR", sans-serif';

const SceneView: React.FC<{s: Scene; index: number}> = ({s, index}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fadeIn = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});
  const zoom = interpolate(frame, [0, s.frames], index % 2 === 0 ? [1, 1.06] : [1.06, 1]);
  const head = spring({frame: frame - 2, fps, config: {damping: 14, stiffness: 160}});
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
      <div style={{position: 'absolute', left: 70, right: 70, top: 1190, fontFamily: FONT}}>
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
