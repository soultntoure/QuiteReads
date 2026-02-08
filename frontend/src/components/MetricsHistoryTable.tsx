import { useMemo } from "react";
import { useMetrics } from "@/hooks/use-metrics";
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
import { Table2, AlertCircle, Award } from "lucide-react";
import type { ExperimentType, MetricResponse } from "@/types/experiment";

interface MetricsHistoryTableProps {
    experimentId: string;
    experimentType: ExperimentType;
}

interface EpochData {
    epoch: number;
    training_loss: number | null;
    validation_rmse: number | null;
    validation_mae: number | null;
    isBest?: boolean;
}

export function MetricsHistoryTable({
    experimentId,
    experimentType,
}: MetricsHistoryTableProps) {
    const { data, isLoading, isError } = useMetrics(experimentId);

    // Process metrics into table rows
    const tableData = useMemo(() => {
        if (!data?.metrics.length) return [];

        const epochMap = new Map<number, EpochData>();

        // Group by epoch/round
        data.metrics.forEach((m: MetricResponse) => {
            const epoch = m.round_number ?? 0;

            if (!epochMap.has(epoch)) {
                epochMap.set(epoch, {
                    epoch,
                    training_loss: null,
                    validation_rmse: null,
                    validation_mae: null,
                });
            }

            const row = epochMap.get(epoch)!;
            const context = m.context || "validation";

            if (m.name === "loss" && context === "training") {
                row.training_loss = m.value;
            } else if (m.name === "rmse" && (context === "validation" || context === "centralized_test")) {
                row.validation_rmse = m.value;
            } else if (m.name === "mae" && (context === "validation" || context === "centralized_test")) {
                row.validation_mae = m.value;
            }
        });

        const rows = Array.from(epochMap.values()).sort((a, b) => a.epoch - b.epoch);

        // Find best RMSE epoch
        let bestRmse = Infinity;
        let bestEpoch = -1;
        rows.forEach((row) => {
            if (row.validation_rmse !== null && row.validation_rmse < bestRmse) {
                bestRmse = row.validation_rmse;
                bestEpoch = row.epoch;
            }
        });

        // Mark best
        rows.forEach((row) => {
            row.isBest = row.epoch === bestEpoch;
        });

        return rows;
    }, [data]);

    if (isLoading) {
        return (
            <div className="space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex h-[200px] items-center justify-center">
                <div className="text-center text-muted-foreground">
                    <AlertCircle className="mx-auto h-12 w-12 opacity-30 mb-3" />
                    <p>Failed to load metrics history</p>
                </div>
            </div>
        );
    }

    if (tableData.length === 0) {
        return (
            <div className="flex h-[200px] items-center justify-center border border-dashed rounded-lg bg-muted/30">
                <div className="text-center text-muted-foreground">
                    <Table2 className="mx-auto h-12 w-12 opacity-30 mb-3" />
                    <p>No metrics history available</p>
                    <p className="text-sm mt-1">Run the experiment to see history</p>
                </div>
            </div>
        );
    }

    const epochLabel = experimentType === "federated" ? "Round" : "Epoch";

    return (
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
    );
}
