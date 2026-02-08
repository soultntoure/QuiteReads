import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/StatusBadge";
import { TypeBadge } from "@/components/TypeBadge";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import type { ExperimentResponse as Experiment } from "@/types/experiment";

interface TopExperimentsTableProps {
    experiments: Experiment[];
    initialSort?: string;
    onSortChange?: (sortBy: string) => void;
}

type SortField = "rmse" | "mae" | "time" | "created_at";
type SortDirection = "asc" | "desc";

function formatTime(seconds: number | null): string {
    if (seconds == null) return "-";
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
}

export function TopExperimentsTable({ experiments, initialSort, onSortChange }: TopExperimentsTableProps) {
    const navigate = useNavigate();
    const [limit, setLimit] = useState<number>(10);
    const [sortField, setSortField] = useState<SortField>(
        (initialSort as SortField) || "rmse"
    );
    const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

    const completed = useMemo(() =>
        experiments.filter(e => e.status === "completed"),
        [experiments]
    );

    const sortedExperiments = useMemo(() => {
        const sorted = [...completed].sort((a, b) => {
            let aVal: number | null = null;
            let bVal: number | null = null;

            switch (sortField) {
                case "rmse":
                    aVal = a.metrics?.final_rmse ?? null;
                    bVal = b.metrics?.final_rmse ?? null;
                    break;
                case "mae":
                    aVal = a.metrics?.final_mae ?? null;
                    bVal = b.metrics?.final_mae ?? null;
                    break;
                case "time":
                    aVal = a.metrics?.training_time_seconds ?? null;
                    bVal = b.metrics?.training_time_seconds ?? null;
                    break;
                case "created_at":
                    aVal = new Date(a.created_at).getTime();
                    bVal = new Date(b.created_at).getTime();
                    break;
            }

            // Handle nulls
            if (aVal == null && bVal == null) return 0;
            if (aVal == null) return 1;
            if (bVal == null) return -1;

            const diff = aVal - bVal;
            return sortDirection === "asc" ? diff : -diff;
        });

        return sorted.slice(0, limit);
    }, [completed, sortField, sortDirection, limit]);

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection(d => d === "asc" ? "desc" : "asc");
        } else {
            setSortField(field);
            setSortDirection("asc");
            onSortChange?.(field);
        }
    };

    const SortIcon = ({ field }: { field: SortField }) => {
        if (sortField !== field) return <ArrowUpDown className="h-4 w-4 ml-1 opacity-50" />;
        return sortDirection === "asc"
            ? <ArrowUp className="h-4 w-4 ml-1" />
            : <ArrowDown className="h-4 w-4 ml-1" />;
    };

    if (completed.length === 0) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Top Experiments</CardTitle>
                </CardHeader>
                <CardContent className="flex items-center justify-center h-32 text-muted-foreground">
                    No completed experiments yet
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle className="text-base">Top Experiments</CardTitle>
                    <p className="text-sm text-muted-foreground">
                        Showing {Math.min(limit, completed.length)} of {completed.length} completed
                    </p>
                </div>
                <Select value={limit.toString()} onValueChange={(v) => setLimit(Number(v))}>
                    <SelectTrigger className="w-24">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="10">Top 10</SelectItem>
                        <SelectItem value="25">Top 25</SelectItem>
                        <SelectItem value="50">Top 50</SelectItem>
                    </SelectContent>
                </Select>
            </CardHeader>
            <CardContent>
                <div className="overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[50px]">#</TableHead>
                                <TableHead>Name</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead
                                    className="cursor-pointer hover:bg-muted/50"
                                    onClick={() => handleSort("rmse")}
                                >
                                    <div className="flex items-center">
                                        RMSE
                                        <SortIcon field="rmse" />
                                    </div>
                                </TableHead>
                                <TableHead
                                    className="cursor-pointer hover:bg-muted/50"
                                    onClick={() => handleSort("mae")}
                                >
                                    <div className="flex items-center">
                                        MAE
                                        <SortIcon field="mae" />
                                    </div>
                                </TableHead>
                                <TableHead
                                    className="cursor-pointer hover:bg-muted/50"
                                    onClick={() => handleSort("time")}
                                >
                                    <div className="flex items-center">
                                        Time
                                        <SortIcon field="time" />
                                    </div>
                                </TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {sortedExperiments.map((exp, index) => (
                                <TableRow
                                    key={exp.id}
                                    className="cursor-pointer hover:bg-muted/50"
                                    onClick={() => navigate(`/experiments/${exp.id}`)}
                                >
                                    <TableCell className="text-muted-foreground">
                                        {index + 1}
                                    </TableCell>
                                    <TableCell className="font-medium max-w-[200px] truncate">
                                        {exp.name}
                                    </TableCell>
                                    <TableCell>
                                        <TypeBadge type={exp.type} />
                                    </TableCell>
                                    <TableCell>
                                        {exp.metrics?.final_rmse?.toFixed(4) ?? "-"}
                                    </TableCell>
                                    <TableCell>
                                        {exp.metrics?.final_mae?.toFixed(4) ?? "-"}
                                    </TableCell>
                                    <TableCell>
                                        {formatTime(exp.metrics?.training_time_seconds ?? null)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>
        </Card>
    );
}
