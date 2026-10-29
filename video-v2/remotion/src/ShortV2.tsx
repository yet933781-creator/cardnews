import React from 'react';
import {AbsoluteFill, Audio, Img, Series, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {CameraMotion} from './components/CameraMotion';
import {OverlayView} from './components/Graphics';
import {ReadabilityShade, SubtitleOverlay, TopBar} from './components/Chrome';
import {parallaxForeground} from './camera';
import {HoneyHeader, HoneyHook, HoneyShade, HoneySubs, HoneyVisual} from './components/Honey';
import type {SceneV2, ShortV2Props} from './types';

const FADE = 7; // 장면 시작 시 짧은 페이드 + 살짝 올라오는 전환

// 꿀템 쇼츠식 장면: 꽉 찬 화면 + 빠른 컷 + 말자막 + 위 고정 제목
const HoneyScene: React.FC<{s: SceneV2; index: number; p: ShortV2Props}> = ({s, index, p}) => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 4], [0.5, 1], {extrapolateRight: 'clamp'});
  const keep = s.overlay && (s.overlay.type === 'cta' || s.overlay.type === 'number');
  return (
    <AbsoluteFill style={{backgroundColor: '#000', opacity: fade}}>
      {s.owner && s.image ? (
        <AbsoluteFill style={{background: 'linear-gradient(#141a36, #060814)'}}>
          <Img src={staticFile(s.image)} style={{position: 'absolute', top: 170, width: '100%'}} />
        </AbsoluteFill>
      ) : (
        <HoneyVisual s={s} demo={p.style === 'demo'} />
      )}
      <HoneyShade />
      {keep && s.overlay ? <OverlayView o={s.overlay} accent={p.accent} frames={s.frames} /> : null}
      {index === 0 && p.style !== 'demo' ? <HoneyHook text={s.headline} accent={p.accent} /> : null}
      {index > 0 || p.style === 'demo' ? <HoneyHeader text={p.header} small={p.style === 'demo'} /> : null}
      <HoneySubs subs={s.subs} accent={p.accent} top={p.style === 'demo' ? (s.overlay?.type === 'cta' ? 1300 : 600) : 1230} plain={p.style === 'demo'} />
      <TopBar storeTag={p.storeTag} index={index} total={p.scenes.length} accent={p.accent} adLabel={p.adLabel} labels={s.labels} />
      {s.audio ? <Audio src={staticFile(s.audio)} /> : null}
      {s.sfx ? <Audio src={staticFile(s.sfx)} volume={0.35} /> : null}
    </AbsoluteFill>
  );
};

const Scene: React.FC<{s: SceneV2; index: number; p: ShortV2Props}> = ({s, index, p}) => {
  if (p.style === 'honey' || p.style === 'demo') return <HoneyScene s={s} index={index} p={p} />;
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
