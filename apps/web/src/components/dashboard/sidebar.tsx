"use client";

import {
  BriefcaseBusiness,
  ClipboardCheck,
  DatabaseZap,
  FileUser,
  Gauge,
  ListChecks,
  Monitor,
  Moon,
  ScrollText,
  Search,
  ServerCog,
  ShieldCheck,
  Sun,
  X,
  type LucideIcon
} from "lucide-react";
import { useEffect, useState } from "react";
import { Pill, type PillTone } from "@/components/ui/pill";
import type { ApiHealthStatus } from "@/lib/health";
import { cn } from "@/lib/utils";

export type DashboardView =
  | "job-overview"
  | "profile"
  | "jobs"
  | "applications"
  | "reviews-needed"
  | "admin-sources"
  | "admin-approvals"
  | "admin-audit"
  | "admin-system";

export type NavigationArea = "job-search" | "administration";

export const navigationAreas = [
  {
    label: "Job Search",
    value: "job-search",
    icon: Search,
    description: "Synthetic matches, profile evidence, and applications."
  },
  {
    label: "Administration",
    value: "administration",
    icon: ShieldCheck,
    description: "Source policy, approvals, audit, and runtime gates."
  }
] satisfies Array<{
  label: string;
  value: NavigationArea;
  icon: LucideIcon;
  description: string;
}>;

type NavItem = {
  label: string;
  icon: LucideIcon;
  view: DashboardView;
  badgeKey?: "reviews" | "approvals";
};

export const navItems = {
  "job-search": [
    { label: "Overview", icon: Gauge, view: "job-overview" },
    { label: "Profile", icon: FileUser, view: "profile" },
    { label: "Jobs", icon: BriefcaseBusiness, view: "jobs" },
    { label: "Applications", icon: ListChecks, view: "applications" },
    {
      label: "Reviews Needed",
      icon: ClipboardCheck,
      view: "reviews-needed",
      badgeKey: "reviews"
    }
  ],
  administration: [
    { label: "Sources", icon: DatabaseZap, view: "admin-sources" },
    {
      label: "Approvals",
      icon: ClipboardCheck,
      view: "admin-approvals",
      badgeKey: "approvals"
    },
    { label: "Audit Log", icon: ScrollText, view: "admin-audit" },
    { label: "System Status", icon: ServerCog, view: "admin-system" }
  ]
} satisfies Record<NavigationArea, ReadonlyArray<NavItem>>;

function healthTone(state: ApiHealthStatus["state"]): PillTone {
  if (state === "healthy") return "success";
  if (state === "unconfigured") return "warning";
  return "danger";
}

export type SidebarProps = {
  activeArea: NavigationArea;
  activeView: DashboardView;
  onSelectArea: (area: NavigationArea) => void;
  onSelectView: (view: DashboardView) => void;
  pendingApprovalCount: number;
  reviewsNeededCount: number;
  health: ApiHealthStatus;
  chainValid: boolean;
  open: boolean;
  onClose: () => void;
};

export function Sidebar({
  activeArea,
  activeView,
  onSelectArea,
  onSelectView,
  pendingApprovalCount,
  reviewsNeededCount,
  health,
  chainValid,
  open,
  onClose
}: SidebarProps) {
  const items = navItems[activeArea];
  const tone = healthTone(health.state);

  return (
    <>
      {/* Mobile backdrop */}
      <div
        aria-hidden={!open}
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-30 bg-black/40 backdrop-blur-sm transition-opacity lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0"
        )}
      />
      <aside
        aria-label="Primary navigation"
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-[280px] flex-col gap-5 overflow-y-auto border-r border-border bg-surface px-4 py-5 transition-transform lg:static lg:z-auto lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-md bg-gradient-brand text-white shadow-sm">
              <ShieldCheck className="size-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight">Jobfinder</p>
              <p className="text-xs text-foreground-muted">Operations</p>
            </div>
          </div>
          <button
            type="button"
            aria-label="Close navigation"
            onClick={onClose}
            className="inline-flex size-8 items-center justify-center rounded-md text-foreground-muted hover:bg-surface-2 hover:text-foreground lg:hidden"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>

        <div
          role="tablist"
          aria-label="Workspace area"
          className="grid grid-cols-2 gap-1 rounded-md border border-border bg-surface-2 p-1"
        >
          {navigationAreas.map((area) => {
            const Icon = area.icon;
            const isActive = area.value === activeArea;
            return (
              <button
                key={area.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => onSelectArea(area.value)}
                className={cn(
                  "inline-flex items-center justify-center gap-1.5 rounded-sm px-2 py-1.5 text-xs font-semibold transition",
                  isActive
                    ? "bg-card text-foreground shadow-sm"
                    : "text-foreground-muted hover:text-foreground"
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" />
                <span className="truncate">{area.label}</span>
              </button>
            );
          })}
        </div>

        <nav
          aria-label={`${navigationAreas.find((a) => a.value === activeArea)?.label ?? "Workspace"} navigation`}
          className="grid gap-0.5"
        >
          <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-foreground-subtle">
            {navigationAreas.find((a) => a.value === activeArea)?.label}
          </p>
          {items.map((item) => {
            const Icon = item.icon;
            const isActive = item.view === activeView;
            const badgeCount =
              item.badgeKey === "reviews"
                ? reviewsNeededCount
                : item.badgeKey === "approvals"
                  ? pendingApprovalCount
                  : null;
            const showBadge = typeof badgeCount === "number" && badgeCount > 0;

            return (
              <button
                key={item.label}
                type="button"
                aria-current={isActive ? "page" : undefined}
                onClick={() => onSelectView(item.view)}
                className={cn(
                  "relative flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm font-medium transition",
                  isActive
                    ? "bg-surface-2 text-foreground"
                    : "text-foreground-muted hover:bg-surface-2 hover:text-foreground"
                )}
              >
                {isActive ? (
                  <span
                    aria-hidden
                    className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-primary"
                  />
                ) : null}
                <Icon className="size-4 shrink-0" aria-hidden="true" />
                <span className="flex-1 truncate">{item.label}</span>
                {showBadge ? (
                  <span
                    className={cn(
                      "inline-flex min-w-[1.25rem] items-center justify-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                      item.badgeKey === "reviews"
                        ? "bg-warning-soft text-warning-soft-foreground"
                        : "bg-info-soft text-info-soft-foreground"
                    )}
                    aria-label={`${badgeCount} pending`}
                  >
                    {badgeCount}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        <div className="mt-auto grid gap-3 border-t border-border pt-4">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-medium text-foreground-muted">API</span>
            <Pill tone={tone} pulse={tone !== "success"}>
              {health.state}
            </Pill>
          </div>
          <div className="rounded-md border border-border bg-surface-2 p-3 text-xs leading-5">
            <div className="flex items-center gap-2">
              <ShieldCheck
                className="size-4 text-accent"
                aria-hidden="true"
              />
              <p className="font-semibold text-foreground">Safe local mode</p>
            </div>
            <p className="mt-1 text-foreground-muted">
              No crawling, LLM calls, automation, autofill, or submissions.
            </p>
            <div className="mt-2 flex items-center justify-between text-[11px]">
              <span className="text-foreground-muted">Audit chain</span>
              <Pill tone={chainValid ? "success" : "danger"} withDot>
                {chainValid ? "valid" : "invalid"}
              </Pill>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </aside>
    </>
  );
}

type ThemeMode = "light" | "dark" | "system";

const THEME_KEY = "jf-theme";

function applyTheme(mode: ThemeMode) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  if (mode === "light") {
    root.classList.add("light");
  } else if (mode === "dark") {
    root.classList.add("dark");
  }
}

export function ThemeToggle() {
  const [mode, setMode] = useState<ThemeMode>("system");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(THEME_KEY) as ThemeMode | null;
      const initial: ThemeMode =
        stored === "light" || stored === "dark" || stored === "system"
          ? stored
          : "system";
      applyTheme(initial);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMode(initial);
    } catch {
      // ignore storage errors
    }
  }, []);

  function selectMode(next: ThemeMode) {
    setMode(next);
    try {
      window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // ignore storage errors
    }
    applyTheme(next);
  }

  const options: Array<{ value: ThemeMode; label: string; icon: LucideIcon }> = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor }
  ];

  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="grid grid-cols-3 gap-1 rounded-md border border-border bg-surface-2 p-1"
    >
      {options.map((option) => {
        const Icon = option.icon;
        const isActive = option.value === mode;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={isActive}
            aria-label={option.label}
            onClick={() => selectMode(option.value)}
            className={cn(
              "inline-flex items-center justify-center gap-1.5 rounded-sm py-1.5 text-[11px] font-semibold transition",
              isActive
                ? "bg-card text-foreground shadow-sm"
                : "text-foreground-muted hover:text-foreground"
            )}
          >
            <Icon className="size-3.5" aria-hidden="true" />
            <span>{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
