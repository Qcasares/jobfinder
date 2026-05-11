"use client";

import * as ProgressPrimitive from "@radix-ui/react-progress";
import type { ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/utils";

type ProgressProps = ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> & {
  indicatorClassName?: string;
};

export function Progress({
  className,
  indicatorClassName,
  value = 0,
  ...props
}: ProgressProps) {
  const normalizedValue = Math.max(0, Math.min(100, Number(value) || 0));

  return (
    <ProgressPrimitive.Root
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-muted",
        className
      )}
      value={normalizedValue}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className={cn(
          "h-full w-full flex-1 rounded-full bg-primary transition-transform duration-700 ease-out",
          indicatorClassName
        )}
        style={{ transform: `translateX(-${100 - normalizedValue}%)` }}
      />
    </ProgressPrimitive.Root>
  );
}
