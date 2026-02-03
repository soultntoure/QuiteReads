import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useMetrics } from "@/hooks/use-metrics";
import { Skeleton } from "@/components/ui/skeleton";
import type { ExperimentType } from "@/types/experiment";

interface ConvergenceChartProps {
  experimentId: string;
  experimentType: ExperimentType;
}

type MetricType = "rmse" | "mae";

interface ChartDataPoint {
  round: number;
  value?: number;
  [key: string]: number | undefined;
}

interface ProcessedChartData {
  data: ChartDataPoint[];
  clientIds: string[];
}

// Chart colors from design system
const CHART_COLORS = [
  "hsl(239, 84%, 67%)",  // chart-1 (primary/indigo)
  "hsl(160, 84%, 39%)",  // chart-2 (success/green)
  "hsl(38, 92%, 50%)",   // chart-3 (warning/amber)
  "hsl(217, 91%, 60%)",  // chart-4 (running/blue)
  "hsl(280, 65%, 60%)",  // chart-5 (purple)
  "hsl(0, 84%, 60%)",    // destructive/red
  "hsl(180, 70%, 45%)",  // cyan
  "hsl(45, 93%, 47%)",   // gold
];

export function ConvergenceChart({ experimentId, experimentType }: ConvergenceChartProps) {
  const [metricType, setMetricType] = useState<MetricType>("rmse");
  const [showPerClient, setShowPerClient] = useState(false);
  
  const { data, isLoading, isError } = useMetrics(experimentId, { name: metricType });
  
  // Process data for chart
  const chartData = useMemo<ProcessedChartData>(() => {
    if (!data?.metrics.length) return { data: [], clientIds: [] };
    
    const metrics = data.metrics;
    
    if (experimentType === "federated" && showPerClient) {
      // Group by round and show per-client values
      const roundMap = new Map<number, ChartDataPoint>();
      const clientIds = new Set<string>();
      
      metrics.forEach((m) => {
        if (m.round_number === null) return;
        const round = m.round_number;
        const clientId = m.client_id || "aggregate";
        clientIds.add(clientId);
        
        if (!roundMap.has(round)) {
          roundMap.set(round, { round });
        }
        roundMap.get(round)![clientId] = m.value;
      });
      
      return {
        data: Array.from(roundMap.values()).sort((a, b) => a.round - b.round),
        clientIds: Array.from(clientIds).sort(),
      };
    }
    
    // For centralized or aggregated federated view
    const grouped = new Map<number, number[]>();
    
    metrics.forEach((m) => {
      const key = m.round_number ?? 0;
      if (!grouped.has(key)) {
        grouped.set(key, []);
      }
      grouped.get(key)!.push(m.value);
    });
    
    const processedData = Array.from(grouped.entries())
      .map(([round, values]) => ({
        round,
        value: values.reduce((a, b) => a + b, 0) / values.length,
      }))
      .sort((a, b) => a.round - b.round);
    
    return { data: processedData, clientIds: [] };
  }, [data, experimentType, showPerClient]);
  
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Training Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }
  
  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Training Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Failed to load metrics</p>
        </CardContent>
      </Card>
    );
  }
  
  const hasData = chartData.data.length > 0;
  
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-lg">Training Progress</CardTitle>
          <div className="flex items-center gap-4">
            <Tabs value={metricType} onValueChange={(v) => setMetricType(v as MetricType)}>
              <TabsList>
                <TabsTrigger value="rmse">RMSE</TabsTrigger>
                <TabsTrigger value="mae">MAE</TabsTrigger>
              </TabsList>
            </Tabs>
            
            {experimentType === "federated" && (
              <div className="flex items-center gap-2">
                <Switch
                  id="per-client"
                  checked={showPerClient}
                  onCheckedChange={setShowPerClient}
                />
                <Label htmlFor="per-client" className="text-sm">
                  Per-client
                </Label>
              </div>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="flex h-[300px] items-center justify-center text-muted-foreground">
            No metrics data available yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData.data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="round"
                label={{
                  value: experimentType === "federated" ? "Round" : "Epoch",
                  position: "insideBottomRight",
                  offset: -10,
                }}
                className="text-xs"
              />
              <YAxis
                label={{
                  value: metricType.toUpperCase(),
                  angle: -90,
                  position: "insideLeft",
                }}
                className="text-xs"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
                labelStyle={{ color: "hsl(var(--foreground))" }}
              />
              
              {experimentType === "federated" && showPerClient && chartData.clientIds.length > 0 ? (
                <>
                  <Legend />
                  {chartData.clientIds.map((clientId, index) => (
                    <Line
                      key={clientId}
                      type="monotone"
                      dataKey={clientId}
                      stroke={CHART_COLORS[index % CHART_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  ))}
                </>
              ) : (
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={CHART_COLORS[0]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                  name={metricType.toUpperCase()}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
