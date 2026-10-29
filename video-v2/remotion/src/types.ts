import type {CameraPreset} from './camera';

export type RGB = [number, number, number];

export type Overlay =
  | {type: 'number'; value: string; label?: string; color?: RGB}
  | {type: 'compare'; title?: string; items: {label: string; value: string; highlight?: boolean}[]; conditions: string}
  | {type: 'checklist'; title?: string; items: string[]}
  | {type: 'timeline'; title?: string; steps: {label: string; when: string}[]; note?: string}
  | {type: 'features'; items: {title: string; desc?: string}[]}
  | {type: 'cta'; number: string; text: string};

export type SceneV2 = {
  frames: number;
  audio?: string;          // 장면 내레이션 (public 기준 경로)
  sfx?: string;            // 장면 시작 효과음
  image?: string;          // 정지 이미지 (사진)
  clip?: string;           // 영상
  productFit?: boolean;    // 상품 원본: 잘리지 않게 전체 표시 + 같은 사진을 흐리게 깐 배경
  camera: CameraPreset;
  focus?: {x: number; y: number};
  overlay?: Overlay;
  headline?: string;
  caption?: string;
  labels: string[];        // 왼쪽 위 표시 (AI 생성 장면, 사진: 제조사 제공 등)
  owner?: boolean;         // 사장님 마무리 장면 (사진 그대로)
  images?: {src: string; camera: CameraPreset}[]; // 한 장면 안에서 빠르게 넘기는 컷 (꿀템 스타일)
  subs?: {text: string; from: number; to: number}[]; // 말하는 대로 바뀌는 자막 (프레임, 장면 기준)
};

export type ShortV2Props = {
  scenes: SceneV2[];
  fps: number;
  storeTag: [string, string];
  adLabel?: string | null;
  accent: RGB;
  style?: 'card' | 'honey'; // honey: 유튜브 꿀템 쇼츠식 (꽉 찬 화면·빠른 컷·말자막·상단 고정 제목)
  header?: string;          // honey: 영상 내내 위에 고정되는 제목
};
