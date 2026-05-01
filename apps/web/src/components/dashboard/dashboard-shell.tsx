"use client";

import { type FormEvent, useState } from "react";
import {
  Activity,
  Ban,
  BriefcaseBusiness,
  CheckCircle2,
  ClipboardCheck,
  DatabaseZap,
  FileUser,
  Gauge,
  ListChecks,
  LockKeyhole,
  RefreshCcw,
  ScrollText,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  TriangleAlert
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
  dashboardData,
  evaluateSourcePolicyLocally,
  getPipelineTotal,
  getSourcePolicySummary,
  sourcePolicyActions,
  type AuditEvent,
  type ReviewQueueItem as ReviewQueueBucket,
  type SourcePolicy,
  type SourcePolicyAction,
  type SourcePolicyDecision
} from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";
import type { ReviewJobItem, ReviewQueueSnapshot } from "@/lib/review-data";
import type { RuntimeCapability, SettingsSnapshot } from "@/lib/settings-data";

type DashboardView =
  | "dashboard"
  | "candidate"
  | "sources"
  | "jobs"
  | "review"
  | "applications"
  | "audit"
  | "settings";

const navItems = [
  { label: "Dashboard", icon: Gauge, view: "dashboard" },
  { label: "Candidate", icon: FileUser, view: "candidate" },
  { label: "Sources", icon: DatabaseZap, view: "sources" },
  { label: "Jobs", icon: BriefcaseBusiness, view: "jobs" },
  { label: "Review", icon: ClipboardCheck, view: "review" },
  { label: "Applications", icon: ListChecks, view: "applications" },
  { label: "Audit", icon: ScrollText, view: "audit" },
  { label: "Settings", icon: Settings, view: "settings" }
] satisfies Array<{ label: string; icon: typeof Gauge; view?: DashboardView }>;

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
  const [activeView, setActiveView] = useState<DashboardView>("dashboard");
  const policySummary = getSourcePolicySummary(dashboardData.sourcePolicies);
  const pipelineTotal = getPipelineTotal(dashboardData.pipeline);
  const reviewTotal = reviewSnapshot.summary.needsReview;
  const isCandidateView = activeView === "candidate";
  const isSourcesView = activeView === "sources";
  const isJobsView = activeView === "jobs";
  const isReviewView = activeView === "review";
  const isApplicationsView = activeView === "applications";
  const isAuditView = activeView === "audit";
  const isSettingsView = activeView === "settings";

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
                <p className="text-xs text-muted-foreground">Governed workflow</p>
              </div>
            </div>
            <nav aria-label="Primary navigation" className="grid gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = item.view === activeView;
                const isEnabled = Boolean(item.view);

                return (
                  <button
                    key={item.label}
                    type="button"
                    aria-current={isActive ? "page" : undefined}
                    disabled={!isEnabled}
                    onClick={() => {
                      if (item.view) {
                        setActiveView(item.view);
                      }
                    }}
                    className={cn(
                      "flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm font-medium text-muted-foreground",
                      isActive && "bg-muted text-foreground",
                      isEnabled && "hover:bg-muted/70 hover:text-foreground",
                      !isEnabled && "cursor-not-allowed opacity-55"
                    )}
                  >
                    <Icon className="size-4" aria-hidden="true" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
            <div className="mt-auto hidden rounded-card border border-border bg-muted/60 p-3 text-xs text-muted-foreground lg:block">
              <p className="font-medium text-foreground">Foundation mode</p>
              <p className="mt-1 leading-5">
                Mock data only. No crawling, LLM calls, candidate files, or submissions.
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
              <div className="flex flex-wrap gap-2">
                <Badge tone="info">{pipelineTotal} staged jobs</Badge>
                <Badge tone={reviewTotal > 0 ? "warning" : "success"}>
                  {reviewTotal} needs review
                </Badge>
                <Badge tone="success">{policySummary.allowed} approved sources</Badge>
              </div>
            </div>
          </header>

          {isSourcesView ? (
            <SourcesWorkspace policies={dashboardData.sourcePolicies} health={health} />
          ) : isCandidateView ? (
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
          ) : isAuditView ? (
            <AuditWorkspace snapshot={auditSnapshot} health={health} />
          ) : isSettingsView ? (
            <SettingsWorkspace snapshot={settingsSnapshot} health={health} />
          ) : (
            <DashboardOverview
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

function DashboardOverview({
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
        <CandidateProfilePanel snapshot={candidateSnapshot} />
        <JobsPreviewPanel snapshot={jobSnapshot} />
        <SourcePolicyPanel policies={dashboardData.sourcePolicies} />
        <PipelinePanel />
        <ApplicationTrackerPreview snapshot={applicationSnapshot} />
        <RuntimePosturePreview snapshot={settingsSnapshot} />
        <AuditFeed events={dashboardData.auditFeed} />
      </section>
      <section className="grid content-start gap-4">
        <HealthPanel health={health} />
        <ReviewQueuePanel items={reviewSnapshot.buckets} />
        <ApprovalSummaryPanel snapshot={approvalSnapshot} />
        <AuditSummaryPanel snapshot={auditSnapshot} />
        <GuardrailPanel />
      </section>
    </div>
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
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Candidate Profile</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>{snapshot.source}</Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div>
          <p className="text-lg font-semibold">{snapshot.profile.profileName}</p>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            {snapshot.profile.summary ?? "No synthetic summary provided."}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <MetricTile label="Evidence" value={snapshot.evidence.length} />
          <MetricTile label="Criteria" value={snapshot.searchCriteria.length} />
          <MetricTile label="Synthetic" value={snapshot.profile.synthetic ? 1 : 0} />
        </div>
        <p className="break-words rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
          {snapshot.profile.id}
        </p>
      </CardContent>
    </Card>
  );
}

function CandidateEvidencePanel({ evidence }: { evidence: readonly CandidateEvidence[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Evidence Bank</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {evidence.map((item) => (
          <div key={item.id} className="rounded-md border border-border px-3 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{item.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{item.evidenceType}</p>
              </div>
              {item.synthetic ? <Badge tone="info">synthetic</Badge> : null}
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
        ))}
      </CardContent>
    </Card>
  );
}

function CandidateCriteriaPanel({ criteria }: { criteria: readonly SearchCriteria[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Search Criteria</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {criteria.map((item) => (
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
        ))}
      </CardContent>
    </Card>
  );
}

function CandidateSafetyPanel({ snapshot }: { snapshot: CandidateWorkspaceSnapshot }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Candidate Safety</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <p className="text-sm leading-5 text-muted-foreground">{snapshot.safetyNote}</p>
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
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <JobCatalogTable jobs={snapshot.jobs} />
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

function SettingsWorkspace({
  snapshot,
  health
}: {
  snapshot: SettingsSnapshot;
  health: ApiHealthStatus;
}) {
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <RuntimeCapabilityPanel capabilities={snapshot.runtime.capabilities} />
      </section>
      <section className="grid content-start gap-4">
        <RuntimeSettingsPanel snapshot={snapshot} />
        <HealthPanel health={health} />
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
  return (
    <div className="grid gap-4 p-4 sm:p-6 xl:grid-cols-[1.55fr_0.95fr]">
      <section className="grid gap-4">
        <ReviewQueueTable items={reviewSnapshot.items} />
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
        <PolicyCheckPanel policies={policies} />
        <HealthPanel health={health} />
        <GuardrailPanel />
      </section>
    </div>
  );
}

function SourcePolicyPanel({ policies }: { policies: readonly SourcePolicy[] }) {
  const summary = getSourcePolicySummary(policies);

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Source Policy Status</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Badge tone="success">Allowed {summary.allowed}</Badge>
          <Badge tone="warning">Manual {summary.manualOnly}</Badge>
          <Badge tone="danger">Blocked {summary.blocked}</Badge>
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        <table className="min-w-full border-separate border-spacing-0 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
              <th className="border-b border-border px-4 py-3 font-semibold">Source</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Domain</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Type</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Status</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Actions</th>
              <th className="border-b border-border px-4 py-3 text-right font-semibold">
                Confidence
              </th>
            </tr>
          </thead>
          <tbody>
            {policies.map((policy) => (
              <tr key={policy.name} className="border-b border-border last:border-0">
                <td className="border-b border-border px-4 py-3 font-medium">{policy.name}</td>
                <td className="border-b border-border px-4 py-3 text-muted-foreground">
                  {policy.domain}
                </td>
                <td className="border-b border-border px-4 py-3 text-muted-foreground">
                  {policy.type}
                </td>
                <td className="border-b border-border px-4 py-3">
                  <PolicyBadge status={policy.status} />
                </td>
                <td className="border-b border-border px-4 py-3 text-muted-foreground">
                  {policy.allowedActions.length > 0 ? policy.allowedActions.join(", ") : "none"}
                </td>
                <td className="border-b border-border px-4 py-3 text-right font-mono text-xs">
                  {typeof policy.confidence === "number"
                    ? `${Math.round(policy.confidence * 100)}%`
                    : "review"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
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
            Policy posture is local fixture data unless the API check is configured.
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
        detail: "NEXT_PUBLIC_API_BASE_URL is not configured; synthetic local policy was used."
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

function PipelinePanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Application Pipeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-5">
          {dashboardData.pipeline.map((column) => (
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
        <CardTitle>Review Queue</CardTitle>
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
  const visibleJobs = snapshot.jobs.slice(0, 4);

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Job Catalog</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Badge tone={snapshot.source === "api" ? "info" : "warning"}>{snapshot.source}</Badge>
          <Badge tone="info">{snapshot.summary.total} synthetic records</Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3">
        {visibleJobs.map((job) => (
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
                {job.fixtureName ?? job.externalId}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 md:justify-end">
              <Badge tone={remoteTone(job.remoteType)}>{job.remoteType}</Badge>
              <ReviewStatusBadge status={job.reviewStatus} />
            </div>
          </div>
        ))}
        <p className="text-sm leading-5 text-muted-foreground">{snapshot.detail}</p>
      </CardContent>
    </Card>
  );
}

function ApplicationTrackerPreview({ snapshot }: { snapshot: ApplicationSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Application Tracker</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Badge tone={snapshot.source === "api" ? "info" : "warning"}>{snapshot.source}</Badge>
          <Badge tone={snapshot.summary.externalSideEffects > 0 ? "danger" : "success"}>
            {snapshot.summary.externalSideEffects} external side effects
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-2 sm:grid-cols-4">
          <MetricTile label="Tracked" value={snapshot.summary.total} />
          <MetricTile label="Review" value={snapshot.summary.inReview} />
          <MetricTile label="Approved" value={snapshot.summary.approved} />
          <MetricTile label="Submitted" value={snapshot.summary.submitted} />
        </div>
        <p className="text-sm leading-5 text-muted-foreground">{snapshot.detail}</p>
      </CardContent>
    </Card>
  );
}

function RuntimePosturePreview({ snapshot }: { snapshot: SettingsSnapshot }) {
  const disabledCount = snapshot.runtime.capabilities.filter((capability) => !capability.enabled).length;

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Runtime Posture</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Badge tone={snapshot.source === "api" ? "info" : "warning"}>{snapshot.source}</Badge>
          <Badge tone="success">{disabledCount} disabled capabilities</Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-2 sm:grid-cols-4">
          <MetricTile label="Audit Schema" value={snapshot.runtime.auditSchemaVersion} />
          <MetricTile label="DB Config" value={snapshot.runtime.databaseConfigured ? 1 : 0} />
          <MetricTile label="Redis Config" value={snapshot.runtime.redisConfigured ? 1 : 0} />
          <MetricTile
            label="Integrations"
            value={snapshot.runtime.externalIntegrationsEnabled ? 1 : 0}
          />
        </div>
        <p className="text-sm leading-5 text-muted-foreground">{snapshot.detail}</p>
      </CardContent>
    </Card>
  );
}

function JobSummaryPanel({ snapshot }: { snapshot: JobCatalogSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Job Summary</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>{snapshot.source}</Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Total" value={snapshot.summary.total} />
          <MetricTile label="Ready" value={snapshot.summary.ready} />
          <MetricTile label="Review" value={snapshot.summary.needsReview} />
          <MetricTile label="Remote" value={snapshot.summary.remote} />
          <MetricTile label="Hybrid" value={snapshot.summary.hybrid} />
          <MetricTile label="Onsite" value={snapshot.summary.onsite} />
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

function ApplicationSummaryPanel({ snapshot }: { snapshot: ApplicationSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Application Summary</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>{snapshot.source}</Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Tracked" value={snapshot.summary.total} />
          <MetricTile label="Not Started" value={snapshot.summary.notStarted} />
          <MetricTile label="Review" value={snapshot.summary.inReview} />
          <MetricTile label="Approved" value={snapshot.summary.approved} />
          <MetricTile label="Submitted" value={snapshot.summary.submitted} />
          <MetricTile label="Side Effects" value={snapshot.summary.externalSideEffects} />
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
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>{snapshot.source}</Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Audit Schema" value={snapshot.runtime.auditSchemaVersion} />
          <MetricTile label="DB Config" value={snapshot.runtime.databaseConfigured ? 1 : 0} />
          <MetricTile label="Redis Config" value={snapshot.runtime.redisConfigured ? 1 : 0} />
          <MetricTile label="Secrets" value={snapshot.runtime.secretsLoaded ? 1 : 0} />
          <MetricTile
            label="External"
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
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Review Summary</CardTitle>
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>{snapshot.source}</Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-3 gap-2">
          <MetricTile label="Total" value={snapshot.summary.total} />
          <MetricTile label="Ready" value={snapshot.summary.ready} />
          <MetricTile label="Review" value={snapshot.summary.needsReview} />
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

function ApprovalSummaryPanel({ snapshot }: { snapshot: ApprovalSnapshot }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Approval Gates</CardTitle>
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
          Manual approval records only. No autofill, submit, or external side effects.
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
        <Badge tone={snapshot.source === "api" ? "info" : "warning"}>{snapshot.source}</Badge>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid grid-cols-4 gap-2">
          <MetricTile label="Total" value={snapshot.summary.total} />
          <MetricTile label="Pending" value={snapshot.summary.pending} />
          <MetricTile label="Approved" value={snapshot.summary.approved} />
          <MetricTile label="Changes" value={snapshot.summary.needsChanges} />
        </div>
        <div className="grid gap-3">
          {snapshot.requests.map((request) => (
            <ApprovalRequestRow key={request.id} request={request} />
          ))}
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
        {request.synthetic ? <Badge tone="info">synthetic</Badge> : null}
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
        <CardTitle>Synthetic Job Postings</CardTitle>
        <Badge tone="info">{jobs.length} synthetic records</Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        <table className="min-w-[1100px] border-separate border-spacing-0 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
              <th className="border-b border-border px-4 py-3 font-semibold">Job</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Source</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Location</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Comp</th>
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
                    {job.fixtureName ?? "synthetic fixture"}
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
                  <p className="mt-2 text-muted-foreground">
                    {job.synthetic ? "synthetic" : "external"}
                  </p>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function ApplicationTable({ applications }: { applications: readonly ApplicationItem[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle>Application Records</CardTitle>
        <Badge tone="info">{applications.length} tracked records</Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        {applications.length === 0 ? (
          <div className="grid gap-3 px-4 py-8">
            <p className="text-sm font-medium">No application records have been created.</p>
            <p className="max-w-2xl text-sm leading-5 text-muted-foreground">
              Phase 1 keeps applications read-only: no drafting packet, autofill, browser handoff,
              or submit operation is available from this workspace.
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
                        submit {application.safety.submitPerformed ? "yes" : "no"}
                      </Badge>
                      <Badge tone={application.safety.autofillPerformed ? "danger" : "success"}>
                        autofill {application.safety.autofillPerformed ? "yes" : "no"}
                      </Badge>
                      {application.synthetic ? <Badge tone="info">synthetic</Badge> : null}
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
        <CardTitle>Extracted Job Review</CardTitle>
        <Badge tone="info">{items.length} synthetic records</Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        <table className="min-w-[1040px] border-separate border-spacing-0 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.12em] text-muted-foreground">
              <th className="border-b border-border px-4 py-3 font-semibold">Job</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Source</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Location</th>
              <th className="border-b border-border px-4 py-3 font-semibold">Comp</th>
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
                  <p className="mt-1 text-muted-foreground">{item.company || "Unknown company"}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">{item.externalId}</p>
                </td>
                <td className="border-b border-border px-4 py-3 align-top">
                  <p className="font-medium">{item.source}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    {item.fixtureName ?? item.dataOrigin}
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
      </CardContent>
    </Card>
  );
}

function AuditFeed({ events }: { events: readonly AuditEvent[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit Feed</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        {events.map((event) => (
          <div key={event.id} className="grid gap-2 sm:grid-cols-[80px_1fr]">
            <time className="font-mono text-xs text-muted-foreground">{event.occurredAt}</time>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={event.actor === "system" ? "info" : "neutral"}>{event.actor}</Badge>
                <p className="text-sm font-semibold">{event.action}</p>
              </div>
              <p className="mt-1 break-words text-sm text-muted-foreground">{event.subject}</p>
              <p className="mt-1 break-words font-mono text-xs text-muted-foreground">
                {event.provenance}
              </p>
            </div>
          </div>
        ))}
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
  if (view === "candidate") {
    return "Candidate workspace";
  }

  if (view === "sources") {
    return "Source governance";
  }

  if (view === "jobs") {
    return "Job catalog";
  }

  if (view === "review") {
    return "Review queue";
  }

  if (view === "applications") {
    return "Application tracker";
  }

  if (view === "audit") {
    return "Audit trail";
  }

  if (view === "settings") {
    return "Runtime settings";
  }

  return "Operations dashboard";
}

function viewTitle(view: DashboardView) {
  if (view === "candidate") {
    return "Synthetic candidate profile";
  }

  if (view === "sources") {
    return "Source registry and policy checks";
  }

  if (view === "jobs") {
    return "Synthetic job postings";
  }

  if (view === "review") {
    return "Extracted job review";
  }

  if (view === "applications") {
    return "Read-only application records";
  }

  if (view === "audit") {
    return "Hash-chained audit events";
  }

  if (view === "settings") {
    return "Safe runtime posture";
  }

  return "Governed application workflow";
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
