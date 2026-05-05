import {
  Children,
  cloneElement,
  isValidElement,
  useId,
  type AriaAttributes,
  type ReactElement,
  type ReactNode
} from "react";
import { cn } from "@/lib/utils";

export type TooltipSide = "top" | "right" | "bottom" | "left";

const sideClasses: Record<TooltipSide, string> = {
  top: "left-1/2 bottom-full mb-2 -translate-x-1/2",
  right: "top-1/2 left-full ml-2 -translate-y-1/2",
  bottom: "left-1/2 top-full mt-2 -translate-x-1/2",
  left: "top-1/2 right-full mr-2 -translate-y-1/2"
};

export type TooltipProps = {
  label: ReactNode;
  side?: TooltipSide;
  children: ReactNode;
  className?: string;
};

export function Tooltip({
  label,
  side = "top",
  children,
  className
}: TooltipProps) {
  const id = useId();
  // If the child is a single element, link aria-describedby to it so the
  // tooltip is announced when the trigger receives keyboard focus. Otherwise
  // fall back to applying it on the wrapper so screen readers that traverse
  // ancestors can still find it.
  const onlyChild = Children.toArray(children).find(isValidElement) as
    | ReactElement<AriaAttributes>
    | undefined;
  const trigger = onlyChild
    ? cloneElement(onlyChild, { "aria-describedby": id })
    : children;
  return (
    <span
      className={cn("group/tooltip relative inline-flex", className)}
      aria-describedby={onlyChild ? undefined : id}
    >
      {trigger}
      <span
        id={id}
        role="tooltip"
        className={cn(
          "pointer-events-none absolute z-50 whitespace-nowrap rounded-md border border-border bg-surface px-2 py-1 text-xs text-foreground shadow-md opacity-0 transition group-hover/tooltip:opacity-100 group-focus-within/tooltip:opacity-100",
          sideClasses[side]
        )}
      >
        {label}
      </span>
    </span>
  );
}
