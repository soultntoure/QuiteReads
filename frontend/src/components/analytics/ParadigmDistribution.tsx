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

// Custom label component to show percentages on the pie chart
const renderCustomizedLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent,
}: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
        <text
            x={x}
            y={y}
            fill="white"
            textAnchor={x > cx ? "start" : "end"}
            dominantBaseline="central"
            className="font-semibold"
            fontSize="14"
        >
            {`${(percent * 100).toFixed(0)}%`}
        </text>
    );
};

// Custom legend formatter to show count alongside name
const renderLegend = (value: string, entry: any) => {
    return (
        <span className="text-sm">
            {value} ({entry.payload.value})
        </span>
    );
};

export function ParadigmDistribution({ experiments }: ParadigmDistributionProps) {
    const total = experiments.length;
    const centralizedCount = experiments.filter((e) => e.type === "centralized").length;
    const federatedCount = experiments.filter((e) => e.type === "federated").length;

    const data = [
        {
            name: "Centralized",
            value: centralizedCount,
            color: "#3b82f6", // blue-500
        },
        {
            name: "Federated",
            value: federatedCount,
            color: "#10b981", // emerald-500
        },
    ].filter((d) => d.value > 0);

    const handleExport = async () => {
        await downloadAsImage("paradigm-distribution-chart", "paradigm-distribution-chart");
    };

    return (
        <Card className="col-span-1">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle>Training Mode Distribution</CardTitle>
                <Button variant="ghost" size="icon" onClick={handleExport} title="Export as PNG">
                    <Download className="h-4 w-4" />
                </Button>
            </CardHeader>
            <CardContent>
                <div id="paradigm-distribution-chart" className="h-[300px] w-full">
                    {total === 0 ? (
                        <div className="flex h-full items-center justify-center">
                            <div className="text-center">
                                <p className="text-muted-foreground text-sm">
                                    No experiments yet
                                </p>
                                <p className="text-muted-foreground text-xs mt-1">
                                    Create your first experiment to see the distribution
                                </p>
                            </div>
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={data}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={renderCustomizedLabel}
                                    outerRadius={100}
                                    paddingAngle={2}
                                    dataKey="value"
                                >
                                    {data.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    formatter={(value: number) => [
                                        `${value} (${((value / total) * 100).toFixed(1)}%)`,
                                        "Count",
                                    ]}
                                />
                                <Legend
                                    verticalAlign="bottom"
                                    height={36}
                                    formatter={renderLegend}
                                    iconType="circle"
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
