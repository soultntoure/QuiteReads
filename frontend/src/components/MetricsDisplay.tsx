import type { ExperimentMetricsSchema } from "@/types/experiment";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingDown, Clock, Target } from "lucide-react";

interface MetricsDisplayProps {
  metrics: ExperimentMetricsSchema;
}

function formatTime(seconds: number | null): string {
  if (seconds === null) return "-";
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  }
  return `${secs}s`;
}

function formatMetric(value: number | null): string {
  if (value === null) return "-";
  return value.toFixed(4);
}

export function MetricsDisplay({ metrics }: MetricsDisplayProps) {
  const items = [
    {
      label: "Final RMSE",
      value: formatMetric(metrics.final_rmse),
      icon: TrendingDown,
      description: "Root Mean Square Error",
    },
    {
      label: "Final MAE",
      value: formatMetric(metrics.final_mae),
      icon: Target,
      description: "Mean Absolute Error",
    },
    {
      label: "Training Time",
      value: formatTime(metrics.training_time_seconds),
      icon: Clock,
      description: "Total training duration",
    },
  ];
  
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Final Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-3">
          {items.map((item) => (
            <div
              key={item.label}
              className="flex items-start gap-3 rounded-lg border p-4"
            >
              <div className="rounded-md bg-primary/10 p-2">
                <item.icon className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  {item.label}
                </p>
                <p className="text-2xl font-bold tabular-nums">
                  {item.value}
                </p>
                <p className="text-xs text-muted-foreground">
                  {item.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
