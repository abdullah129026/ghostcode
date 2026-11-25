import * as React from "react";
import { cn } from "@/lib/utils";

// One geometry for every control: 40px tall, radius-md, 1.5px border on
// focus in accent, label 4px above, error text 4px below. Errors are
// carried by aria-invalid plus a visible message from the form, never by
// color alone.
const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-clay aria-[invalid=true]:focus:border-clay aria-[invalid=true]:focus:ring-clay",
        className,
      )}
      ref={ref}
      {...props}
    />
  );
});
Input.displayName = "Input";

export { Input };
