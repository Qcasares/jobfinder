import { Loader2 } from "lucide-react";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "destructive"
  | "outline";

export type ButtonSize = "sm" | "md" | "lg" | "icon";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-primary text-primary-foreground hover:bg-primary-hover border border-transparent",
  secondary:
    "bg-surface-2 text-foreground hover:bg-surface-3 border border-border",
  ghost:
    "bg-transparent text-foreground hover:bg-surface-2 border border-transparent",
  destructive:
    "bg-danger text-background hover:opacity-90 border border-transparent",
  outline:
    "bg-transparent text-foreground border border-border hover:bg-surface-2"
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-sm gap-2",
  icon: "h-9 w-9 p-0 gap-0"
};

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      leadingIcon,
      trailingIcon,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;
    return (
      <button
        ref={ref}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        className={cn(
          "inline-flex items-center justify-center rounded-md font-semibold transition focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {loading ? (
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        ) : leadingIcon ? (
          <span className="inline-flex size-4 items-center justify-center" aria-hidden="true">
            {leadingIcon}
          </span>
        ) : null}
        {children}
        {!loading && trailingIcon ? (
          <span className="inline-flex size-4 items-center justify-center" aria-hidden="true">
            {trailingIcon}
          </span>
        ) : null}
      </button>
    );
  }
);
Button.displayName = "Button";
