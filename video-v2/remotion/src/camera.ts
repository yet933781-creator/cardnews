// 가상 카메라 계산 (React·Remotion 없이 순수 함수 → 단위 테스트 가능)
// 규칙: 화면 밖 검은 여백이 생기지 않도록 이동량은 항상 (배율-1)/2 이내로 제한한다.
//       회전·비선형 변형 없음(상품 원본 보존). 한 장면에 한 방향으로만 천천히 움직인다.

export type CameraPreset =
  | 'slow_zoom_in'
  | 'slow_zoom_out'
  | 'pan_left'
  | 'pan_right'
  | 'push_in'
  | 'parallax_2d'
  | 'static';

export const PRESETS: CameraPreset[] = [
  'slow_zoom_in', 'slow_zoom_out', 'pan_left', 'pan_right', 'push_in', 'parallax_2d', 'static',
];

export type Transform = {scale: number; tx: number; ty: number}; // tx, ty: 화면 폭·높이 대비 비율(-0.5~0.5)

// 부드러운 가감속 (Remotion Easing.inOut(Easing.cubic) 과 같은 곡선)
export const easeInOutCubic = (t: number): number =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

const clamp01 = (t: number) => Math.min(1, Math.max(0, t));

// 검은 여백이 생기지 않는 최대 이동량
export const maxShift = (scale: number): number => Math.max(0, (scale - 1) / 2);

const limit = (v: number, scale: number) => {
  const m = maxShift(scale);
  return Math.min(m, Math.max(-m, v));
};

/**
 * @param preset 카메라 프리셋
 * @param progress 장면 진행률 0~1
 * @param focus push_in 의 중심(0~1, 기본 화면 중앙). 상품·얼굴 쪽으로 다가갈 때 사용
 */
export function cameraTransform(
  preset: CameraPreset,
  progress: number,
  focus: {x: number; y: number} = {x: 0.5, y: 0.5},
): Transform {
  const t = easeInOutCubic(clamp01(progress));
  let scale = 1;
  let tx = 0;
  let ty = 0;
  switch (preset) {
    case 'slow_zoom_in':
      scale = 1 + 0.12 * t;
      break;
    case 'slow_zoom_out':
      scale = 1.12 - 0.12 * t;
      break;
    case 'pan_left': // 화면이 왼쪽으로 흐르듯 (내용이 왼쪽으로 이동)
      scale = 1.12;
      tx = maxShift(scale) * (1 - 2 * t);
      break;
    case 'pan_right':
      scale = 1.12;
      tx = -maxShift(scale) * (1 - 2 * t);
      break;
    case 'push_in': {
      scale = 1 + 0.18 * t;
      // 초점이 화면 중앙으로 오도록 이동 (여백 제한 안에서)
      tx = (0.5 - focus.x) * (scale - 1);
      ty = (0.5 - focus.y) * (scale - 1);
      break;
    }
    case 'parallax_2d': // 배경 레이어 기준. 전경은 parallaxForeground 사용
      scale = 1.1;
      tx = maxShift(scale) * 0.8 * (1 - 2 * t);
      break;
    case 'static':
    default:
      break;
  }
  return {scale, tx: limit(tx, scale), ty: limit(ty, scale)};
}

// parallax_2d 전경(글자·그래픽) 레이어: 배경과 반대 방향으로 아주 조금 (px)
export function parallaxForeground(progress: number, amountPx = 24): number {
  const t = easeInOutCubic(clamp01(progress));
  return -amountPx * (1 - 2 * t);
}

// CSS transform 문자열 (가운데 기준)
export function toCss(tr: Transform): string {
  return `translate(${(tr.tx * 100).toFixed(3)}%, ${(tr.ty * 100).toFixed(3)}%) scale(${tr.scale.toFixed(4)})`;
}

// 장면 순서대로 프리셋을 고를 때 같은 움직임이 연속되지 않게
export function autoPreset(index: number, isVideo: boolean): CameraPreset {
  if (isVideo) return 'static';
  const cycle: CameraPreset[] = ['slow_zoom_in', 'pan_left', 'slow_zoom_out', 'pan_right', 'push_in'];
  return cycle[index % cycle.length];
}
