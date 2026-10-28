import React from 'react';
import {Composition} from 'remotion';
import {Short, ShortProps} from './Short';

const defaults: ShortProps = {scenes: [], fps: 30};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Short"
    component={Short}
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
