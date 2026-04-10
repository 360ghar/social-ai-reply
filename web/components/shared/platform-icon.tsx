interface PlatformIconProps {
  platform: string;
}

const ICONS: Record<string, string> = {
  reddit: "🟠",
  quora: "🔴",
  facebook: "🔵",
  default: "🌐",
};

export function PlatformIcon({ platform }: PlatformIconProps) {
  return <span title={platform}>{ICONS[platform] ?? ICONS.default}</span>;
}
