import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "border-white/10 bg-white/5 text-slate-300",
  success: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
  warning: "border-gold-500/25 bg-gold-500/15 text-gold-200",
  danger: "border-red-400/25 bg-red-500/10 text-red-200",
  info: "border-cyan-300/25 bg-cyan-300/10 text-cyan-100"
};

export function Badge({
  className,
  tone = "neutral",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex min-h-6 items-center rounded-md border px-2 py-0.5 text-xs font-medium shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}
