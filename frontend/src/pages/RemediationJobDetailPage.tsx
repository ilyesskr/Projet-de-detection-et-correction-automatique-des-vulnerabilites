import { useNavigate, useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { PageHeader } from "@/components/layout/PageHeader";
import { ErrorState } from "@/components/feedback/ErrorState";
import { JobStatusBadge } from "@/components/badges/JobStatusBadge";
import { LifecycleStepper } from "@/components/remediation/LifecycleStepper";
import { JobActions } from "@/components/remediation/JobActions";
import { JobAuditTrail } from "@/components/remediation/JobAuditTrail";

import { useRemediationJob } from "@/hooks/queries/useRemediation";
import { dash, formatDateTime } from "@/lib/format";

export default function RemediationJobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const query = useRemediationJob(jobId);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <Button
        variant="ghost"
        size="sm"
        className="mb-3 -ml-2 text-muted-foreground hover:text-slate-100"
        onClick={() => navigate("/remediation")}
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to remediation jobs
      </Button>

      {query.isError ? (
        <ErrorState
          error={query.error}
          onRetry={() => query.refetch()}
          title="Couldn't load job"
        />
      ) : query.isLoading || !query.data ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-32" />
          <Skeleton className="h-48" />
        </div>
      ) : (
        <>
          <PageHeader
            title={`Job ${query.data.id.slice(0, 8)}…`}
            description={`${query.data.action} on asset ${query.data.asset_id}`}
            actions={<JobStatusBadge status={query.data.status} />}
          />

          <Card className="mb-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Lifecycle</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <LifecycleStepper status={query.data.status} />
              <JobActions job={query.data} />
              {query.data.error_message && (
                <div className="text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2">
                  <span className="font-medium">Error:</span>{" "}
                  {query.data.error_message}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 mb-6">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Job</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-1.5">
                <DetailRow label="Job id"  value={query.data.id} mono />
                <DetailRow
                  label="Asset"
                  value={
                    <Link
                      to={`/assets/${query.data.asset_id}`}
                      className="font-mono text-xs underline-offset-2 hover:underline text-slate-200"
                    >
                      {query.data.asset_id.slice(0, 8)}…
                    </Link>
                  }
                />
                <DetailRow
                  label="Vulnerability id"
                  value={dash(query.data.vulnerability_id)}
                  mono
                />
                <DetailRow label="Engine"  value={query.data.engine} />
                <DetailRow label="Action"  value={query.data.action} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Provenance & AWX</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-1.5">
                <DetailRow label="Created by"  value={query.data.created_by} />
                <DetailRow label="Approved by" value={dash(query.data.approved_by)} />
                <DetailRow
                  label="Approved at"
                  value={formatDateTime(query.data.approved_at)}
                />
                <DetailRow
                  label="AWX template"
                  value={dash(query.data.awx_job_template_id)}
                  mono
                />
                <DetailRow
                  label="AWX job id"
                  value={dash(query.data.awx_job_id)}
                  mono
                />
                <DetailRow
                  label="Created"
                  value={formatDateTime(query.data.created_at)}
                />
                <DetailRow
                  label="Updated"
                  value={formatDateTime(query.data.updated_at)}
                />
              </CardContent>
            </Card>
          </div>

          <h2 className="text-lg font-semibold tracking-tight text-slate-100 mb-3">
            Audit trail
          </h2>
          <JobAuditTrail jobId={query.data.id} />
        </>
      )}
    </div>
  );
}

interface DetailRowProps {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}
function DetailRow({ label, value, mono }: DetailRowProps) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? "font-mono text-xs text-right" : "text-right"}>
        {value}
      </span>
    </div>
  );
}
