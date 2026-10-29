import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import {CameraPreset, cameraTransform, toCss} from '../camera';

// 사진·영상에 가상 카메라 움직임을 준다. 이동·확대만 (회전·변형 없음).
// productFit: 상품 원본은 잘리지 않게 전체를 보여주고, 빈 곳은 같은 사진을 흐리게 깔아 채운다(AI 합성 아님).
export const CameraMotion: React.FC<{
  image?: string;
  clip?: string;
  preset: CameraPreset;
  frames: number;
  focus?: {x: number; y: number};
  productFit?: boolean;
}> = ({image, clip, preset, frames, focus, productFit}) => {
  const frame = useCurrentFrame();
  const tr = cameraTransform(preset, frames > 1 ? frame / (frames - 1) : 0, focus);
  const moving: React.CSSProperties = {transform: toCss(tr), transformOrigin: '50% 50%'};
  if (clip) {
    return (
      <AbsoluteFill style={moving}>
        <OffthreadVideo src={staticFile(clip)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </AbsoluteFill>
    );
  }
  if (!image) return null;
  const src = staticFile(image);
  if (productFit) {
    return (
      <AbsoluteFill>
        <AbsoluteFill style={{transform: 'scale(1.15)'}}>
          <Img src={src} style={{width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(38px) brightness(0.55)'}} />
        </AbsoluteFill>
        <AbsoluteFill style={moving}>
          <div style={{position: 'absolute', top: 240, height: 800, left: 70, right: 70}}>
            <Img src={src} style={{width: '100%', height: '100%', objectFit: 'contain',
              filter: 'drop-shadow(0 18px 40px rgba(0,0,0,0.45))'}} />
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={moving}>
      <Img src={src} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </AbsoluteFill>
  );
};
