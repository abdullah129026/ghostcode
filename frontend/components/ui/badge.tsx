import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// Badges name state in one or two words. They are never buttons and never
// the only place a state is explained. Chips use radius-sm per the copy.
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "border-transparent bg-accent-tint text-accent-deep",
        secondary: "border-line bg-surface-2 text-ink-2",
        destructive: "border-transparent bg-clay/10 text-clay",
        warning: "border-transparent bg-amber/10 text-amber",
        outline: "border-line-2 bg-transparent text-ink-2",
        success: "border-transparent bg-accent-soft text-accent-deep",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
