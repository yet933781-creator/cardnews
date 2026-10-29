import React from 'react';
import {Composition} from 'remotion';
import {ShortV2} from './ShortV2';
import type {ShortV2Props} from './types';

const defaults: ShortV2Props = {scenes: [], fps: 30, storeTag: ['방학', '폰 성지'], adLabel: null, accent: [255, 212, 56]};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ShortV2"
    component={ShortV2}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={30}
    defaultProps={defaults}
    calculateMetadata={({props}) => ({
      durationInFrames: Math.max(1, props.scenes.reduce((a, s) => a + s.frames, 0)),
      fps: props.fps,
    })}
  />
);
