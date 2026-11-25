import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// Living Design Copy, buttons page: four variants, every state defined.
// Primary lifts 1px and gains shadow-md on hover, focus is a 2px ring
// offset 2px, pressed scales to 0.98 for 120ms, loading swaps the icon
// for a spinner and never changes the button width.
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-on-accent shadow-sm hover:bg-accent-deep hover:-translate-y-px hover:shadow-md",
        secondary:
          "bg-surface text-ink border border-line-2 hover:border-ink hover:shadow-sm",
        ghost: "text-ink hover:bg-accent-soft hover:text-accent-deep",
        destructive:
          "bg-clay text-on-danger shadow-sm hover:opacity-90 hover:-translate-y-px hover:shadow-md",
        outline:
          "border border-line-2 bg-transparent text-ink hover:bg-surface-2",
        link: "text-accent-deep underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-[13px]",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant, size, asChild = false, loading = false, children, disabled, ...props },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        {children}
      </Comp>
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
