import { describe, expect, it } from "vitest";
import {
  dashboardData,
  evaluateSourcePolicyLocally,
  getPipelineTotal,
  getReviewQueueTotal,
  getSourcePolicySummary,
  sourcePolicyActions
} from "./dashboard-data";

describe("dashboardData", () => {
  it("summarizes source policy decisions without counting blocked sources as allowed", () => {
    expect(getSourcePolicySummary(dashboardData.sourcePolicies)).toEqual({
      allowed: 8,
      manualOnly: 2,
      blocked: 2
    });
  });

  it("keeps pipeline and review totals deterministic for shell metrics", () => {
    expect(getPipelineTotal(dashboardData.pipeline)).toBe(38);
    expect(getReviewQueueTotal(dashboardData.reviewQueue)).toBe(17);
  });

  it("ships audit events with immutable labels and source subjects", () => {
    expect(dashboardData.auditFeed).toHaveLength(5);
    expect(dashboardData.auditFeed[0]).toMatchObject({
      actor: "system",
      subject: "greenhouse-intake"
    });
    expect(dashboardData.auditFeed.every((event) => event.provenance !== "")).toBe(true);
  });

  it("denies every action for unknown sources until a reviewer approves them", () => {
    const decision = evaluateSourcePolicyLocally({
      source: "Unlisted Board",
      domain: "jobs.unlisted.example",
      action: "extract"
    });

    expect(decision.allowed).toBe(false);
    expect(decision.policy.status).toBe("manual_only");
    expect(decision.policy.allowedActions).toEqual([]);
    expect(decision.policy.deniedActions).toEqual(sourcePolicyActions);
  });

  it("denies submit for prohibited sources even when requested by domain", () => {
    const decision = evaluateSourcePolicyLocally({
      domain: "linkedin.com",
      action: "submit"
    });

    expect(decision.allowed).toBe(false);
    expect(decision.policy.status).toBe("blocked");
    expect(decision.policy.deniedActions).toContain("submit");
    expect(decision.reason).toContain("official integration");
  });

  it("allows bounded public intake for approved UK job boards", () => {
    const decision = evaluateSourcePolicyLocally({
      domain: "reed.co.uk",
      action: "discover"
    });

    expect(decision.allowed).toBe(true);
    expect(decision.policy.status).toBe("allowed");
    expect(decision.policy.deniedActions).toContain("submit");
  });
});
