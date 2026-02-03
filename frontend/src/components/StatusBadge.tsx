import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { ExperimentStatus } from "@/types/experiment";

interface StatusBadgeProps {
  status: ExperimentStatus;
  className?: string;
}

const statusConfig: Record<ExperimentStatus, { label: string; className: string }> = {
  pending: {
    label: "Pending",
    className: "bg-muted text-muted-foreground hover:bg-muted",
  },
  running: {
    label: "Running",
    className: "bg-running text-running-foreground hover:bg-running animate-pulse-slow",
  },
  completed: {
    label: "Completed",
    className: "bg-success text-success-foreground hover:bg-success",
  },
  failed: {
    label: "Failed",
    className: "bg-destructive text-destructive-foreground hover:bg-destructive",
  },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];
  
  return (
    <Badge className={cn(config.className, className)} variant="secondary">
      {config.label}
    </Badge>
  );
}
