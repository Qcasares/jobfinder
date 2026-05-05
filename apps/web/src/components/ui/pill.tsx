import { forwardRef, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export type PillTone =
  | "neutral"
  | "primary"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info";

const toneClasses: Record<PillTone, string> = {
  neutral: "bg-surface-2 text-foreground-muted",
  primary: "bg-primary-soft text-primary-soft-foreground",
  accent: "bg-accent-soft text-accent-soft-foreground",
  success: "bg-success-soft text-success-soft-foreground",
  warning: "bg-warning-soft text-warning-soft-foreground",
  danger: "bg-danger-soft text-danger-soft-foreground",
  info: "bg-info-soft text-info-soft-foreground"
};

const dotClasses: Record<PillTone, string> = {
  neutral: "bg-foreground-muted",
  primary: "bg-primary",
  accent: "bg-accent",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info"
};

export type PillProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: PillTone;
  pulse?: boolean;
  withDot?: boolean;
  children?: ReactNode;
};

export const Pill = forwardRef<HTMLSpanElement, PillProps>(
  (
    {
      className,
      tone = "neutral",
      pulse = false,
      withDot = true,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
          toneClasses[tone],
          className
        )}
        {...props}
      >
        {withDot ? (
          <span className="relative inline-flex size-1.5" aria-hidden="true">
            {pulse ? (
              <span
                className={cn(
                  "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
                  dotClasses[tone]
                )}
              />
            ) : null}
            <span
              className={cn(
                "relative inline-flex size-1.5 rounded-full",
                dotClasses[tone]
              )}
            />
          </span>
        ) : null}
        <span>{children}</span>
      </span>
    );
  }
);
Pill.displayName = "Pill";
