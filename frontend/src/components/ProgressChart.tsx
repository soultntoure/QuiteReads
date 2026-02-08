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
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useMetrics } from "@/hooks/use-metrics";
import { LineChart as LineChartIcon, AlertCircle, Table2, Award } from "lucide-react";
import type { ExperimentType, MetricResponse } from "@/types/experiment";

interface ProgressChartProps {
    experimentId: string;
    experimentType: ExperimentType;
}

// Chart colors aligned with design system
const CHART_COLORS = {
    training_loss: "hsl(38, 92%, 50%)",    // Amber for training loss
    validation_rmse: "hsl(239, 84%, 67%)", // Indigo for validation RMSE
    validation_mae: "hsl(160, 84%, 39%)",  // Teal for validation MAE
    // Per-client colors (when showing per-client breakdown)
    clients: [
        "hsl(239, 84%, 67%)",
        "hsl(160, 84%, 39%)",
        "hsl(38, 92%, 50%)",
        "hsl(217, 91%, 60%)",
        "hsl(280, 65%, 60%)",
        "hsl(0, 84%, 60%)",
        "hsl(180, 70%, 45%)",
        "hsl(45, 93%, 47%)",
    ],
};

interface ChartDataPoint {
    epoch: number;
    training_loss?: number;
    validation_rmse?: number;
    validation_mae?: number;
    [key: string]: number | undefined;
}

interface TableRowData {
    epoch: number;
    training_loss: number | null;
    validation_rmse: number | null;
    validation_mae: number | null;
    isBest?: boolean;
}

export function ProgressChart({ experimentId, experimentType }: ProgressChartProps) {
    const [showPerClient, setShowPerClient] = useState(false);

    // Fetch all metrics for the experiment
    const { data: allMetricsData, isLoading, isError } = useMetrics(experimentId);

    // Process the data for the chart
    const { chartData, tableData } = useMemo(() => {
        if (!allMetricsData?.metrics.length) {
            return { chartData: { data: [], clientIds: [] }, tableData: [] };
        }

        const metrics = allMetricsData.metrics;
        const epochMap = new Map<number, ChartDataPoint>();
        const clientIds = new Set<string>();

        // Group metrics by epoch/round
        metrics.forEach((m: MetricResponse) => {
            const epoch = m.round_number ?? 0;

            if (!epochMap.has(epoch)) {
                epochMap.set(epoch, { epoch });
            }

            const point = epochMap.get(epoch)!;
            const context = m.context || "validation";

            // Handle different metric types based on context
            // For loss: accept "training" or "centralized_test" context
            if (m.name === "loss" && (context === "training" || context === "centralized_test")) {
                // Prefer training context, but use centralized_test if no training
                if (context === "training" || point.training_loss === undefined) {
                    point.training_loss = m.value;
                }
            } else if (m.name === "rmse") {
                if (experimentType === "federated" && showPerClient && m.client_id) {
                    // Per-client RMSE for federated
                    const key = `rmse_${m.client_id}`;
                    point[key] = m.value;
                    clientIds.add(m.client_id);
                } else if (context === "validation" || context === "centralized_test" || context === "client_aggregated" || !m.client_id) {
                    // Aggregated or centralized RMSE
                    point.validation_rmse = m.value;
                }
            } else if (m.name === "mae") {
                if (experimentType === "federated" && showPerClient && m.client_id) {
                    // Per-client MAE for federated
                    const key = `mae_${m.client_id}`;
                    point[key] = m.value;
                    clientIds.add(m.client_id);
                } else if (context === "validation" || context === "centralized_test" || context === "client_aggregated" || !m.client_id) {
                    // Aggregated or centralized MAE
                    point.validation_mae = m.value;
                }
            }
        });

        const sortedData = Array.from(epochMap.values()).sort((a, b) => a.epoch - b.epoch);

        // Create table data
        const tableRows: TableRowData[] = sortedData.map(d => ({
            epoch: d.epoch,
            training_loss: d.training_loss ?? null,
            validation_rmse: d.validation_rmse ?? null,
            validation_mae: d.validation_mae ?? null,
        }));

        // Find best RMSE epoch
        let bestRmse = Infinity;
        let bestEpoch = -1;
        tableRows.forEach((row) => {
            if (row.validation_rmse !== null && row.validation_rmse < bestRmse) {
                bestRmse = row.validation_rmse;
                bestEpoch = row.epoch;
            }
        });

        // Mark best
        tableRows.forEach((row) => {
            row.isBest = row.epoch === bestEpoch;
        });

        return {
            chartData: {
                data: sortedData,
                clientIds: Array.from(clientIds).sort(),
            },
            tableData: tableRows,
        };
    }, [allMetricsData, experimentType, showPerClient]);

    if (isLoading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-[350px] w-full" />
                <Skeleton className="h-[200px] w-full" />
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex h-[350px] items-center justify-center">
                <div className="text-center text-muted-foreground">
                    <AlertCircle className="mx-auto h-12 w-12 opacity-30 mb-3" />
                    <p>Failed to load training progress</p>
                </div>
            </div>
        );
    }

    const hasData = chartData.data.length > 0;
    const xAxisLabel = experimentType === "federated" ? "Round" : "Epoch";
    const epochLabel = experimentType === "federated" ? "Round" : "Epoch";

    return (
        <div className="space-y-6">
            {/* Controls */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <LineChartIcon className="h-5 w-5 text-muted-foreground" />
                    <span className="text-sm font-medium">
                        Training & Validation Progress
                    </span>
                </div>

                {experimentType === "federated" && (
                    <div className="flex items-center gap-2">
                        <Switch
                            id="per-client-progress"
                            checked={showPerClient}
                            onCheckedChange={setShowPerClient}
                        />
                        <Label htmlFor="per-client-progress" className="text-sm">
                            Per-client breakdown
                        </Label>
                    </div>
                )}
            </div>

            {/* Chart */}
            {!hasData ? (
                <div className="flex h-[350px] items-center justify-center bg-muted/30 rounded-lg border border-dashed">
                    <div className="text-center text-muted-foreground">
                        <LineChartIcon className="mx-auto h-12 w-12 opacity-30 mb-3" />
                        <p>No training progress data available yet</p>
                        <p className="text-sm mt-1">Start the experiment to see progress</p>
                    </div>
                </div>
            ) : (
                <>
                    {/* Line Chart */}
                    <Card>
                        <CardContent className="pt-6">
                            <ResponsiveContainer width="100%" height={350}>
                                <LineChart
                                    data={chartData.data}
                                    margin={{ top: 5, right: 30, left: 20, bottom: 25 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                                    <XAxis
                                        dataKey="epoch"
                                        tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                                        tickLine={false}
                                        label={{
                                            value: xAxisLabel,
                                            position: "insideBottomRight",
                                            offset: -10,
                                            fill: "hsl(var(--muted-foreground))",
                                            fontSize: 12,
                                        }}
                                    />
                                    <YAxis
                                        tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                                        tickLine={false}
                                        label={{
                                            value: "Value",
                                            angle: -90,
                                            position: "insideLeft",
                                            fill: "hsl(var(--muted-foreground))",
                                            fontSize: 12,
                                        }}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "hsl(var(--card))",
                                            border: "1px solid hsl(var(--border))",
                                            borderRadius: "var(--radius)",
                                            boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                                        }}
                                        labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
                                        formatter={(value: number, name: string) => [
                                            value.toFixed(4),
                                            name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
                                        ]}
                                        labelFormatter={(label) => `${xAxisLabel} ${label}`}
                                    />
                                    <Legend
                                        wrapperStyle={{ paddingTop: 20 }}
                                        formatter={(value) => (
                                            <span className="text-sm font-medium">
                                                {value.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                                            </span>
                                        )}
                                    />

                                    {/* Training Loss Line */}
                                    <Line
                                        type="monotone"
                                        dataKey="training_loss"
                                        name="Training Loss"
                                        stroke={CHART_COLORS.training_loss}
                                        strokeWidth={2}
                                        dot={{ r: 3, fill: CHART_COLORS.training_loss }}
                                        activeDot={{ r: 6, strokeWidth: 2 }}
                                        connectNulls
                                    />

                                    {/* Validation Lines (only if not showing per-client) */}
                                    {!showPerClient && (
                                        <>
                                            <Line
                                                type="monotone"
                                                dataKey="validation_rmse"
                                                name="Validation RMSE"
                                                stroke={CHART_COLORS.validation_rmse}
                                                strokeWidth={2}
                                                dot={{ r: 3, fill: CHART_COLORS.validation_rmse }}
                                                activeDot={{ r: 6, strokeWidth: 2 }}
                                                connectNulls
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="validation_mae"
                                                name="Validation MAE"
                                                stroke={CHART_COLORS.validation_mae}
                                                strokeWidth={2}
                                                dot={{ r: 3, fill: CHART_COLORS.validation_mae }}
                                                activeDot={{ r: 6, strokeWidth: 2 }}
                                                connectNulls
                                            />
                                        </>
                                    )}

                                    {/* Per-client lines for federated (when enabled) */}
                                    {showPerClient &&
                                        chartData.clientIds.map((clientId, index) => (
                                            <Line
                                                key={`rmse_${clientId}`}
                                                type="monotone"
                                                dataKey={`rmse_${clientId}`}
                                                name={`RMSE - ${clientId}`}
                                                stroke={CHART_COLORS.clients[index % CHART_COLORS.clients.length]}
                                                strokeWidth={2}
                                                dot={{ r: 2 }}
                                                activeDot={{ r: 5 }}
                                                connectNulls
                                            />
                                        ))}
                                </LineChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>

                    {/* Metrics History Table */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-2">
                            <Table2 className="h-5 w-5 text-muted-foreground" />
                            <span className="text-sm font-medium">Validation Metrics History</span>
                            <Badge variant="secondary" className="text-xs">
                                {tableData.length} {tableData.length === 1 ? epochLabel.toLowerCase() : `${epochLabel.toLowerCase()}s`}
                            </Badge>
                        </div>

                        <div className="rounded-lg border overflow-hidden">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-muted/50">
                                        <TableHead className="font-semibold">{epochLabel}</TableHead>
                                        <TableHead className="font-semibold text-right">Training Loss</TableHead>
                                        <TableHead className="font-semibold text-right">Val RMSE</TableHead>
                                        <TableHead className="font-semibold text-right">Val MAE</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {tableData.map((row, index) => (
                                        <TableRow
                                            key={row.epoch}
                                            className={`${row.isBest
                                                    ? "bg-emerald-50 dark:bg-emerald-950/30 hover:bg-emerald-100 dark:hover:bg-emerald-950/50"
                                                    : index % 2 === 0
                                                        ? "bg-background"
                                                        : "bg-muted/20"
                                                }`}
                                        >
                                            <TableCell className="font-medium">
                                                <div className="flex items-center gap-2">
                                                    {row.epoch}
                                                    {row.isBest && (
                                                        <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900 dark:text-emerald-300 gap-1 text-xs">
                                                            <Award className="h-3 w-3" />
                                                            Best
                                                        </Badge>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right tabular-nums">
                                                {row.training_loss !== null ? row.training_loss.toFixed(4) : "—"}
                                            </TableCell>
                                            <TableCell
                                                className={`text-right tabular-nums ${row.isBest ? "font-semibold text-emerald-700 dark:text-emerald-400" : ""
                                                    }`}
                                            >
                                                {row.validation_rmse !== null ? row.validation_rmse.toFixed(4) : "—"}
                                            </TableCell>
                                            <TableCell className="text-right tabular-nums">
                                                {row.validation_mae !== null ? row.validation_mae.toFixed(4) : "—"}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
