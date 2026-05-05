"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export type TabItem = {
  value: string;
  label: ReactNode;
  count?: number;
};

export type TabsProps = {
  items: readonly TabItem[];
  value: string;
  onChange: (value: string) => void;
  ariaLabel?: string;
  className?: string;
};

export function Tabs({ items, value, onChange, ariaLabel, className }: TabsProps) {
  const buttonsRef = useRef<Array<HTMLButtonElement | null>>([]);
  const id = useId();

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const currentIndex = items.findIndex((item) => item.value === value);
    if (currentIndex === -1) return;

    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      const next = (currentIndex + 1) % items.length;
      onChange(items[next].value);
      buttonsRef.current[next]?.focus();
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      const prev = (currentIndex - 1 + items.length) % items.length;
      onChange(items[prev].value);
      buttonsRef.current[prev]?.focus();
    } else if (event.key === "Home") {
      event.preventDefault();
      onChange(items[0].value);
      buttonsRef.current[0]?.focus();
    } else if (event.key === "End") {
      event.preventDefault();
      const last = items.length - 1;
      onChange(items[last].value);
      buttonsRef.current[last]?.focus();
    }
  }

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      onKeyDown={handleKeyDown}
      className={cn(
        "inline-flex flex-wrap items-center gap-1 rounded-md border border-border bg-surface-2 p-1",
        className
      )}
    >
      {items.map((item, index) => {
        const isActive = item.value === value;
        return (
          <button
            key={item.value}
            ref={(node) => {
              buttonsRef.current[index] = node;
            }}
            id={`${id}-tab-${item.value}`}
            role="tab"
            type="button"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(item.value)}
            className={cn(
              "inline-flex items-center gap-2 rounded-sm px-3 py-1.5 text-xs font-semibold transition",
              isActive
                ? "bg-card text-foreground shadow-sm"
                : "text-foreground-muted hover:text-foreground"
            )}
          >
            <span>{item.label}</span>
            {typeof item.count === "number" ? (
              <span
                className={cn(
                  "inline-flex min-w-[1.25rem] items-center justify-center rounded-full px-1.5 text-[10px] font-semibold",
                  isActive
                    ? "bg-primary-soft text-primary-soft-foreground"
                    : "bg-surface-3 text-foreground-muted"
                )}
              >
                {item.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
