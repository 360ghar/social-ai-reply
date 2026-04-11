import { cn } from "@/lib/utils";
import { MessageCircle } from "lucide-react";

interface PlatformIconProps {
  platform: string;
  className?: string;
}

/** Reddit SVG logo */
function RedditLogo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.843.07 3.51.646 4.662 1.534a1.58 1.58 0 0 1 1.063-.413c.883 0 1.598.715 1.598 1.598 0 .65-.39 1.206-.948 1.451a3.3 3.3 0 0 1 .043.551c0 2.79-3.27 5.062-7.31 5.062-4.037 0-7.308-2.272-7.308-5.062 0-.183.015-.366.043-.547A1.748 1.748 0 0 1 3.45 11.65c0-.883.716-1.598 1.598-1.598.396 0 .753.147 1.031.39a8.9 8.9 0 0 1 4.72-1.535l.876-4.089a.346.346 0 0 1 .14-.208.346.346 0 0 1 .246-.041l2.907.637a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.608.608 1.806.649 2.147.649.342 0 1.536-.04 2.147-.649a.33.33 0 0 0 0-.463.33.33 0 0 0-.462 0c-.39.39-1.195.497-1.685.497-.49 0-1.296-.107-1.685-.497a.326.326 0 0 0-.231-.094z" />
    </svg>
  );
}

const ICON_MAP: Record<string, { icon: React.ElementType; color: string }> = {
  reddit: { icon: RedditLogo, color: "text-orange-500" },
  quora: { icon: MessageCircle, color: "text-red-500" },
  facebook: { icon: MessageCircle, color: "text-blue-600" },
  default: { icon: MessageCircle, color: "text-muted-foreground" },
};

export function PlatformIcon({ platform, className }: PlatformIconProps) {
  const normalizedPlatform = platform.trim().toLowerCase();
  const { icon: Icon, color } = ICON_MAP[normalizedPlatform] ?? ICON_MAP.default;
  return (
    <span role="img" aria-label={normalizedPlatform} className={cn("inline-flex", color, className)}>
      <Icon className="h-4 w-4" />
    </span>
  );
}
