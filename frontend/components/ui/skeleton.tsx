import { cn } from "@/lib/utils";

// Skeleton blocks match the shape of the content they replace and pulse
// softly. Content swaps in without layout shift.
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-surface-2", className)}
      aria-hidden="true"
      {...props}
    />
  );
}

export { Skeleton };
