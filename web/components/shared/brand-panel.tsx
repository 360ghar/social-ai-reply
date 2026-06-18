import Link from "next/link";

export function BrandPanel() {
  return (
    <div className="hidden md:flex md:w-1/2 flex-col items-center justify-center bg-gradient-to-br from-primary/90 to-primary p-12 text-center relative overflow-hidden">
      <Link href="/" className="mb-4 text-2xl font-bold text-primary-foreground">
        RedditFlow
      </Link>
      <p className="max-w-xs text-base leading-relaxed text-primary-foreground/80">
        Find your audience. Engage authentically. Grow on Reddit.
      </p>
      <div className="pointer-events-none absolute bottom-0 left-0 h-64 w-64 rounded-full bg-primary-foreground/5 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-0 h-48 w-48 rounded-full bg-primary-foreground/5 blur-3xl" />
    </div>
  );
}
