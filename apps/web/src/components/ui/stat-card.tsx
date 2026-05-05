import {
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  type LucideIcon
} from "lucide-react";
import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type StatCardTone =
  | "neutral"
  | "primary"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info";

export type StatCardTrend = {
  direction: "up" | "down" | "flat";
  label: string;
};

const toneAccent: Record<StatCardTone, string> = {
  neutral: "bg-border-strong",
  primary: "bg-gradient-brand",
  accent: "bg-accent",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info"
};

const toneIcon: Record<StatCardTone, string> = {
  neutral: "bg-surface-2 text-foreground-muted",
  primary: "bg-primary-soft text-primary-soft-foreground",
  accent: "bg-accent-soft text-accent-soft-foreground",
  success: "bg-success-soft text-success-soft-foreground",
  warning: "bg-warning-soft text-warning-soft-foreground",
  danger: "bg-danger-soft text-danger-soft-foreground",
  info: "bg-info-soft text-info-soft-foreground"
};

const trendIcon = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  flat: Minus
} as const;

const trendTone = {
  up: "bg-success-soft text-success-soft-foreground",
  down: "bg-danger-soft text-danger-soft-foreground",
  flat: "bg-surface-2 text-foreground-muted"
} as const;

export type StatCardProps = HTMLAttributes<HTMLDivElement> & {
  label: string;
  value: number | string;
  description?: string;
  icon?: LucideIcon;
  tone?: StatCardTone;
  trend?: StatCardTrend;
};

export const StatCard = forwardRef<HTMLDivElement, StatCardProps>(
  (
    {
      label,
      value,
      description,
      icon: Icon,
      tone = "neutral",
      trend,
      className,
      ...props
    },
    ref
  ) => {
    const TrendIcon = trend ? trendIcon[trend.direction] : null;
    return (
      <div
        ref={ref}
        className={cn(
          "relative overflow-hidden rounded-card border border-border bg-card p-5 shadow-sm",
          className
        )}
        {...props}
      >
        <div
          aria-hidden
          className={cn("absolute inset-x-0 top-0 h-1", toneAccent[tone])}
        />
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-foreground-muted">
              {label}
            </p>
            <p className="mt-3 font-mono text-3xl font-semibold tabular-nums text-foreground">
              {value}
            </p>
            {description ? (
              <p className="mt-1 text-xs leading-5 text-foreground-muted">
                {description}
              </p>
            ) : null}
          </div>
          {Icon ? (
            <div
              className={cn(
                "flex size-10 shrink-0 items-center justify-center rounded-md",
                toneIcon[tone]
              )}
            >
              <Icon className="size-5" aria-hidden="true" />
            </div>
          ) : null}
        </div>
        {trend && TrendIcon ? (
          <div className="mt-3 inline-flex items-center gap-1">
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium",
                trendTone[trend.direction]
              )}
            >
              <TrendIcon className="size-3" aria-hidden="true" />
              {trend.label}
            </span>
          </div>
        ) : null}
      </div>
    );
  }
);
StatCard.displayName = "StatCard";
