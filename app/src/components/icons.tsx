import Svg, { Circle, Path, Rect } from "react-native-svg";

// Traced from the inline SVGs in docs/prototype/Receptenapp.dc.html. Stroke weight, caps and joins
// are the prototype's — they are what make the set look like one family.

type IconProps = {
  color: string;
  size?: number;
};

const STROKE = 1.7;

function Frame({ size = 24, color, children }: IconProps & { children: React.ReactNode }) {
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={STROKE}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </Svg>
  );
}

export function CompassIcon(props: IconProps) {
  return (
    <Frame {...props}>
      <Circle cx={12} cy={12} r={9} />
      <Path d="M15.2 8.8l-2 4.4-4.4 2 2-4.4z" />
    </Frame>
  );
}

export function BooksIcon(props: IconProps) {
  return (
    <Frame {...props}>
      <Path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H10a2 2 0 0 1 2 2v13a1.6 1.6 0 0 0-1.6-1.6H5.5A1.5 1.5 0 0 1 4 15.9z" />
      <Path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H14a2 2 0 0 0-2 2v13a1.6 1.6 0 0 1 1.6-1.6h4.9A1.5 1.5 0 0 0 20 15.9z" />
    </Frame>
  );
}

export function CalendarIcon(props: IconProps) {
  return (
    <Frame {...props}>
      <Rect x={3.5} y={5} width={17} height={15} rx={2.5} />
      <Path d="M3.5 9.5h17M8 5V3.2M16 5V3.2" />
      <Circle cx={8.5} cy={13.5} r={1} />
      <Circle cx={12} cy={13.5} r={1} />
      <Circle cx={15.5} cy={13.5} r={1} />
    </Frame>
  );
}

export function PersonIcon(props: IconProps) {
  return (
    <Frame {...props}>
      <Circle cx={12} cy={8.5} r={3.6} />
      <Path d="M4.8 20c.6-3.6 3.6-5.6 7.2-5.6s6.6 2 7.2 5.6" />
    </Frame>
  );
}

export function ChevronLeftIcon({ color, size = 20 }: IconProps) {
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Path d="M15 5l-7 7 7 7" />
    </Svg>
  );
}
