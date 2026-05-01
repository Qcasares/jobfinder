import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { getApplicationSnapshot } from "@/lib/application-data";
import { getApprovalSnapshot } from "@/lib/approval-data";
import { getAuditSnapshot } from "@/lib/audit-data";
import { getCandidateWorkspaceSnapshot } from "@/lib/candidate-data";
import { getApiHealth } from "@/lib/health";
import { getJobCatalogSnapshot } from "@/lib/job-data";
import { getReviewQueueSnapshot } from "@/lib/review-data";
import { getSettingsSnapshot } from "@/lib/settings-data";

export default async function Page() {
  const [
    health,
    candidateSnapshot,
    jobSnapshot,
    reviewSnapshot,
    approvalSnapshot,
    applicationSnapshot,
    auditSnapshot,
    settingsSnapshot
  ] = await Promise.all([
      getApiHealth(),
      getCandidateWorkspaceSnapshot(),
      getJobCatalogSnapshot(),
      getReviewQueueSnapshot(),
      getApprovalSnapshot(),
      getApplicationSnapshot(),
      getAuditSnapshot(),
      getSettingsSnapshot()
    ]);

  return (
    <DashboardShell
      health={health}
      candidateSnapshot={candidateSnapshot}
      jobSnapshot={jobSnapshot}
      reviewSnapshot={reviewSnapshot}
      approvalSnapshot={approvalSnapshot}
      applicationSnapshot={applicationSnapshot}
      auditSnapshot={auditSnapshot}
      settingsSnapshot={settingsSnapshot}
    />
  );
}
