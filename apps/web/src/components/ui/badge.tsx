import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type BadgeTone =
  | "neutral"
  | "primary"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info";

export type BadgeVariant = "soft" | "solid" | "outline";

export type BadgeSize = "sm" | "md";

const softToneClasses: Record<BadgeTone, string> = {
  neutral:
    "border-transparent bg-surface-2 text-foreground-muted",
  primary:
    "border-transparent bg-primary-soft text-primary-soft-foreground",
  accent:
    "border-transparent bg-accent-soft text-accent-soft-foreground",
  success:
    "border-transparent bg-success-soft text-success-soft-foreground",
  warning:
    "border-transparent bg-warning-soft text-warning-soft-foreground",
  danger:
    "border-transparent bg-danger-soft text-danger-soft-foreground",
  info: "border-transparent bg-info-soft text-info-soft-foreground"
};

const solidToneClasses: Record<BadgeTone, string> = {
  neutral: "border-transparent bg-foreground-muted text-background",
  primary: "border-transparent bg-primary text-primary-foreground",
  accent: "border-transparent bg-accent text-background",
  success: "border-transparent bg-success text-background",
  warning: "border-transparent bg-warning text-background",
  danger: "border-transparent bg-danger text-background",
  info: "border-transparent bg-info text-background"
};

const outlineToneClasses: Record<BadgeTone, string> = {
  neutral: "border-border bg-transparent text-foreground-muted",
  primary: "border-primary bg-transparent text-primary",
  accent: "border-accent bg-transparent text-accent",
  success: "border-success bg-transparent text-success",
  warning: "border-warning bg-transparent text-warning",
  danger: "border-danger bg-transparent text-danger",
  info: "border-info bg-transparent text-info"
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "min-h-5 px-1.5 py-0 text-[11px]",
  md: "min-h-6 px-2 py-0.5 text-xs"
};

function toneClassesFor(tone: BadgeTone, variant: BadgeVariant) {
  if (variant === "solid") return solidToneClasses[tone];
  if (variant === "outline") return outlineToneClasses[tone];
  return softToneClasses[tone];
}

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
  variant?: BadgeVariant;
  size?: BadgeSize;
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, tone = "neutral", variant = "soft", size = "md", ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1 rounded-md border font-medium",
          sizeClasses[size],
          toneClassesFor(tone, variant),
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";
