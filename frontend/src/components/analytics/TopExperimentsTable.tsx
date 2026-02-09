import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExperimentResponse } from "@/types/experiment";
import { ArrowUpDown, Download } from "lucide-react";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { downloadCSV, downloadJSON } from "@/lib/export-utils";

interface TopExperimentsTableProps {
    experiments: ExperimentResponse[];
}

type SortField = "final_rmse" | "final_mae" | "training_time_seconds" | "created_at";

export function TopExperimentsTable({ experiments }: TopExperimentsTableProps) {
    const [limit, setLimit] = useState<string>("10");
    const [sortField, setSortField] = useState<SortField>("final_rmse");
    const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

    const completed = experiments.filter(
        (e) => e.status === "completed" && e.metrics
    );

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection(sortDirection === "asc" ? "desc" : "asc");
        } else {
            setSortField(field);
            setSortDirection("asc");
        }
    };

    const sortedData = [...completed].sort((a, b) => {
        const field = sortField;
        const aValue =
            field === "created_at"
                ? new Date(a.created_at).getTime()
                : a.metrics?.[field as keyof typeof a.metrics] || 0;
        const bValue =
            field === "created_at"
                ? new Date(b.created_at).getTime()
                : b.metrics?.[field as keyof typeof b.metrics] || 0;

        if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
        if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
        return 0;
    });

    const displayData = sortedData.slice(0, parseInt(limit));

    const SortIcon = ({ field }: { field: SortField }) => {
        return sortField === field ? (
            <ArrowUpDown className="ml-2 h-4 w-4" />
        ) : null;
    };

    const handleExportCSV = () => {
        const exportData = displayData.map((exp, index) => ({
            "#": index + 1,
            name: exp.name,
            type: exp.type,
            rmse: exp.metrics?.final_rmse?.toFixed(4) || "N/A",
            mae: exp.metrics?.final_mae?.toFixed(4) || "N/A",
            "time_seconds": exp.metrics?.training_time_seconds?.toFixed(2) || "N/A",
        }));

        // Generate contextual filename based on current sorting
        const sortLabel = sortField.replace('_', '-');
        downloadCSV(exportData, `top-experiments-sort-${sortLabel}`);
    };

    const handleExportJSON = () => {
        // Generate contextual filename based on current sorting
        const sortLabel = sortField.replace('_', '-');
        downloadJSON(displayData, `top-experiments-sort-${sortLabel}`);
    };

    return (
        <Card className="col-span-1 lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardTitle>Top Experiments</CardTitle>
                <div className="flex items-center space-x-2">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm">
                                <Download className="mr-2 h-4 w-4" />
                                Export
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={handleExportCSV}>
                                Export as CSV
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={handleExportJSON}>
                                Export as JSON
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                    <span className="text-sm text-muted-foreground">Show:</span>
                    <Select value={limit} onValueChange={setLimit}>
                        <SelectTrigger className="w-[70px]">
                            <SelectValue placeholder="10" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="10">10</SelectItem>
                            <SelectItem value="25">25</SelectItem>
                            <SelectItem value="50">50</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </CardHeader>
            <CardContent>
                <div className="rounded-md border">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[60px]">#</TableHead>
                                <TableHead>Name</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead
                                    className="cursor-pointer"
                                    onClick={() => handleSort("final_rmse")}
                                >
                                    <div className="flex items-center">
                                        RMSE <SortIcon field="final_rmse" />
                                    </div>
                                </TableHead>
                                <TableHead
                                    className="cursor-pointer"
                                    onClick={() => handleSort("final_mae")}
                                >
                                    <div className="flex items-center">
                                        MAE <SortIcon field="final_mae" />
                                    </div>
                                </TableHead>
                                <TableHead
                                    className="cursor-pointer"
                                    onClick={() => handleSort("training_time_seconds")}
                                >
                                    <div className="flex items-center">
                                        Time (s) <SortIcon field="training_time_seconds" />
                                    </div>
                                </TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {displayData.map((experiment, index) => (
                                <TableRow key={experiment.id}>
                                    <TableCell className="text-muted-foreground font-mono">
                                        {index + 1}
                                    </TableCell>
                                    <TableCell className="font-medium">
                                        {experiment.name}
                                    </TableCell>
                                    <TableCell>
                                        <Badge
                                            variant={
                                                experiment.type === "federated" ? "secondary" : "default"
                                            }
                                        >
                                            {experiment.type}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        {experiment.metrics?.final_rmse?.toFixed(4) || "N/A"}
                                    </TableCell>
                                    <TableCell>
                                        {experiment.metrics?.final_mae?.toFixed(4) || "N/A"}
                                    </TableCell>
                                    <TableCell>
                                        {experiment.metrics?.training_time_seconds?.toFixed(2) ||
                                            "N/A"}
                                    </TableCell>
                                </TableRow>
                            ))}
                            {displayData.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-24 text-center">
                                        No completed experiments found.
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>
        </Card>
    );
}
