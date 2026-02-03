import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { ExperimentType } from "@/types/experiment";
import { Server, Network } from "lucide-react";

interface TypeBadgeProps {
  type: ExperimentType;
  className?: string;
  showIcon?: boolean;
}

const typeConfig: Record<ExperimentType, { label: string; icon: typeof Server }> = {
  centralized: {
    label: "Centralized",
    icon: Server,
  },
  federated: {
    label: "Federated",
    icon: Network,
  },
};

export function TypeBadge({ type, className, showIcon = true }: TypeBadgeProps) {
  const config = typeConfig[type];
  const Icon = config.icon;
  
  return (
    <Badge 
      variant="outline" 
      className={cn("font-medium", className)}
    >
      {showIcon && <Icon className="mr-1 h-3 w-3" />}
      {config.label}
    </Badge>
  );
}
