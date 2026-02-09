import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ExperimentResponse } from "@/types/experiment";
import { Download } from "lucide-react";
import { downloadAsImage } from "@/lib/export-utils";
import {
    PieChart,
    Pie,
    Cell,
    ResponsiveContainer,
    Legend,
    Tooltip,
} from "recharts";

interface ParadigmDistributionProps {
    experiments: ExperimentResponse[];
}

export function ParadigmDistribution({ experiments }: ParadigmDistributionProps) {
    const data = [
        {
            name: "Centralized",
            value: experiments.filter((e) => e.type === "centralized").length,
            color: "#3b82f6", // blue-500
        },
        {
            name: "Federated",
            value: experiments.filter((e) => e.type === "federated").length,
            color: "#10b981", // emerald-500
        },
    ].filter((d) => d.value > 0);

    const handleExport = async () => {
        await downloadAsImage("paradigm-distribution-chart", "paradigm-distribution-chart");
    };

    return (
        <Card className="col-span-1">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle>Paradigm Distribution</CardTitle>
                <Button variant="ghost" size="icon" onClick={handleExport} title="Export as PNG">
                    <Download className="h-4 w-4" />
                </Button>
            </CardHeader>
            <CardContent>
                <div id="paradigm-distribution-chart" className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={data}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {data.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip />
                            <Legend verticalAlign="bottom" height={36} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
