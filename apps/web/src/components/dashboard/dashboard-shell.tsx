"use client";

import { type FormEvent, useState } from "react";
import {
  Activity,
  Ban,
  BookOpen,
  BriefcaseBusiness,
  CheckCircle2,
  ClipboardCheck,
  DatabaseZap,
  FileUser,
  Gauge,
  HelpCircle,
  Info,
  ListChecks,
  LockKeyhole,
  RefreshCcw,
  Search,
  ServerCog,
  ScrollText,
  ShieldCheck,
  SlidersHorizontal,
  TriangleAlert,
  X
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { ApplicationItem, ApplicationSnapshot } from "@/lib/application-data";
import type {
  ApprovalRequestItem,
  ApprovalRequestStatus,
  ApprovalSnapshot
} from "@/lib/approval-data";
import type { AuditEventItem, AuditSnapshot } from "@/lib/audit-data";
import type {
  CandidateEvidence,
  CandidateWorkspaceSnapshot,
  SearchCriteria
} from "@/lib/candidate-data";
import type { ApiHealthStatus } from "@/lib/health";
import type { JobCatalogSnapshot, JobItem } from "@/lib/job-data";
import {
  createLiveDiscoveryRun,
  createLiveSearchDiscoveryRun,
  type LiveDiscoveryRun
} from "@/lib/live-discovery-data";
import {
  attachSourcePolicy,
  createOperatorToken,
  getDiscoveryQueueRuns,
  getManualHandoffs,
  getObservabilitySummary,
  getSourceRecords,
  processDiscoveryQueueRun,
  resolveManualHandoff,
  type DiscoveryQueueRun,
  type ManualHandoff,
  type ObservabilitySummary,
  type OperatorToken,
  type SourceRecord
} from "@/lib/operator-control-data";
import {
  dashboardData,
  evaluateSourcePolicyLocally,
  getSourcePolicySummary,
  sourcePolicyActions,
  type ReviewQueueItem as ReviewQueueBucket,
  type SourcePolicy,
  type SourcePolicyAction,
  type SourcePolicyDecision
} from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";
import type { ReviewJobItem, ReviewQueueSnapshot } from "@/lib/review-data";
import type { RuntimeCapability, RuntimeSettings, SettingsSnapshot } from "@/lib/settings-data";

type DashboardView =
  | "job-overview"
  | "profile"
  | "jobs"
  | "applications"
  | "reviews-needed"
  | "admin-sources"
  | "admin-approvals"
  | "admin-audit"
  | "admin-system";

type NavigationArea = "job-search" | "administration";

const navigationAreas = [
  {
    label: "Job Search",
    value: "job-search",
    icon: Search,
    description: "Review live job matches, profile evidence, and application progress."
  },
  {
    label: "Administration",
    value: "administration",
    icon: ShieldCheck,
    description: "Review source policy, approvals, audit integrity, and runtime gates."
  }
] satisfies Array<{
  label: string;
  value: NavigationArea;
  icon: typeof Gauge;
  description: string;
}>;

const navItems = {
  "job-search": [
    { label: "Overview", icon: Gauge, view: "job-overview" },
    { label: "Profile", icon: FileUser, view: "profile" },
    { label: "Jobs", icon: BriefcaseBusiness, view: "jobs" },
    { label: "Applications", icon: ListChecks, view: "applications" },
    { label: "Reviews Needed", icon: ClipboardCheck, view: "reviews-needed" }
  ],
  administration: [
    { label: "Sources", icon: DatabaseZap, view: "admin-sources" },
    { label: "Approvals", icon: ClipboardCheck, view: "admin-approvals" },
    { label: "Audit Log", icon: ScrollText, view: "admin-audit" },
    { label: "System Status", icon: ServerCog, view: "admin-system" }
  ]
} satisfies Record<
  NavigationArea,
  Array<{ label: string; icon: typeof Gauge; view: DashboardView }>
>;

type HelpContent = {
  shows: string;
  actions: string[];
  guardrails: string[];
};

const helpContent = {
  "job-overview": {
    shows: "A user-facing summary of job matches, reviews, approvals, and application progress.",
    actions: [
      "Start with reviews that need a human check.",
      "Open Jobs to inspect matched roles.",
      "Open Applications to see tracked application status."
    ],
    guardrails: [
      "Review-first mode is active.",
      "Only approved external intake records are shown in the primary workflow.",
      "Discovery and packet preparation stay behind runtime flags, source policies, and manual review."
    ]
  },
  profile: {
    shows: "The connected profile, evidence, and job preferences used for matching.",
    actions: [
      "Check that profile evidence is complete enough for review.",
      "Use job preferences to understand the current matching criteria.",
      "Keep real CV, contact, and private candidate data out of this workspace."
    ],
    guardrails: [
      "Profile data stays disconnected until approved evidence or vault metadata is enabled.",
      "Candidate evidence is audited when changed.",
      "Claims must map back to approved evidence before later phases can use them."
    ]
  },
  jobs: {
    shows: "Live job records with source, location, pay, skills, and review status.",
    actions: [
      "Scan ready jobs first.",
      "Use review status to identify jobs that need human checks.",
      "Queue approved public source URLs from the Operator Console."
    ],
    guardrails: [
      "Only approved source-policy intake records are shown.",
      "Extraction confidence does not authorize automation.",
      "Submission remains disabled."
    ]
  },
  applications: {
    shows: "Read-only application tracker records and safety flags.",
    actions: [
      "Check whether an application is not started, in review, approved, or submitted.",
      "Use safety flags to confirm no autofill or submission has happened.",
      "Review linked approval records in Administration if needed."
    ],
    guardrails: [
      "No application creation endpoint is exposed.",
      "No autofill, browser handoff, or submit operation is available.",
      "External side effects should remain zero in this phase."
    ]
  },
  "reviews-needed": {
    shows: "Jobs and workflow items blocked by policy, confidence, or evidence issues.",
    actions: [
      "Review the reason before moving a job forward.",
      "Prioritize missing or uncertain data.",
      "Use approval requests for operator decisions."
    ],
    guardrails: [
      "Review is a stop gate, not a bypass.",
      "Policy and evidence issues must be resolved before later automation.",
      "CAPTCHA, access controls, and prohibited platforms stay blocked."
    ]
  },
  "admin-sources": {
    shows: "Source registry posture and action-scoped policy checks.",
    actions: [
      "Check whether a source/action pair is allowed, denied, or requires review.",
      "Confirm unknown sources deny all actions until reviewed.",
      "Keep source evidence current before allowing any downstream workflow."
    ],
    guardrails: [
      "Allowed discovery does not imply extraction, drafting, autofill, or submission.",
      "Expired evidence requires manual review.",
      "LinkedIn and Indeed examples are blocked by default."
    ]
  },
  "admin-approvals": {
    shows: "Manual approval requests and gated decisions.",
    actions: [
      "Review pending approval requests.",
      "Inspect why a request exists before approving or requesting changes.",
      "Use this area for operator review, not normal job browsing."
    ],
    guardrails: [
      "Approvals do not submit applications.",
      "Autofill and submit flags must remain false in this phase.",
      "Approval decisions emit audit events."
    ]
  },
  "admin-audit": {
    shows: "Hash-chained audit events for material decisions.",
    actions: [
      "Check event type, actor, correlation, and payload summary.",
      "Use the integrity status to spot direct data tampering.",
      "Keep raw private pages, cookies, tokens, and real candidate data out of audit payloads."
    ],
    guardrails: [
      "Audit events are append-only through the service layer.",
      "The chain must stay valid before trusting downstream workflow history.",
      "Payloads should be metadata and references, not secrets."
    ]
  },
  "admin-system": {
    shows: "Runtime health, capability gates, API status, and audit integrity.",
    actions: [
      "Confirm API health before investigating stale UI data.",
      "Check capability gates before enabling future integrations.",
      "Use system status for diagnostics, not everyday job-search work."
    ],
    guardrails: [
      "External integrations remain disabled.",
      "Secrets are not surfaced in the UI.",
      "Runtime gates should stay explicit before new capabilities are added."
    ]
  }
} satisfies Record<DashboardView, HelpContent>;

type DashboardShellProps = {
  health: ApiHealthStatus;
  candidateSnapshot: CandidateWorkspaceSnapshot;
  jobSnapshot: JobCatalogSnapshot;
  reviewSnapshot: ReviewQueueSnapshot;
  approvalSnapshot: ApprovalSnapshot;
  applicationSnapshot: ApplicationSnapshot;
  auditSnapshot: AuditSnapshot;
  settingsSnapshot: SettingsSnapshot;
};

export function DashboardShell({
  health,
  candidateSnapshot,
  jobSnapshot,
  reviewSnapshot,
  approvalSnapshot,
  applicationSnapshot,
  auditSnapshot,
  settingsSnapshot
}: DashboardShellProps) {
  const [activeArea, setActiveArea] = useState<NavigationArea>("job-search");
  const [activeView, setActiveView] = useState<DashboardView>("job-overview");
  const [helpOpen, setHelpOpen] = useState(false);
  const policySummary = getSourcePolicySummary(dashboardData.sourcePolicies);
  const liveJobs = liveJobItems(jobSnapshot.jobs);
  const liveReviewTotal = reviewSnapshot.items.filter((item) => !item.synthetic).length;
  const isProfileView = activeView === "profile";
  const isSourcesView = activeView === "admin-sources";
  const isJobsView = activeView === "jobs";
  const isReviewView = activeView === "reviews-needed";
  const isApplicationsView = activeView === "applications";
  const isApprovalsView = activeView === "admin-approvals";
  const isAuditView = activeView === "admin-audit";
  const isSystemView = activeView === "admin-system";
  const activeAreaMeta = navigationAreas.find((area) => area.value === activeArea);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="grid min-h-screen lg:grid-cols-[248px_1fr]">
        <aside className="border-b border-border bg-white lg:border-b-0 lg:border-r">
          <div className="flex h-full flex-col gap-5 px-4 py-4">
            <div className="flex items-center gap-3 px-2">
              <div className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <ShieldCheck className="size-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-semibold">Jobfinder</p>
                <p className="text-xs text-muted-foreground">Job search workspace</p>
              </div>
            </div>

            <div className="grid gap-2" aria-label="Workspace area">
              {navigationAreas.map((area) => {
                const Icon = area.icon;
                const isActive = area.value === activeArea;
                const firstView = navItems[area.value][0]?.view;

                return (
                  <button
                    key={area.value}
                    type="button"
                    aria-pressed={isActive}
                    onClick={() => {
                      setActiveArea(area.value);
                      setActiveView(firstView);
                    }}
                    className={cn(
                      "flex min-h-12 w-full items-start gap-3 rounded-md border px-3 py-2 text-left",
                      isActive
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-white text-foreground hover:bg-muted/70"
                    )}
                  >
                    <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold">{area.label}</span>
                      <span
                        className={cn(
                          "mt-0.5 block text-xs leading-4",
                          isActive ? "text-primary-foreground/80" : "text-muted-foreground"
                        )}
                      >
                        {area.description}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>

            <nav aria-label={`${activeAreaMeta?.label ?? "Workspace"} navigation`} className="grid gap-1">
              <p className="px-3 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                {activeAreaMeta?.label}
              </p>
              {navItems[activeArea].map((item) => {
                const Icon = item.icon;
                const isActive = item.view === activeView;

                return (
                  <button
                    key={item.label}
                    type="button"
                    aria-current={isActive ? "page" : undefined}
                    onClick={() => setActiveView(item.view)}
                    className={cn(
                      "flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm font-medium text-muted-foreground",
                      isActive && "bg-muted text-foreground",
                      "hover:bg-muted/70 hover:text-foreground"
                    )}
                  >
                    <Icon className="size-4" aria-hidden="true" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
            <div className="mt-auto hidden rounded-card border border-border bg-muted/60 p-3 text-xs text-muted-foreground lg:block">
              <p className="font-medium text-foreground">Review-first mode</p>
              <p className="mt-1 leading-5">
                Governed live intake can be enabled; browser automation and submission stay blocked.
              </p>
            </div>
          </div>
        </aside>

        <main className="min-w-0">
          <header className="border-b border-border bg-white px-4 py-4 sm:px-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  {viewEyebrow(activeView)}
                </p>
                <h1 className="mt-1 text-2xl font-semibold tracking-normal text-foreground">
                  {viewTitle(activeView)}
                </h1>
              </div>
              <div className="relative flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  aria-expanded={helpOpen}
                  aria-label={`Open help for ${viewTitle(activeView)}`}
                  onClick={() => setHelpOpen((open) => !open)}
                  className={cn(
                    "inline-flex size-8 items-center justify-center rounded-md border border-border bg-white text-muted-foreground",
                    "hover:bg-muted hover:text-foreground"
                  )}
                >
                  <HelpCircle className="size-4" aria-hidden="true" />
                </button>
                {helpOpen ? (
                  <ContextHelpPopover
                    areaLabel={activeAreaMeta?.label ?? "Workspace"}
                    title={`${viewTitle(activeView)} help`}
                    content={helpContent[activeView]}
                    onClose={() => setHelpOpen(false)}
                  />
                ) : null}
                {activeArea === "administration" ? (
                  <>
                    <Badge tone="success">{policySummary.allowed} approved sources</Badge>
                    <Badge tone={approvalSnapshot.summary.pending > 0 ? "warning" : "success"}>
                      {approvalSnapshot.summary.pending} pending approvals
                    </Badge>
                    <Badge tone={auditSnapshot.summary.chainValid ? "success" : "danger"}>
                      audit chain {auditSnapshot.summary.chainValid ? "valid" : "invalid"}
                    </Badge>
                  </>
                ) : (
                  <>
                    <Badge tone={liveJobs.length > 0 ? "success" : "warning"}>
                      {liveJobs.length} live jobs
                    </Badge>
                    <Badge tone={liveReviewTotal > 0 ? "warning" : "success"}>
                      {liveReviewTotal} live reviews
                    </Badge>
                    <Badge tone="info">
                      {applicationSnapshot.summary.total} applications
                    </Badge>
                  </>
                )}
              </div>
            </div>
          </header>

          {isSourcesView ? (
            <SourcesWorkspace policies={dashboardData.sourcePolicies} health={health} />
          ) : isProfileView ? (
            <CandidateWorkspace snapshot={candidateSnapshot} health={health} />
          ) : isJobsView ? (
            <JobsWorkspace snapshot={jobSnapshot} health={health} />
          ) : isReviewView ? (
            <ReviewWorkspace
              reviewSnapshot={reviewSnapshot}
              approvalSnapshot={approvalSnapshot}
              health={health}
            />
          ) : isApplicationsView ? (
            <ApplicationsWorkspace snapshot={applicationSnapshot} health={health} />
          ) : isApprovalsView ? (
            <ApprovalsWorkspace
              reviewSnapshot={reviewSnapshot}
              approvalSnapshot={approvalSnapshot}
              health={health}
            />
          ) : isAuditView ? (
            <AuditWorkspace snapshot={auditSnapshot} health={health} />
          ) : isSystemView ? (
            <SystemStatusWorkspace
              settingsSnapshot={settingsSnapshot}
              auditSnapshot={auditSnapshot}
              health={health}
            />
          ) : (
            <JobSearchOverview
              health={health}
              candidateSnapshot={candidateSnapshot}
              jobSnapshot={jobSnapshot}
              reviewSnapshot={reviewSnapshot}
              approvalSnapshot={approvalSnapshot}
              applicationSnapshot={applicationSnapshot}
              auditSnapshot={auditSnapshot}
              settingsSnapshot={settingsSnapshot}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function JobSearchOverview({
  health,
  candidateSnapshot,
  jobSnapshot,
  reviewSnapshot,
  approvalSnapshot,
  applicationSnapshot,
  auditSnapshot,
  settingsSnapshot
}: {
  health: ApiHealthStatus;
  candidateSnapshot: CandidateWorkspaceSnapshot;
  jobSnapshot: JobCatalogSnapshot;
  reviewSnapshot: ReviewQueueSnapshot;
  approvalSnapshot: ApprovalSnapshot;
  applicationSnapshot: ApplicationSnapshot;
  auditSnapshot: AuditSnapshot;
  settingsSnapshot: SettingsSnapshot;
}) {
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.5fr_1fr]">
      <section className="grid gap-4">
        <SafeLocalModeIntro />
        <NextActionPanel
          jobSnapshot={jobSnapshot}
          reviewSnapshot={reviewSnapshot}
          approvalSnapshot={approvalSnapshot}
          applicationSnapshot={applicationSnapshot}
        />
        <CandidateProfilePanel snapshot={candidateSnapshot} />
        <JobsPreviewPanel snapshot={jobSnapshot} />
        <PipelinePanel
          jobSnapshot={jobSnapshot}
          reviewSnapshot={reviewSnapshot}
          applicationSnapshot={applicationSnapshot}
        />
        <ApplicationTrackerPreview snapshot={applicationSnapshot} />
      </section>
      <section className="grid content-start gap-4">
        <HealthPanel health={health} />
        <ReviewQueuePanel items={reviewSnapshot.buckets} />
        <ApprovalSummaryPanel snapshot={approvalSnapshot} />
        <SafeModePanel
          source={settingsSnapshot.source}
          chainValid={auditSnapshot.summary.chainValid}
        />
        <GuardrailPanel />
      </section>
    </div>
  );
}

function SafeLocalModeIntro() {
  return (
    <Card className="border-blue-200 bg-blue-50/70">
      <CardContent className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 size-5 shrink-0 text-blue-700" aria-hidden="true" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-blue-950">Live job board intake</p>
          <p className="mt-1 text-sm leading-5 text-blue-900">
            Jobfinder is configured for governed live intake from approved public job sources.
            Reed, Hays, Totaljobs, CityJobs, and eFinancialCareers can be queued for bounded
            discovery and extraction. Indeed remains manual-only unless an approved official
            integration is configured.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function NextActionPanel({
  jobSnapshot,
  reviewSnapshot,
  approvalSnapshot,
  applicationSnapshot
}: {
  jobSnapshot: JobCatalogSnapshot;
  reviewSnapshot: ReviewQueueSnapshot;
  approvalSnapshot: ApprovalSnapshot;
  applicationSnapshot: ApplicationSnapshot;
}) {
  const liveJobs = liveJobItems(jobSnapshot.jobs);
  const liveReviewCount = reviewSnapshot.items.filter((item) => !item.synthetic).length;
  const actions = [
    {
      label: "Review job matches",
      detail: `${liveReviewCount} live jobs need a human check before they can move forward.`,
      tone: liveReviewCount > 0 ? "warning" : "success"
    },
    {
      label: "Track applications",
      detail: `${applicationSnapshot.summary.total} applications are in the tracker.`,
      tone: "info"
    },
    {
      label: "Check approvals",
      detail: `${approvalSnapshot.summary.pending} requests are waiting for review.`,
      tone: approvalSnapshot.summary.pending > 0 ? "warning" : "success"
    }
  ] satisfies Array<{ label: string; detail: string; tone: "info" | "success" | "warning" }>;

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle>Job Search Overview</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            Start here to import live postings, review matches, and track applications.
          </p>
        </div>
        <Badge tone={liveJobs.length > 0 ? "success" : "warning"}>{liveJobs.length} live jobs</Badge>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-3">
        {actions.map((action) => (
          <div key={action.label} className="rounded-md border border-border bg-muted/40 px-3 py-3">
            <Badge tone={action.tone}>{action.label}</Badge>
            <p className="mt-3 text-sm leading-5 text-muted-foreground">{action.detail}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function CandidateWorkspace({
  snapshot,
  health
}: {
  snapshot: CandidateWorkspaceSnapshot;
  health: ApiHealthStatus;
}) {
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.5fr_1fr]">
      <section className="grid gap-4">
        <CandidateProfilePanel snapshot={snapshot} />
        <CandidateEvidencePanel evidence={snapshot.evidence} />
      </section>
      <section className="grid content-start gap-4">
        <CandidateCriteriaPanel criteria={snapshot.searchCriteria} />
        <CandidateSafetyPanel snapshot={snapshot} />
        <HealthPanel health={health} />
      </section>
    </div>
  );
}

function CandidateProfilePanel({ snapshot }: { snapshot: CandidateWorkspaceSnapshot }) {
  const profileConnected = !snapshot.profile.synthetic;
  const displayName = profileConnected
    ? snapshot.profile.profileName
    : "Candidate profile not connected";
  const displaySummary =
    profileConnected && snapshot.profile.summary
      ? snapshot.profile.summary
      : "Connect approved profile evidence or encrypted candidate vault metadata before using profile data for matching.";

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Profile</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>
          {formatDataSource(snapshot.source)}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div>
          <p className="text-lg font-semibold">{displayName}</p>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            {displaySummary}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <MetricTile
            label="Evidence"
            value={snapshot.evidence.filter((item) => !item.synthetic).length}
          />
          <MetricTile
            label="Preferences"
            value={snapshot.searchCriteria.filter((item) => !item.synthetic).length}
          />
          <MetricTile label="Connected Profile" value={profileConnected ? 1 : 0} />
        </div>
        <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
          {profileConnected ? snapshot.profile.id : "profile connection pending"}
        </p>
      </CardContent>
    </Card>
  );
}

function CandidateEvidencePanel({ evidence }: { evidence: readonly CandidateEvidence[] }) {
  const liveEvidence = evidence.filter((item) => !item.synthetic);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile Evidence</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {liveEvidence.length === 0 ? (
          <div className="rounded-md border border-border bg-muted/40 px-3 py-4">
            <p className="text-sm font-medium">No approved profile evidence connected.</p>
            <p className="mt-2 text-sm leading-5 text-muted-foreground">
              Add evidence through the governed candidate vault flow before using profile data for
              matching or drafting.
            </p>
          </div>
        ) : (
          liveEvidence.map((item) => (
            <div key={item.id} className="rounded-md border border-border px-3 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{item.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{item.evidenceType}</p>
                </div>
              </div>
              <p className="mt-3 text-sm leading-5 text-muted-foreground">
                {item.description ?? "No description."}
              </p>
              {item.sourceUrl ? (
                <p className="mt-2 break-words font-mono text-xs text-muted-foreground">
                  {item.sourceUrl}
                </p>
              ) : null}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function CandidateCriteriaPanel({ criteria }: { criteria: readonly SearchCriteria[] }) {
  const liveCriteria = criteria.filter((item) => !item.synthetic);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Job Preferences</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {liveCriteria.length === 0 ? (
          <div className="rounded-md border border-border bg-muted/40 px-3 py-4">
            <p className="text-sm font-medium">No live search preferences configured.</p>
            <p className="mt-2 text-sm leading-5 text-muted-foreground">
              Use Administration to queue approved job-board URLs while profile preferences are
              being connected.
            </p>
          </div>
        ) : (
          liveCriteria.map((item) => (
            <div key={item.id} className="rounded-md border border-border px-3 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">{item.name}</p>
                <Badge tone={remoteTone(item.remoteType)}>{item.remoteType}</Badge>
              </div>
              <p className="mt-2 text-sm leading-5 text-muted-foreground">{item.query}</p>
              <p className="mt-2 font-mono text-xs text-muted-foreground">
                {item.location ?? "location open"} / {formatCriteriaSalary(item)}
              </p>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function CandidateSafetyPanel({ snapshot }: { snapshot: CandidateWorkspaceSnapshot }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile Data Safety</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <p className="text-sm leading-5 text-muted-foreground">
          Candidate profile data is only used after it is explicitly connected through approved
          evidence or candidate vault metadata.
        </p>
        {snapshot.checkedUrl ? (
          <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
            {snapshot.checkedUrl}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function JobsWorkspace({
  snapshot,
  health
}: {
  snapshot: JobCatalogSnapshot;
  health: ApiHealthStatus;
}) {
  const liveJobs = liveJobItems(snapshot.jobs);
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <JobCatalogTable jobs={liveJobs} />
      </section>
      <section className="grid content-start gap-4">
        <JobSummaryPanel snapshot={snapshot} />
        <HealthPanel health={health} />
        <GuardrailPanel />
      </section>
    </div>
  );
}

function ApplicationsWorkspace({
  snapshot,
  health
}: {
  snapshot: ApplicationSnapshot;
  health: ApiHealthStatus;
}) {
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <ApplicationTable applications={snapshot.applications} />
      </section>
      <section className="grid content-start gap-4">
        <ApplicationSummaryPanel snapshot={snapshot} />
        <HealthPanel health={health} />
        <GuardrailPanel />
      </section>
    </div>
  );
}

function ApprovalsWorkspace({
  reviewSnapshot,
  approvalSnapshot,
  health
}: {
  reviewSnapshot: ReviewQueueSnapshot;
  approvalSnapshot: ApprovalSnapshot;
  health: ApiHealthStatus;
}) {
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <ApprovalRequestsPanel snapshot={approvalSnapshot} />
      </section>
      <section className="grid content-start gap-4">
        <ApprovalSummaryPanel snapshot={approvalSnapshot} />
        <ReviewSummaryPanel snapshot={reviewSnapshot} />
        <HealthPanel health={health} />
        <GuardrailPanel />
      </section>
    </div>
  );
}

function SystemStatusWorkspace({
  settingsSnapshot,
  auditSnapshot,
  health
}: {
  settingsSnapshot: SettingsSnapshot;
  auditSnapshot: AuditSnapshot;
  health: ApiHealthStatus;
}) {
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <OperatorConsolePanel runtime={settingsSnapshot.runtime} />
        <LiveIntakePanel runtime={settingsSnapshot.runtime} />
        <RuntimeCapabilityPanel capabilities={settingsSnapshot.runtime.capabilities} />
        <RuntimeSettingsPanel snapshot={settingsSnapshot} />
      </section>
      <section className="grid content-start gap-4">
        <HealthPanel health={health} />
        <AuditSummaryPanel snapshot={auditSnapshot} />
        <GuardrailPanel />
      </section>
    </div>
  );
}

function AuditWorkspace({
  snapshot,
  health
}: {
  snapshot: AuditSnapshot;
  health: ApiHealthStatus;
}) {
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <AuditEventTable events={snapshot.events} />
      </section>
      <section className="grid content-start gap-4">
        <AuditSummaryPanel snapshot={snapshot} />
        <HealthPanel health={health} />
        <GuardrailPanel />
      </section>
    </div>
  );
}

function ReviewWorkspace({
  reviewSnapshot,
  approvalSnapshot,
  health
}: {
  reviewSnapshot: ReviewQueueSnapshot;
  approvalSnapshot: ApprovalSnapshot;
  health: ApiHealthStatus;
}) {
  const liveReviewItems = reviewSnapshot.items.filter((item) => !item.synthetic);

  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <ReviewQueueTable items={liveReviewItems} />
      </section>
      <section className="grid content-start gap-4">
        <ReviewSummaryPanel snapshot={reviewSnapshot} />
        <ApprovalRequestsPanel snapshot={approvalSnapshot} />
        <ReviewQueuePanel items={reviewSnapshot.buckets} />
        <HealthPanel health={health} />
      </section>
    </div>
  );
}

function SourcesWorkspace({
  policies,
  health
}: {
  policies: readonly SourcePolicy[];
  health: ApiHealthStatus;
}) {
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <SourceRegistryPanel policies={policies} />
      </section>
      <section className="grid content-start gap-4">
        <SourcePolicyReviewPanel />
        <PolicyCheckPanel policies={policies} />
        <HealthPanel health={health} />
        <GuardrailPanel />
      </section>
    </div>
  );
}

function SourceRegistryPanel({ policies }: { policies: readonly SourcePolicy[] }) {
  const summary = getSourcePolicySummary(policies);

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle>Source Registry</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Policy posture uses local fallback data unless the API check is configured.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="success">Allowed {summary.allowed}</Badge>
          <Badge tone="warning">Manual {summary.manualOnly}</Badge>
          <Badge tone="danger">Blocked {summary.blocked}</Badge>
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        <table className="min-w-[980px] border-separate border-spacing-0 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
              <th className="border-b border-border px-4 py-3 font-semibold">Source</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Type</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Policy</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Allowed</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Denied</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Review</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Reason</th>
            </tr>
          </thead>
          <tbody>
            {policies.map((policy) => (
              <tr key={policy.domain}>
                <td className="border-b border-border px-4 py-3 align-top">
                  <p className="font-medium">{policy.name}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">{policy.domain}</p>
                </td>
                <td className="border-b border-border px-4 py-3 align-top text-muted-foreground">
                  {policy.type}
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <PolicyBadge status={policy.status} />
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <ActionList actions={policy.allowedActions} emptyLabel="none" tone="success" />
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <ActionList actions={policy.deniedActions} emptyLabel="none" tone="danger" />
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <p className="text-sm">{formatReviewStatus(policy.reviewStatus)}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    {typeof policy.confidence === "number"
                      ? `${Math.round(policy.confidence * 100)}%`
                      : "no score"}
                  </p>
                </td>
                <td className="max-w-sm border-b border-border px-4 py-3 align-top text-muted-foreground">
                  {policy.reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function SourcePolicyReviewPanel() {
  const [actorId, setActorId] = useState("source-reviewer");
  const [loginSecret, setLoginSecret] = useState("");
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [status, setStatus] = useState("manual_only");
  const [allowedActions, setAllowedActions] = useState<SourcePolicyAction[]>(["extract"]);
  const [reason, setReason] = useState("Reviewed from operator console.");
  const [message, setMessage] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  async function handleRefreshSources() {
    setIsBusy(true);
    setMessage(null);
    try {
      const records = await getSourceRecords();
      setSources(records);
      setSelectedSourceId((current) => current || records[0]?.id || "");
      setMessage(`Loaded ${records.length} sources.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load sources.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleAttachPolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const selected = sources.find((source) => source.id === selectedSourceId);
    const deniedActions = sourcePolicyActions.filter((action) => !allowedActions.includes(action));
    setIsBusy(true);
    setMessage(null);
    try {
      if (!selected) {
        throw new Error("Select a source before attaching a policy.");
      }
      const token = await createOperatorToken(loginSecret, actorId);
      await attachSourcePolicy(token.accessToken, {
        sourceId: selected.id,
        status,
        reason,
        allowedActions,
        deniedActions
      });
      setMessage(`Policy attached to ${selected.domain}.`);
      const records = await getSourceRecords();
      setSources(records);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not attach source policy.");
    } finally {
      setIsBusy(false);
    }
  }

  function toggleAllowedAction(action: SourcePolicyAction) {
    setAllowedActions((current) =>
      current.includes(action)
        ? current.filter((candidate) => candidate !== action)
        : [...current, action]
    );
  }

  const selectedSource = sources.find((source) => source.id === selectedSourceId);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <div>
          <CardTitle>Source Policy Review</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Attach reviewed policies to registered sources.
          </p>
        </div>
        <Badge tone="info">operator</Badge>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={handleAttachPolicy}>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="grid gap-2 text-sm font-medium">
              <span>Actor</span>
              <input
                value={actorId}
                onChange={(event) => setActorId(event.currentTarget.value)}
                autoComplete="username"
                className="h-10 rounded-md border border-border bg-white px-3 text-sm"
              />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              <span>Login secret</span>
              <input
                type="password"
                value={loginSecret}
                onChange={(event) => setLoginSecret(event.currentTarget.value)}
                autoComplete="current-password"
                className="h-10 rounded-md border border-border bg-white px-3 text-sm"
              />
            </label>
          </div>
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <label className="grid gap-2 text-sm font-medium">
              <span>Source</span>
              <select
                value={selectedSourceId}
                onChange={(event) => setSelectedSourceId(event.currentTarget.value)}
                className="h-10 rounded-md border border-border bg-white px-3 text-sm"
              >
                {sources.length === 0 ? <option value="">Refresh sources</option> : null}
                {sources.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.name} - {source.domain}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={handleRefreshSources}
              disabled={isBusy}
              className="inline-flex h-10 items-center justify-center gap-2 self-end rounded-md border border-border bg-white px-3 text-sm font-semibold disabled:cursor-wait disabled:opacity-70"
            >
              <RefreshCcw className={cn("size-4", isBusy && "animate-spin")} aria-hidden="true" />
              Refresh
            </button>
          </div>
          {selectedSource ? (
            <div className="rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
              <p className="font-mono">{selectedSource.sourceType}</p>
              <p className="mt-1">Current policy: {selectedSource.policyStatus ?? "none"}</p>
            </div>
          ) : null}
          <label className="grid gap-2 text-sm font-medium">
            <span>Status</span>
            <select
              value={status}
              onChange={(event) => setStatus(event.currentTarget.value)}
              className="h-10 rounded-md border border-border bg-white px-3 text-sm"
            >
              <option value="allowed">allowed</option>
              <option value="manual_only">manual only</option>
              <option value="blocked">blocked</option>
            </select>
          </label>
          <fieldset className="grid gap-2">
            <legend className="text-sm font-medium">Allowed actions</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {sourcePolicyActions.map((action) => (
                <label key={action} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={allowedActions.includes(action)}
                    onChange={() => toggleAllowedAction(action)}
                    className="size-4 rounded border-border"
                  />
                  <span>{action}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <label className="grid gap-2 text-sm font-medium">
            <span>Reason</span>
            <textarea
              value={reason}
              onChange={(event) => setReason(event.currentTarget.value)}
              rows={3}
              className="rounded-md border border-border bg-white px-3 py-2 text-sm"
            />
          </label>
          <button
            type="submit"
            disabled={isBusy || !loginSecret || !selectedSourceId || !reason}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-70"
          >
            <ShieldCheck className="size-4" aria-hidden="true" />
            Attach policy
          </button>
        </form>
        {message ? (
          <p className="mt-3 rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
            {message}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function PolicyCheckPanel({ policies }: { policies: readonly SourcePolicy[] }) {
  const customSourceValue = "custom-source";
  const [selectedDomain, setSelectedDomain] = useState(policies[0]?.domain ?? "");
  const [customSource, setCustomSource] = useState("");
  const [customDomain, setCustomDomain] = useState("");
  const [action, setAction] = useState<SourcePolicyAction>("submit");
  const [result, setResult] = useState<PolicyCheckResult | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const isCustomSource = selectedDomain === customSourceValue;
    const selectedPolicy = policies.find((policy) => policy.domain === selectedDomain);
    const domain = isCustomSource ? customDomain : selectedDomain;
    const checkInput = {
      source: isCustomSource ? customSource || domain : selectedPolicy?.name ?? domain,
      domain,
      action
    };
    const localDecision = evaluateSourcePolicyLocally(checkInput, policies);
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

    setIsChecking(true);

    if (!apiBaseUrl) {
      setResult({
        ...localDecision,
        decisionSource: "local",
        detail: "NEXT_PUBLIC_API_BASE_URL is not configured; local policy fallback was used."
      });
      setIsChecking(false);
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/source-policies/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(checkInput)
      });

      if (!response.ok) {
        throw new Error(`Policy API returned ${response.status}`);
      }

      const payload = (await response.json()) as Partial<ApiPolicyCheckResponse>;
      setResult({
        ...mergeApiDecision(payload, localDecision),
        decisionSource: "api",
        detail: "Decision returned by the configured policy API."
      });
    } catch (error) {
      setResult({
        ...localDecision,
        decisionSource: "local",
        detail:
          error instanceof Error
            ? `Policy API unavailable; local fallback used. ${error.message}`
            : "Policy API unavailable; local fallback used."
      });
    } finally {
      setIsChecking(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Policy Check</CardTitle>
        <SlidersHorizontal className="size-4 text-muted-foreground" aria-hidden="true" />
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <label className="grid gap-2 text-sm font-medium">
            <span>Source / domain</span>
            <select
              value={selectedDomain}
              onChange={(event) => setSelectedDomain(event.currentTarget.value)}
              className="h-10 rounded-md border border-border bg-white px-3 text-sm"
            >
              {policies.map((policy) => (
                <option key={policy.domain} value={policy.domain}>
                  {policy.name} - {policy.domain}
                </option>
              ))}
              <option value={customSourceValue}>Custom / unknown source</option>
            </select>
          </label>
          {selectedDomain === customSourceValue ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-medium">
                <span>Source name</span>
                <input
                  value={customSource}
                  onChange={(event) => setCustomSource(event.currentTarget.value)}
                  placeholder="Unlisted board"
                  className="h-10 rounded-md border border-border bg-white px-3 text-sm"
                />
              </label>
              <label className="grid gap-2 text-sm font-medium">
                <span>Domain</span>
                <input
                  value={customDomain}
                  onChange={(event) => setCustomDomain(event.currentTarget.value)}
                  placeholder="jobs.example.com"
                  className="h-10 rounded-md border border-border bg-white px-3 text-sm"
                />
              </label>
            </div>
          ) : null}
          <label className="grid gap-2 text-sm font-medium">
            <span>Action</span>
            <select
              value={action}
              onChange={(event) => setAction(event.currentTarget.value as SourcePolicyAction)}
              className="h-10 rounded-md border border-border bg-white px-3 text-sm"
            >
              {sourcePolicyActions.map((policyAction) => (
                <option key={policyAction} value={policyAction}>
                  {policyAction}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={isChecking}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-3 text-sm font-semibold text-primary-foreground disabled:cursor-wait disabled:opacity-70"
          >
            <RefreshCcw className={cn("size-4", isChecking && "animate-spin")} aria-hidden="true" />
            Check policy
          </button>
        </form>

        {result ? (
          <div className="mt-4 rounded-md border border-border bg-muted/40 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={result.allowed ? "success" : "danger"}>
                {result.allowed ? "allowed" : "denied"}
              </Badge>
              <Badge tone={result.decisionSource === "api" ? "info" : "warning"}>
                {result.decisionSource}
              </Badge>
              <span className="font-mono text-xs text-muted-foreground">{result.action}</span>
            </div>
            <p className="mt-3 text-sm font-semibold">{result.policy.name}</p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">{result.policy.domain}</p>
            <p className="mt-3 text-sm leading-5 text-muted-foreground">{result.reason}</p>
            <p className="mt-3 text-xs leading-5 text-muted-foreground">{result.detail}</p>
          </div>
        ) : (
          <div className="mt-4 flex items-start gap-3 rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
            <Ban className="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
            <p>
              Submit and automation checks are denied for prohibited examples such as LinkedIn and
              Indeed.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PipelinePanel({
  jobSnapshot,
  reviewSnapshot,
  applicationSnapshot
}: {
  jobSnapshot: JobCatalogSnapshot;
  reviewSnapshot: ReviewQueueSnapshot;
  applicationSnapshot: ApplicationSnapshot;
}) {
  const liveJobs = liveJobItems(jobSnapshot.jobs);
  const liveReviewCount = reviewSnapshot.items.filter((item) => !item.synthetic).length;
  const columns = [
    {
      label: "Imported",
      count: liveJobs.length,
      description: "Live postings imported from approved job-board or ATS sources."
    },
    {
      label: "Needs Review",
      count: liveReviewCount,
      description: "Live postings waiting for source, confidence, or evidence review."
    },
    {
      label: "Ready",
      count: liveJobs.filter((job) => job.reviewStatus === "ready").length,
      description: "Live postings ready for operator review and application tracking."
    },
    {
      label: "Applications",
      count: applicationSnapshot.summary.total,
      description: "Application tracker records created from approved live postings."
    }
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live Pipeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-4">
          {columns.map((column) => (
            <div
              key={column.label}
              className="min-h-36 rounded-card border border-border bg-muted/40 p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold">{column.label}</h3>
                <span className="font-mono text-xl font-semibold">{column.count}</span>
              </div>
              <Separator className="my-3" />
              <p className="text-xs leading-5 text-muted-foreground">{column.description}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ReviewQueuePanel({ items }: { items: readonly ReviewQueueBucket[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Reviews Needed</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex min-h-12 items-center justify-between gap-3 rounded-md border border-border px-3 py-2"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{item.label}</p>
              <p className="text-xs text-muted-foreground">Approval gate pending</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={riskTone(item.risk)}>{item.risk}</Badge>
              <span className="w-6 text-right font-mono text-sm font-semibold">{item.count}</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function JobsPreviewPanel({ snapshot }: { snapshot: JobCatalogSnapshot }) {
  const visibleJobs = liveJobItems(snapshot.jobs).slice(0, 4);

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Jobs</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Badge tone={snapshot.source === "api" ? "info" : "warning"}>
            {formatDataSource(snapshot.source)}
          </Badge>
          <Badge tone={visibleJobs.length > 0 ? "success" : "warning"}>
            {visibleJobs.length} live jobs
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3">
        {visibleJobs.length === 0 ? (
          <div className="rounded-md border border-border bg-muted/40 px-3 py-4">
            <p className="text-sm font-medium">No live jobs imported yet.</p>
            <p className="mt-2 text-sm leading-5 text-muted-foreground">
              Use the Operator Console to queue approved public URLs from Reed, Hays, Totaljobs,
              CityJobs, or eFinancialCareers.
            </p>
          </div>
        ) : (
          visibleJobs.map((job) => (
            <div
              key={job.id}
              className="grid gap-3 rounded-md border border-border px-3 py-3 md:grid-cols-[1.4fr_0.8fr_auto]"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{job.title}</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">{job.company}</p>
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs text-muted-foreground">{job.source}</p>
                <p className="mt-1 truncate font-mono text-xs text-muted-foreground">
                  {job.externalId}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2 md:justify-end">
                <Badge tone={remoteTone(job.remoteType)}>{job.remoteType}</Badge>
                <ReviewStatusBadge status={job.reviewStatus} />
              </div>
            </div>
          ))
        )}
        <p className="text-sm leading-5 text-muted-foreground">
          Live job data appears here after approved source intake. Placeholder records are hidden
          from the primary job search workflow.
        </p>
      </CardContent>
    </Card>
  );
}

function ApplicationTrackerPreview({ snapshot }: { snapshot: ApplicationSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Applications</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Badge tone={snapshot.source === "api" ? "info" : "warning"}>
            {formatDataSource(snapshot.source)}
          </Badge>
          <Badge tone={snapshot.summary.externalSideEffects > 0 ? "danger" : "success"}>
            {snapshot.summary.externalSideEffects} safety flags
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-2 sm:grid-cols-4">
          <MetricTile label="Tracked" value={snapshot.summary.total} />
          <MetricTile label="Needs Review" value={snapshot.summary.inReview} />
          <MetricTile label="Approved" value={snapshot.summary.approved} />
          <MetricTile label="Submitted" value={snapshot.summary.submitted} />
        </div>
        <p className="text-sm leading-5 text-muted-foreground">{snapshot.detail}</p>
      </CardContent>
    </Card>
  );
}

function JobSummaryPanel({ snapshot }: { snapshot: JobCatalogSnapshot }) {
  const liveJobs = liveJobItems(snapshot.jobs);
  const readyLiveJobs = liveJobs.filter((job) => job.reviewStatus === "ready").length;
  const liveNeedsReview = liveJobs.filter((job) => job.reviewStatus === "needs_review").length;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Job Summary</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>
          {formatDataSource(snapshot.source)}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Live Total" value={liveJobs.length} />
          <MetricTile label="Ready" value={readyLiveJobs} />
          <MetricTile label="Needs Review" value={liveNeedsReview} />
          <MetricTile
            label="Remote"
            value={liveJobs.filter((job) => job.remoteType === "remote").length}
          />
          <MetricTile
            label="Hybrid"
            value={liveJobs.filter((job) => job.remoteType === "hybrid").length}
          />
          <MetricTile
            label="Onsite"
            value={liveJobs.filter((job) => job.remoteType === "onsite").length}
          />
        </div>
        <p className="text-sm leading-5 text-muted-foreground">
          Live totals count approved external intake records only.
        </p>
        {snapshot.checkedUrl ? (
          <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
            {snapshot.checkedUrl}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ApplicationSummaryPanel({ snapshot }: { snapshot: ApplicationSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Application Summary</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>
          {formatDataSource(snapshot.source)}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Tracked" value={snapshot.summary.total} />
          <MetricTile label="Not Started" value={snapshot.summary.notStarted} />
          <MetricTile label="Needs Review" value={snapshot.summary.inReview} />
          <MetricTile label="Approved" value={snapshot.summary.approved} />
          <MetricTile label="Submitted" value={snapshot.summary.submitted} />
          <MetricTile label="Safety Flags" value={snapshot.summary.externalSideEffects} />
        </div>
        <p className="text-sm leading-5 text-muted-foreground">{snapshot.detail}</p>
        {snapshot.checkedUrl ? (
          <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
            {snapshot.checkedUrl}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function RuntimeSettingsPanel({ snapshot }: { snapshot: SettingsSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Runtime Settings</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>
          {formatDataSource(snapshot.source)}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Audit Schema" value={snapshot.runtime.auditSchemaVersion} />
          <MetricTile label="Database" value={snapshot.runtime.databaseConfigured ? 1 : 0} />
          <MetricTile label="Redis" value={snapshot.runtime.redisConfigured ? 1 : 0} />
          <MetricTile label="Secrets" value={snapshot.runtime.secretsLoaded ? 1 : 0} />
          <MetricTile
            label="External Integrations"
            value={snapshot.runtime.externalIntegrationsEnabled ? 1 : 0}
          />
          <MetricTile label="Capabilities" value={snapshot.runtime.capabilities.length} />
        </div>
        <div className="rounded-md border border-border bg-muted/40 px-3 py-3">
          <p className="text-sm font-medium">{snapshot.runtime.serviceName}</p>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            environment {snapshot.runtime.environment}
          </p>
        </div>
        <p className="text-sm leading-5 text-muted-foreground">{snapshot.detail}</p>
        {snapshot.checkedUrl ? (
          <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
            {snapshot.checkedUrl}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ReviewSummaryPanel({ snapshot }: { snapshot: ReviewQueueSnapshot }) {
  const liveItems = snapshot.items.filter((item) => !item.synthetic);
  const readyLiveItems = liveItems.filter((item) => item.reviewStatus === "ready").length;
  const needsReviewLiveItems = liveItems.filter(
    (item) => item.reviewStatus === "needs_review"
  ).length;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Review Summary</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>
          {formatDataSource(snapshot.source)}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-3 gap-2">
          <MetricTile label="Live Total" value={liveItems.length} />
          <MetricTile label="Ready" value={readyLiveItems} />
          <MetricTile label="Needs Review" value={needsReviewLiveItems} />
        </div>
        <p className="text-sm leading-5 text-muted-foreground">
          Live review totals count approved external intake records only.
        </p>
        {snapshot.checkedUrl ? (
          <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
            {snapshot.checkedUrl}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ApprovalSummaryPanel({ snapshot }: { snapshot: ApprovalSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Approvals</CardTitle>
        <Badge tone={snapshot.summary.pending > 0 ? "warning" : "success"}>
          {snapshot.summary.pending} pending
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Total" value={snapshot.summary.total} />
          <MetricTile label="Changes" value={snapshot.summary.needsChanges} />
        </div>
        <p className="text-sm leading-5 text-muted-foreground">
          Manual approval records only. No autofill or submit action is available.
        </p>
      </CardContent>
    </Card>
  );
}

function ApprovalRequestsPanel({ snapshot }: { snapshot: ApprovalSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Approval Requests</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>
          {formatDataSource(snapshot.source)}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-4 gap-2">
          <MetricTile label="Total" value={snapshot.summary.total} />
          <MetricTile label="Pending" value={snapshot.summary.pending} />
          <MetricTile label="Approved" value={snapshot.summary.approved} />
          <MetricTile label="Changes" value={snapshot.summary.needsChanges} />
        </div>
        <div className="grid gap-3">
          {snapshot.requests.length === 0 ? (
            <p className="rounded-md border border-border px-3 py-3 text-sm text-muted-foreground">
              No approval requests are waiting.
            </p>
          ) : (
            snapshot.requests.map((request) => (
              <ApprovalRequestRow key={request.id} request={request} />
            ))
          )}
        </div>
        <p className="text-sm leading-5 text-muted-foreground">{snapshot.detail}</p>
        {snapshot.checkedUrl ? (
          <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
            {snapshot.checkedUrl}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function AuditSummaryPanel({ snapshot }: { snapshot: AuditSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Audit Integrity</CardTitle>
        <Badge tone={snapshot.summary.chainValid ? "success" : "danger"}>
          {snapshot.summary.chainValid ? "chain valid" : "chain invalid"}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Events" value={snapshot.summary.total} />
          <MetricTile label="Schema" value={snapshot.events[0]?.schemaVersion ?? 1} />
        </div>
        <p className="text-sm leading-5 text-muted-foreground">{snapshot.detail}</p>
        {snapshot.summary.latestHash ? (
          <p className="break-all rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
            {snapshot.summary.latestHash}
          </p>
        ) : null}
        {snapshot.checkedUrl ? (
          <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
            {snapshot.checkedUrl}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function AuditEventTable({ events }: { events: readonly AuditEventItem[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Audit Events</CardTitle>
        <Badge tone="info">{events.length} visible</Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        <table className="min-w-[1040px] border-separate border-spacing-0 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
              <th className="border-b border-border px-4 py-3 font-semibold">Event</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Actor</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Correlation</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Payload</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Hash</th>
              <th className="border-b border-border px-4 py-3 text-right font-semibold">Time</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td className="border-b border-border px-4 py-3 align-top">
                  <p className="font-medium">{event.eventType}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">{event.id}</p>
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <Badge tone={event.actorType === "system" ? "info" : "neutral"}>
                    {event.actorType}
                  </Badge>
                  <p className="mt-2 font-mono text-xs text-muted-foreground">{event.actorId}</p>
                </td>
                <td className="max-w-xs border-b border-border px-4 py-3 align-top font-mono text-xs text-muted-foreground">
                  {event.correlationId}
                </td>
                <td className="max-w-xs border-b border-border px-4 py-3 align-top text-muted-foreground">
                  {summarizePayload(event.payload)}
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <p className="max-w-[220px] truncate font-mono text-xs text-muted-foreground">
                    {event.eventHash}
                  </p>
                  <p className="mt-1 max-w-[220px] truncate font-mono text-xs text-muted-foreground">
                    prev {event.previousHash ?? "genesis"}
                  </p>
                </td>
                <td className="border-b border-border px-4 py-3 text-right align-top font-mono text-xs text-muted-foreground">
                  {formatTimestamp(event.createdAt)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function ApprovalRequestRow({ request }: { request: ApprovalRequestItem }) {
  return (
    <div className="rounded-md border border-border px-3 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{formatRequestType(request.requestType)}</p>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{request.jobPostingId}</p>
        </div>
        <ApprovalStatusBadge status={request.status} />
      </div>
      <p className="mt-3 text-sm leading-5 text-muted-foreground">{request.reason}</p>
      {request.decisionReason ? (
        <p className="mt-2 text-xs leading-5 text-muted-foreground">{request.decisionReason}</p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Badge tone="neutral">{request.sideEffect}</Badge>
      </div>
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-xl font-semibold">{value}</p>
    </div>
  );
}

function JobCatalogTable({ jobs }: { jobs: readonly JobItem[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Live Jobs</CardTitle>
        <Badge tone={jobs.length > 0 ? "success" : "warning"}>{jobs.length} live jobs</Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        {jobs.length === 0 ? (
          <div className="grid gap-3 px-4 py-8">
            <p className="text-sm font-medium">No live jobs imported yet.</p>
            <p className="max-w-2xl text-sm leading-5 text-muted-foreground">
              Queue approved source URLs from the Operator Console. Jobfinder will stop at manual
              handoff if a page presents login, CAPTCHA, bot detection, or access controls.
            </p>
          </div>
        ) : (
          <table className="min-w-[1100px] border-separate border-spacing-0 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
              <th className="border-b border-border px-4 py-3 font-semibold">Job</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Source</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Location</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Pay</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Skills</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Status</th>
              <th className="border-b border-border px-4 py-3 text-right font-semibold">
                Confidence
              </th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td className="border-b border-border px-4 py-3 align-top">
                  <p className="font-medium">{job.title || "Untitled posting"}</p>
                  <p className="mt-1 text-muted-foreground">{job.company || "Unknown company"}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">{job.externalId}</p>
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <p className="font-medium">{job.source}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    {job.externalId}
                  </p>
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <Badge tone={remoteTone(job.remoteType)}>{job.remoteType}</Badge>
                  <p className="mt-2 text-muted-foreground">{job.locations.join(", ")}</p>
                </td>
                <td className="border-b border-border px-4 py-3 align-top text-muted-foreground">
                  {formatSalary(job)}
                </td>
                <td className="max-w-xs border-b border-border px-4 py-3 align-top">
                  <SkillList skills={[...job.requiredSkills, ...job.preferredSkills]} />
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <ReviewStatusBadge status={job.reviewStatus} />
                  <ReviewReasons reasons={job.reviewReasons} />
                </td>
                <td className="border-b border-border px-4 py-3 text-right align-top font-mono text-xs">
                  {Math.round(job.extractionConfidence * 100)}%
                  <p className="mt-2 text-muted-foreground">live</p>
                </td>
              </tr>
            ))}
          </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}

function ApplicationTable({ applications }: { applications: readonly ApplicationItem[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Applications</CardTitle>
        <Badge tone="info">{applications.length} tracked</Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        {applications.length === 0 ? (
          <div className="grid gap-3 px-4 py-8">
            <p className="text-sm font-medium">No application records have been created.</p>
            <p className="max-w-2xl text-sm leading-5 text-muted-foreground">
              This workspace is read-only for now: no drafting packet, autofill, browser handoff,
              or submit operation is available.
            </p>
          </div>
        ) : (
          <table className="min-w-[980px] border-separate border-spacing-0 text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
                <th className="border-b border-border px-4 py-3 font-semibold">Application</th>
                <th className="border-b border-border px-4 py-3 font-semibold">Status</th>
                <th className="border-b border-border px-4 py-3 font-semibold">Approval</th>
                <th className="border-b border-border px-4 py-3 font-semibold">Safety</th>
                <th className="border-b border-border px-4 py-3 text-right font-semibold">
                  Updated
                </th>
              </tr>
            </thead>
            <tbody>
              {applications.map((application) => (
                <tr key={application.id}>
                  <td className="border-b border-border px-4 py-3 align-top">
                    <p className="font-medium">{application.jobTitle}</p>
                    <p className="mt-1 text-muted-foreground">{application.company}</p>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {application.jobPostingId}
                    </p>
                  </td>
                  <td className="border-b border-border px-4 py-3 align-top">
                    <ApplicationStatusBadge status={application.status} />
                    {application.submittedAt ? (
                      <p className="mt-2 font-mono text-xs text-muted-foreground">
                        submitted {formatTimestamp(application.submittedAt)}
                      </p>
                    ) : null}
                  </td>
                  <td className="border-b border-border px-4 py-3 align-top font-mono text-xs text-muted-foreground">
                    {application.approvalRequestId ?? "not linked"}
                  </td>
                  <td className="border-b border-border px-4 py-3 align-top">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone={application.safety.submitPerformed ? "danger" : "success"}>
                        submitted {application.safety.submitPerformed ? "yes" : "no"}
                      </Badge>
                      <Badge tone={application.safety.autofillPerformed ? "danger" : "success"}>
                        autofilled {application.safety.autofillPerformed ? "yes" : "no"}
                      </Badge>
                    </div>
                  </td>
                  <td className="border-b border-border px-4 py-3 text-right align-top font-mono text-xs text-muted-foreground">
                    {formatTimestamp(application.updatedAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}

function OperatorConsolePanel({ runtime }: { runtime: RuntimeSettings }) {
  const sessionAuthEnabled = isCapabilityEnabled(runtime.capabilities, "operator_session_auth");
  const [actorId, setActorId] = useState("dashboard-operator");
  const [loginSecret, setLoginSecret] = useState("");
  const [token, setToken] = useState<OperatorToken | null>(null);
  const [handoffs, setHandoffs] = useState<ManualHandoff[]>([]);
  const [queueRuns, setQueueRuns] = useState<DiscoveryQueueRun[]>([]);
  const [observability, setObservability] = useState<ObservabilitySummary | null>(null);
  const [statusText, setStatusText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refreshConsole() {
    setLoading(true);
    setStatusText(null);
    try {
      const [handoffPayload, queuePayload, observabilityPayload] = await Promise.all([
        getManualHandoffs(),
        getDiscoveryQueueRuns(),
        getObservabilitySummary()
      ]);
      setHandoffs(handoffPayload);
      setQueueRuns(queuePayload);
      setObservability(observabilityPayload);
    } catch (caught) {
      setStatusText(caught instanceof Error ? caught.message : "Operator console refresh failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setStatusText(null);
    try {
      const nextToken = await createOperatorToken(loginSecret, actorId);
      setToken(nextToken);
      setLoginSecret("");
      setStatusText(`Session active until ${new Date(nextToken.expiresAt).toLocaleString()}.`);
    } catch (caught) {
      setStatusText(caught instanceof Error ? caught.message : "Operator login failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(recordId: string) {
    if (!token) {
      setStatusText("Sign in with an operator session before resolving handoffs.");
      return;
    }
    setLoading(true);
    try {
      await resolveManualHandoff(token.accessToken, recordId, token.actorId);
      await refreshConsole();
    } catch (caught) {
      setStatusText(caught instanceof Error ? caught.message : "Handoff resolve failed.");
      setLoading(false);
    }
  }

  async function handleProcess(runId: string) {
    if (!token) {
      setStatusText("Sign in with an operator session before processing queued runs.");
      return;
    }
    setLoading(true);
    try {
      await processDiscoveryQueueRun(token.accessToken, runId);
      await refreshConsole();
    } catch (caught) {
      setStatusText(caught instanceof Error ? caught.message : "Queue processing failed.");
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle>Operator Console</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            Resolve handoffs, process queued discovery, and inspect live operational health.
          </p>
        </div>
        <Badge tone={sessionAuthEnabled ? "success" : "warning"}>
          {sessionAuthEnabled ? "session auth" : "legacy auth"}
        </Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <form className="grid gap-3 md:grid-cols-[0.9fr_1fr_auto]" onSubmit={handleLogin}>
          <label className="grid gap-1 text-sm font-medium">
            Actor
            <input
              value={actorId}
              onChange={(event) => setActorId(event.target.value)}
              autoComplete="username"
              className="h-10 rounded-md border border-border bg-white px-3 text-sm font-normal outline-none focus:border-primary"
            />
          </label>
          <label className="grid gap-1 text-sm font-medium">
            Login secret
            <input
              type="password"
              value={loginSecret}
              onChange={(event) => setLoginSecret(event.target.value)}
              autoComplete="current-password"
              className="h-10 rounded-md border border-border bg-white px-3 text-sm font-normal outline-none focus:border-primary"
            />
          </label>
          <button
            type="submit"
            disabled={loading || !loginSecret.trim()}
            className="inline-flex h-10 items-center justify-center gap-2 self-end rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-60"
          >
            <LockKeyhole className="size-4" aria-hidden="true" />
            Sign in
          </button>
        </form>
        <div className="grid gap-2 sm:grid-cols-5">
          <MetricTile label="Open Handoffs" value={observability?.openManualHandoffs ?? 0} />
          <MetricTile label="Queued Runs" value={observability?.queuedDiscoveryRuns ?? 0} />
          <MetricTile label="Failed Runs" value={observability?.failedDiscoveryRuns ?? 0} />
          <MetricTile label="Audit Events" value={observability?.totalAuditEvents ?? 0} />
          <MetricTile label="Errors" value={observability?.errorEvents ?? 0} />
        </div>
        {observability?.activeAlerts.length ? (
          <div className="grid gap-2">
            {observability.activeAlerts.map((alert) => (
              <div key={alert.id} className="rounded-md border border-border bg-muted/40 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    tone={
                      alert.severity === "critical"
                        ? "danger"
                        : alert.severity === "warning"
                          ? "warning"
                          : "info"
                    }
                  >
                    {alert.severity}
                  </Badge>
                  <p className="text-sm font-semibold">{alert.title}</p>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{alert.detail}</p>
                <p className="mt-2 text-xs text-muted-foreground">{alert.recommendedAction}</p>
              </div>
            ))}
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void refreshConsole()}
            disabled={loading}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-white px-3 text-sm font-medium text-foreground disabled:opacity-60"
          >
            <RefreshCcw className={cn("size-4", loading && "animate-spin")} aria-hidden="true" />
            Refresh
          </button>
          <Badge tone={token ? "success" : "neutral"}>{token ? "signed in" : "read only"}</Badge>
          {observability ? (
            <Badge tone={observability.auditChainValid ? "success" : "danger"}>
              audit {observability.auditChainValid ? "valid" : "invalid"}
            </Badge>
          ) : null}
        </div>
        {statusText ? (
          <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
            {statusText}
          </p>
        ) : null}
        <div className="grid gap-4 xl:grid-cols-2">
          <OperatorHandoffList
            handoffs={handoffs}
            canMutate={Boolean(token)}
            onResolve={handleResolve}
          />
          <OperatorQueueList
            runs={queueRuns}
            canMutate={Boolean(token)}
            onProcess={handleProcess}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function OperatorHandoffList({
  handoffs,
  canMutate,
  onResolve
}: {
  handoffs: readonly ManualHandoff[];
  canMutate: boolean;
  onResolve: (recordId: string) => void;
}) {
  return (
    <div className="rounded-md border border-border">
      <div className="border-b border-border px-3 py-2">
        <p className="text-sm font-semibold">Manual Handoffs</p>
      </div>
      <div className="grid max-h-80 gap-2 overflow-auto p-3">
        {handoffs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No open handoffs.</p>
        ) : (
          handoffs.map((handoff) => (
            <div key={handoff.id} className="rounded-md bg-muted/50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Badge tone="warning">{handoff.triggerType}</Badge>
                <button
                  type="button"
                  disabled={!canMutate}
                  onClick={() => onResolve(handoff.id)}
                  className="h-8 rounded-md border border-border bg-white px-3 text-xs font-semibold text-foreground disabled:opacity-50"
                >
                  Resolve
                </button>
              </div>
              <p className="mt-2 truncate font-mono text-xs text-muted-foreground">{handoff.url}</p>
              <p className="mt-2 text-sm leading-5 text-muted-foreground">
                {handoff.detectionDetail}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function OperatorQueueList({
  runs,
  canMutate,
  onProcess
}: {
  runs: readonly DiscoveryQueueRun[];
  canMutate: boolean;
  onProcess: (runId: string) => void;
}) {
  return (
    <div className="rounded-md border border-border">
      <div className="border-b border-border px-3 py-2">
        <p className="text-sm font-semibold">Discovery Queue</p>
      </div>
      <div className="grid max-h-80 gap-2 overflow-auto p-3">
        {runs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No queued discovery runs.</p>
        ) : (
          runs.map((run) => (
            <div key={run.id} className="rounded-md bg-muted/50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Badge tone={run.status === "failed" ? "danger" : "info"}>{run.status}</Badge>
                <button
                  type="button"
                  disabled={!canMutate || run.status === "completed"}
                  onClick={() => onProcess(run.id)}
                  className="h-8 rounded-md border border-border bg-white px-3 text-xs font-semibold text-foreground disabled:opacity-50"
                >
                  Process
                </button>
              </div>
              <p className="mt-2 truncate font-mono text-xs text-muted-foreground">{run.url}</p>
              <p className="mt-2 text-xs text-muted-foreground">
                {run.mode} / attempts {run.attempts}/{run.maxAttempts}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function LiveIntakePanel({
  runtime
}: {
  runtime: RuntimeSettings;
}) {
  const capabilities = runtime.capabilities;
  const liveDiscoveryEnabled = isCapabilityEnabled(capabilities, "live_discovery");
  const liveSearchEnabled = isCapabilityEnabled(capabilities, "live_search_discovery");
  const productionMode = runtime.environment === "production";
  const operatorKeyConfigured = isCapabilityEnabled(capabilities, "operator_api_key");
  const [mode, setMode] = useState<"job" | "search">("job");
  const [url, setUrl] = useState("");
  const [sourceDomain, setSourceDomain] = useState("");
  const [maxResults, setMaxResults] = useState(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [run, setRun] = useState<LiveDiscoveryRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeEnabled = mode === "job" ? liveDiscoveryEnabled : liveSearchEnabled;
  const command = formatLiveIntakeCommand({ maxResults, mode, sourceDomain, url });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (productionMode) {
      setRun(null);
      setError("Use the local operator command for production live intake.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setRun(null);

    try {
      const result =
        mode === "job"
          ? await createLiveDiscoveryRun({
              url,
              sourceDomain: sourceDomain.trim() || undefined
            })
          : await createLiveSearchDiscoveryRun({
              url,
              sourceDomain: sourceDomain.trim() || undefined,
              maxResults
            });
      setRun(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Live intake failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle>Live Intake</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            Production live intake is run through the local operator command so the operator key
            never enters the browser.
          </p>
        </div>
        <Badge tone={activeEnabled ? "success" : "neutral"}>
          {activeEnabled ? "enabled" : "disabled"}
        </Badge>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="inline-grid w-full grid-cols-2 rounded-md border border-border bg-muted/40 p-1 sm:w-fit">
            <button
              type="button"
              aria-pressed={mode === "job"}
              onClick={() => setMode("job")}
              className={cn(
                "rounded px-3 py-2 text-sm font-medium",
                mode === "job" ? "bg-white text-foreground shadow-sm" : "text-muted-foreground"
              )}
            >
              Job page
            </button>
            <button
              type="button"
              aria-pressed={mode === "search"}
              onClick={() => setMode("search")}
              className={cn(
                "rounded px-3 py-2 text-sm font-medium",
                mode === "search" ? "bg-white text-foreground shadow-sm" : "text-muted-foreground"
              )}
            >
              Search page
            </button>
          </div>
          <div className="grid gap-3 md:grid-cols-[1.4fr_0.8fr]">
            <label className="grid gap-1 text-sm font-medium">
              URL
              <input
                type="url"
                required
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://careers.example.test/jobs/platform"
                className="h-10 rounded-md border border-border bg-white px-3 text-sm font-normal outline-none focus:border-primary"
              />
            </label>
            <label className="grid gap-1 text-sm font-medium">
              Source domain
              <input
                type="text"
                value={sourceDomain}
                onChange={(event) => setSourceDomain(event.target.value)}
                placeholder="careers.example.test"
                className="h-10 rounded-md border border-border bg-white px-3 text-sm font-normal outline-none focus:border-primary"
              />
            </label>
          </div>
          {mode === "search" ? (
            <label className="grid max-w-48 gap-1 text-sm font-medium">
              Max results
              <input
                type="number"
                min={1}
                max={100}
                value={maxResults}
                onChange={(event) => setMaxResults(Number(event.target.value))}
                className="h-10 rounded-md border border-border bg-white px-3 text-sm font-normal outline-none focus:border-primary"
              />
            </label>
          ) : null}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="submit"
              disabled={isSubmitting || productionMode}
              className={cn(
                "inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground",
                "disabled:cursor-not-allowed disabled:opacity-60"
              )}
            >
              {isSubmitting ? (
                <RefreshCcw className="size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Search className="size-4" aria-hidden="true" />
              )}
              {productionMode ? "Use local command" : "Run intake"}
            </button>
            <Badge tone={activeEnabled ? "success" : "warning"}>
              {activeEnabled ? "policy gated" : "runtime flag off"}
            </Badge>
            {productionMode ? (
              <Badge tone={operatorKeyConfigured ? "success" : "warning"}>
                {operatorKeyConfigured ? "operator key configured" : "operator key missing"}
              </Badge>
            ) : null}
          </div>
        </form>
        {productionMode ? (
          <div className="mt-4 rounded-md border border-border bg-muted/40 p-3">
            <p className="text-sm font-medium text-foreground">Local command</p>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded bg-white p-3 font-mono text-xs text-muted-foreground">
              {command}
            </pre>
          </div>
        ) : null}
        {error ? (
          <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
            {error}
          </p>
        ) : null}
        {run ? <LiveIntakeResult run={run} /> : null}
      </CardContent>
    </Card>
  );
}

function formatLiveIntakeCommand({
  maxResults,
  mode,
  sourceDomain,
  url
}: {
  maxResults: number;
  mode: "job" | "search";
  sourceDomain: string;
  url: string;
}) {
  const args = ["pnpm operator:live-intake --"];
  if (mode === "search") {
    args.push("--search");
  }
  args.push("--url", shellArg(url || "https://careers.example.test/jobs/platform"));
  if (sourceDomain.trim()) {
    args.push("--source-domain", shellArg(sourceDomain.trim()));
  }
  if (mode === "search") {
    args.push("--max-results", String(maxResults));
  }
  return args.join(" ");
}

function shellArg(value: string) {
  return `'${value.replaceAll("'", "'\\''")}'`;
}

function LiveIntakeResult({ run }: { run: LiveDiscoveryRun }) {
  return (
    <div className="mt-4 rounded-md border border-border bg-muted/40 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={run.status === "denied" || run.status === "failed" ? "warning" : "success"}>
          {run.status}
        </Badge>
        <span className="font-mono text-xs text-muted-foreground">{run.id}</span>
      </div>
      <div className="mt-3 grid gap-2 text-muted-foreground sm:grid-cols-2">
        <p>
          Extracted: <span className="font-medium text-foreground">{run.extractedCount}</span>
        </p>
        <p>
          Discovered: <span className="font-medium text-foreground">{run.discoveredCount}</span>
        </p>
      </div>
      {run.failure ? <p className="mt-2 text-red-900">{run.failure.detail}</p> : null}
      {run.manualHandoffId ? (
        <p className="mt-2 font-mono text-xs text-muted-foreground">
          handoff {run.manualHandoffId}
        </p>
      ) : null}
      {run.discoveredUrls.length > 0 ? (
        <ul className="mt-3 grid gap-1">
          {run.discoveredUrls.slice(0, 8).map((discoveredUrl) => (
            <li key={discoveredUrl} className="truncate font-mono text-xs text-muted-foreground">
              {discoveredUrl}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function isCapabilityEnabled(
  capabilities: readonly RuntimeCapability[],
  key: RuntimeCapability["key"]
) {
  return capabilities.some((capability) => capability.key === key && capability.enabled);
}

function RuntimeCapabilityPanel({
  capabilities
}: {
  capabilities: readonly RuntimeCapability[];
}) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Capability Gates</CardTitle>
        <Badge tone="info">{capabilities.length} runtime gates</Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        <table className="min-w-[840px] border-separate border-spacing-0 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
              <th className="border-b border-border px-4 py-3 font-semibold">Capability</th>
              <th className="border-b border-border px-4 py-3 font-semibold">State</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Posture</th>
            </tr>
          </thead>
          <tbody>
            {capabilities.map((capability) => (
              <tr key={capability.key}>
                <td className="border-b border-border px-4 py-3 align-top">
                  <p className="font-medium">{capability.label}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">{capability.key}</p>
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <Badge tone={capability.enabled ? "success" : "neutral"}>
                    {capability.enabled ? "enabled" : "disabled"}
                  </Badge>
                </td>
                <td className="max-w-xl border-b border-border px-4 py-3 align-top text-muted-foreground">
                  {capability.detail}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function ReviewQueueTable({ items }: { items: readonly ReviewJobItem[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Reviews Needed</CardTitle>
        <Badge tone="info">{items.length} jobs</Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        {items.length === 0 ? (
          <div className="grid gap-2 px-4 py-8 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">No live reviews are waiting.</p>
            <p>
              Queue approved source URLs in the Operator Console; records that need human review
              will appear here after extraction.
            </p>
          </div>
        ) : (
          <table className="min-w-[1040px] border-separate border-spacing-0 text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
                <th className="border-b border-border px-4 py-3 font-semibold">Job</th>
                <th className="border-b border-border px-4 py-3 font-semibold">Source</th>
                <th className="border-b border-border px-4 py-3 font-semibold">Location</th>
                <th className="border-b border-border px-4 py-3 font-semibold">Pay</th>
                <th className="border-b border-border px-4 py-3 font-semibold">Skills</th>
                <th className="border-b border-border px-4 py-3 font-semibold">Status</th>
                <th className="border-b border-border px-4 py-3 text-right font-semibold">
                  Confidence
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td className="border-b border-border px-4 py-3 align-top">
                    <p className="font-medium">{item.title || "Untitled posting"}</p>
                    <p className="mt-1 text-muted-foreground">
                      {item.company || "Unknown company"}
                    </p>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {item.externalId}
                    </p>
                  </td>
                  <td className="border-b border-border px-4 py-3 align-top">
                    <p className="font-medium">{item.source}</p>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {item.externalId}
                    </p>
                  </td>
                  <td className="border-b border-border px-4 py-3 align-top">
                    <Badge tone={remoteTone(item.remoteType)}>{item.remoteType}</Badge>
                    <p className="mt-2 text-muted-foreground">{item.locations.join(", ")}</p>
                  </td>
                  <td className="border-b border-border px-4 py-3 align-top text-muted-foreground">
                    {formatSalary(item)}
                  </td>
                  <td className="max-w-xs border-b border-border px-4 py-3 align-top">
                    <SkillList skills={[...item.requiredSkills, ...item.preferredSkills]} />
                  </td>
                  <td className="border-b border-border px-4 py-3 align-top">
                    <ReviewStatusBadge status={item.reviewStatus} />
                    <ReviewReasons reasons={item.reviewReasons} />
                  </td>
                  <td className="border-b border-border px-4 py-3 text-right align-top font-mono text-xs">
                    {Math.round(item.extractionConfidence * 100)}%
                    <p className="mt-2 text-muted-foreground">
                      {lowestProvenanceHint(item)?.fieldName ?? "provenance"}
                    </p>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}

function HealthPanel({ health }: { health: ApiHealthStatus }) {
  const Icon = health.state === "healthy" ? CheckCircle2 : TriangleAlert;
  const tone = health.state === "healthy" ? "success" : health.state === "unconfigured" ? "warning" : "danger";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Health / API Status</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "flex size-10 shrink-0 items-center justify-center rounded-md",
              health.state === "healthy" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"
            )}
          >
            <Icon className="size-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <Badge tone={tone}>{health.state}</Badge>
            <p className="mt-2 text-sm font-semibold">{health.label}</p>
            <p className="mt-1 text-sm leading-5 text-muted-foreground">{health.detail}</p>
          </div>
        </div>
        {health.checkedUrl ? (
          <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
            {health.checkedUrl}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function GuardrailPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Guardrails</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm">
        <GuardrailRow icon={LockKeyhole} label="No submission without approval" />
        <GuardrailRow icon={ShieldCheck} label="Generated claims require evidence mapping" />
        <GuardrailRow icon={Activity} label="Every material decision emits an audit event" />
      </CardContent>
    </Card>
  );
}

function SafeModePanel({
  source,
  chainValid
}: {
  source: SettingsSnapshot["source"];
  chainValid: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Safety Status</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm">
        <div className="flex min-h-10 items-center justify-between gap-3">
          <span className="text-muted-foreground">Data source</span>
          <Badge tone={source === "api" ? "info" : "warning"}>{formatDataSource(source)}</Badge>
        </div>
        <div className="flex min-h-10 items-center justify-between gap-3">
          <span className="text-muted-foreground">Audit chain</span>
          <Badge tone={chainValid ? "success" : "danger"}>
            {chainValid ? "valid" : "invalid"}
          </Badge>
        </div>
        <p className="text-sm leading-5 text-muted-foreground">
          Job Search hides administrative controls while keeping guardrail status visible.
        </p>
      </CardContent>
    </Card>
  );
}

function ContextHelpPopover({
  areaLabel,
  title,
  content,
  onClose
}: {
  areaLabel: string;
  title: string;
  content: HelpContent;
  onClose: () => void;
}) {
  return (
    <aside
      aria-label={title}
      className="absolute right-0 top-10 z-40 w-[min(calc(100vw-2rem),390px)] rounded-md border border-border bg-white shadow-lg"
    >
      <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="info">{areaLabel}</Badge>
            <BookOpen className="size-4 text-muted-foreground" aria-hidden="true" />
          </div>
          <h2 className="mt-2 text-sm font-semibold text-foreground">{title}</h2>
        </div>
        <button
          type="button"
          aria-label="Close help"
          onClick={onClose}
          className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      </div>
      <div className="grid max-h-[70vh] gap-4 overflow-y-auto px-4 py-4 text-sm">
        <HelpSection
          icon={Info}
          title="What this view shows"
          items={[content.shows]}
          ordered={false}
        />
        <HelpSection
          icon={ListChecks}
          title="What you can do here"
          items={content.actions}
          ordered
        />
        <HelpSection
          icon={ShieldCheck}
          title="Safety guardrails"
          items={content.guardrails}
          ordered={false}
        />
        <div className="rounded-md border border-border bg-muted/50 px-3 py-3 text-xs leading-5 text-muted-foreground">
          Live intake and packet preparation require explicit runtime flags and source policies.
          Browser execution, credential capture, and external submissions remain blocked.
        </div>
      </div>
    </aside>
  );
}

function HelpSection({
  icon: Icon,
  title,
  items,
  ordered
}: {
  icon: typeof Info;
  title: string;
  items: readonly string[];
  ordered: boolean;
}) {
  const ListTag = ordered ? "ol" : "ul";

  return (
    <section className="grid gap-2">
      <div className="flex items-center gap-2">
        <Icon className="size-4 text-accent" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      </div>
      <ListTag className={cn("grid gap-2 text-muted-foreground", ordered && "list-decimal pl-5", !ordered && "list-disc pl-5")}>
        {items.map((item) => (
          <li key={item} className="leading-5">
            {item}
          </li>
        ))}
      </ListTag>
    </section>
  );
}

function GuardrailRow({
  icon: Icon,
  label
}: {
  icon: typeof LockKeyhole;
  label: string;
}) {
  return (
    <div className="flex min-h-10 items-center gap-3 rounded-md border border-border px-3">
      <Icon className="size-4 text-accent" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

function viewEyebrow(view: DashboardView) {
  if (view === "profile") {
    return "Job search";
  }

  if (view === "admin-sources") {
    return "Administration";
  }

  if (view === "jobs") {
    return "Job search";
  }

  if (view === "reviews-needed") {
    return "Job search";
  }

  if (view === "applications") {
    return "Job search";
  }

  if (view === "admin-approvals") {
    return "Administration";
  }

  if (view === "admin-audit") {
    return "Administration";
  }

  if (view === "admin-system") {
    return "Administration";
  }

  return "Job search";
}

function viewTitle(view: DashboardView) {
  if (view === "profile") {
    return "Profile and preferences";
  }

  if (view === "admin-sources") {
    return "Sources and policy checks";
  }

  if (view === "jobs") {
    return "Jobs";
  }

  if (view === "reviews-needed") {
    return "Reviews needed";
  }

  if (view === "applications") {
    return "Applications";
  }

  if (view === "admin-approvals") {
    return "Approval requests";
  }

  if (view === "admin-audit") {
    return "Audit log";
  }

  if (view === "admin-system") {
    return "System status";
  }

  return "Job search overview";
}

function SkillList({ skills }: { skills: readonly string[] }) {
  if (skills.length === 0) {
    return <span className="text-muted-foreground">none</span>;
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {skills.slice(0, 5).map((skill) => (
        <Badge key={skill} tone="neutral">
          {skill}
        </Badge>
      ))}
      {skills.length > 5 ? <Badge tone="info">+{skills.length - 5}</Badge> : null}
    </div>
  );
}

function ReviewReasons({ reasons }: { reasons: readonly string[] }) {
  if (reasons.length === 0) {
    return <p className="mt-2 text-xs text-muted-foreground">Ready</p>;
  }

  return (
    <div className="mt-2 grid gap-1">
      {reasons.slice(0, 2).map((reason) => (
        <p key={reason} className="max-w-xs text-xs leading-5 text-muted-foreground">
          {reason}
        </p>
      ))}
      {reasons.length > 2 ? (
        <p className="text-xs text-muted-foreground">+{reasons.length - 2} more</p>
      ) : null}
    </div>
  );
}

function ReviewStatusBadge({ status }: { status: ReviewJobItem["reviewStatus"] | JobItem["reviewStatus"] }) {
  if (status === "needs_review") {
    return <Badge tone="warning">needs review</Badge>;
  }

  return <Badge tone="success">ready</Badge>;
}

function ApprovalStatusBadge({ status }: { status: ApprovalRequestStatus }) {
  if (status === "approved") {
    return <Badge tone="success">approved</Badge>;
  }

  if (status === "rejected") {
    return <Badge tone="danger">rejected</Badge>;
  }

  if (status === "needs_changes") {
    return <Badge tone="warning">needs changes</Badge>;
  }

  return <Badge tone="info">pending</Badge>;
}

function ApplicationStatusBadge({ status }: { status: ApplicationItem["status"] }) {
  if (status === "submitted") {
    return <Badge tone="danger">submitted</Badge>;
  }

  if (status === "approved") {
    return <Badge tone="success">approved</Badge>;
  }

  if (status === "ready_for_review") {
    return <Badge tone="warning">ready for review</Badge>;
  }

  if (status === "withdrawn") {
    return <Badge tone="neutral">withdrawn</Badge>;
  }

  return <Badge tone="info">not started</Badge>;
}

function remoteTone(remoteType: ReviewJobItem["remoteType"] | JobItem["remoteType"]) {
  if (remoteType === "remote") {
    return "success";
  }

  if (remoteType === "hybrid") {
    return "info";
  }

  if (remoteType === "unknown") {
    return "warning";
  }

  return "neutral";
}

type SalaryDisplayItem = Pick<
  ReviewJobItem | JobItem,
  "salaryMin" | "salaryMax" | "salaryCurrency"
>;

function formatSalary(item: SalaryDisplayItem) {
  if (item.salaryMin === null && item.salaryMax === null) {
    return "not listed";
  }

  const currency = item.salaryCurrency ? `${item.salaryCurrency} ` : "";

  if (item.salaryMin !== null && item.salaryMax !== null && item.salaryMin !== item.salaryMax) {
    return `${currency}${formatNumber(item.salaryMin)}-${formatNumber(item.salaryMax)}`;
  }

  const salary = item.salaryMin ?? item.salaryMax;
  return salary === null ? "not listed" : `${currency}${formatNumber(salary)}`;
}

function formatCriteriaSalary(item: SearchCriteria) {
  if (item.salaryMin === null && item.salaryMax === null) {
    return "salary open";
  }

  if (item.salaryMin !== null && item.salaryMax !== null) {
    return `${formatNumber(item.salaryMin)}-${formatNumber(item.salaryMax)}`;
  }

  return formatNumber(item.salaryMin ?? item.salaryMax ?? 0);
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

function lowestProvenanceHint(item: ReviewJobItem) {
  return Object.values(item.provenanceHints).sort((left, right) => left.confidence - right.confidence)[0];
}

function formatRequestType(requestType: string) {
  return requestType
    .split("_")
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function summarizePayload(payload: Record<string, unknown>) {
  const entries = Object.entries(payload).slice(0, 3);

  if (entries.length === 0) {
    return "empty payload";
  }

  return entries
    .map(([key, value]) => `${key}: ${formatPayloadValue(value)}`)
    .join("; ");
}

function formatPayloadValue(value: unknown) {
  if (value === null || value === undefined) {
    return "null";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (Array.isArray(value)) {
    return `[${value.length}]`;
  }

  return "{...}";
}

function formatTimestamp(value: string) {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatDataSource(source: string) {
  if (source === "api") {
    return "API data";
  }

  if (source === "local") {
    return "Local fallback";
  }

  return source;
}

function liveJobItems(jobs: readonly JobItem[]) {
  return jobs.filter((job) => !job.synthetic);
}

type PolicyCheckResult = SourcePolicyDecision & {
  decisionSource: "api" | "local";
  detail: string;
};

type ApiPolicyCheckResponse = {
  allowed: boolean;
  reason: string;
  status: SourcePolicy["status"];
  confidence: number;
  reviewStatus: SourcePolicy["reviewStatus"];
  allowedActions: SourcePolicyAction[];
  deniedActions: SourcePolicyAction[];
  policy: Partial<SourcePolicy>;
};

function mergeApiDecision(
  payload: Partial<ApiPolicyCheckResponse>,
  fallback: SourcePolicyDecision
): SourcePolicyDecision {
  const reason = payload.reason ?? payload.policy?.reason ?? fallback.reason;

  return {
    action: fallback.action,
    allowed: typeof payload.allowed === "boolean" ? payload.allowed : fallback.allowed,
    reason,
    policy: {
      ...fallback.policy,
      ...payload.policy,
      status: payload.status ?? payload.policy?.status ?? fallback.policy.status,
      confidence:
        typeof payload.confidence === "number"
          ? payload.confidence
          : payload.policy?.confidence ?? fallback.policy.confidence,
      reviewStatus:
        payload.reviewStatus ?? payload.policy?.reviewStatus ?? fallback.policy.reviewStatus,
      allowedActions:
        payload.allowedActions ?? payload.policy?.allowedActions ?? fallback.policy.allowedActions,
      deniedActions:
        payload.deniedActions ?? payload.policy?.deniedActions ?? fallback.policy.deniedActions,
      reason
    }
  };
}

function ActionList({
  actions,
  emptyLabel,
  tone
}: {
  actions: readonly SourcePolicyAction[];
  emptyLabel: string;
  tone: "success" | "danger" | "neutral";
}) {
  if (actions.length === 0) {
    return <span className="text-muted-foreground">{emptyLabel}</span>;
  }

  return (
    <div className="flex max-w-xs flex-wrap gap-1.5">
      {actions.map((action) => (
        <Badge key={action} tone={tone}>
          {action}
        </Badge>
      ))}
    </div>
  );
}

function formatReviewStatus(status: SourcePolicy["reviewStatus"]) {
  if (status === "approved") {
    return "approved";
  }

  if (status === "prohibited") {
    return "prohibited";
  }

  return "needs review";
}

function PolicyBadge({ status }: { status: SourcePolicy["status"] }) {
  if (status === "allowed") {
    return <Badge tone="success">allowed</Badge>;
  }

  if (status === "blocked") {
    return <Badge tone="danger">blocked</Badge>;
  }

  return <Badge tone="warning">manual only</Badge>;
}

function riskTone(risk: ReviewQueueBucket["risk"]) {
  if (risk === "high") {
    return "danger";
  }

  if (risk === "medium") {
    return "warning";
  }

  return "success";
}
