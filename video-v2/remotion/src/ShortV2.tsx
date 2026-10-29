import React from 'react';
import {AbsoluteFill, Audio, Img, Series, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {CameraMotion} from './components/CameraMotion';
import {OverlayView} from './components/Graphics';
import {ReadabilityShade, SubtitleOverlay, TopBar} from './components/Chrome';
import {parallaxForeground} from './camera';
import type {SceneV2, ShortV2Props} from './types';

const FADE = 7; // 장면 시작 시 짧은 페이드 + 살짝 올라오는 전환

const Scene: React.FC<{s: SceneV2; index: number; p: ShortV2Props}> = ({s, index, p}) => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, FADE], [0, 1], {extrapolateRight: 'clamp'});
  const lift = interpolate(frame, [0, FADE + 3], [26, 0], {extrapolateRight: 'clamp'});
  const fg = s.camera === 'parallax_2d' ? parallaxForeground(s.frames > 1 ? frame / (s.frames - 1) : 0) : 0;
  return (
    <AbsoluteFill style={{backgroundColor: '#060814', opacity: fade}}>
      {s.owner && s.image ? (
        <AbsoluteFill style={{background: 'linear-gradient(#141a36, #060814)'}}>
          <Img src={staticFile(s.image)} style={{position: 'absolute', top: 170, width: '100%'}} />
        </AbsoluteFill>
      ) : (
        <CameraMotion image={s.image} clip={s.clip} preset={s.camera} frames={s.frames} focus={s.focus} productFit={s.productFit} />
      )}
      <ReadabilityShade />
      <AbsoluteFill style={{transform: `translate(${fg}px, ${lift}px)`}}>
        {s.overlay ? <OverlayView o={s.overlay} accent={p.accent} frames={s.frames} lower={s.productFit} /> : null}
        <SubtitleOverlay headline={s.headline} caption={s.caption} top={s.owner ? 1190 : 1080} />
      </AbsoluteFill>
      <TopBar storeTag={p.storeTag} index={index} total={p.scenes.length} accent={p.accent} adLabel={p.adLabel} labels={s.labels} />
      {s.audio ? <Audio src={staticFile(s.audio)} /> : null}
      {s.sfx ? <Audio src={staticFile(s.sfx)} volume={0.35} /> : null}
    </AbsoluteFill>
  );
};

export const ShortV2: React.FC<ShortV2Props> = (p) => (
  <AbsoluteFill style={{backgroundColor: '#060814'}}>
    <Series>
      {p.scenes.map((s, i) => (
        <Series.Sequence key={i} durationInFrames={s.frames}>
          <Scene s={s} index={i} p={p} />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
