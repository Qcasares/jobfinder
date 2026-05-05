import type { LucideIcon } from "lucide-react";
import { forwardRef, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export type EmptyStateProps = HTMLAttributes<HTMLDivElement> & {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
};

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ icon: Icon, title, description, action, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-card border border-dashed border-border bg-surface-2/50 px-6 py-10 text-center",
          className
        )}
        {...props}
      >
        {Icon ? (
          <div className="flex size-12 items-center justify-center rounded-full bg-surface-2 text-foreground-muted">
            <Icon className="size-6" aria-hidden="true" />
          </div>
        ) : null}
        <p className="text-sm font-semibold text-foreground">{title}</p>
        {description ? (
          <p className="max-w-md text-sm leading-5 text-foreground-muted">
            {description}
          </p>
        ) : null}
        {action ? <div className="mt-1">{action}</div> : null}
      </div>
    );
  }
);
EmptyState.displayName = "EmptyState";
