import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExperimentResponse } from "@/types/experiment";
import { Activity, Clock, Trophy, Zap } from "lucide-react";

interface OverviewStatsProps {
    experiments: ExperimentResponse[];
    onSortChange?: (metric: "rmse" | "time" | "date") => void;
}

export function OverviewStats({ experiments, onSortChange }: OverviewStatsProps) {
    const completedExperiments = experiments.filter(
        (e) => e.status === "completed" && e.metrics
    );

    const totalCompleted = completedExperiments.length;

    const avgRmse =
        totalCompleted > 0
            ? completedExperiments.reduce(
                (sum, e) => sum + (e.metrics.final_rmse || 0),
                0
            ) / totalCompleted
            : 0;

    const bestRmse =
        totalCompleted > 0
            ? Math.min(
                ...completedExperiments
                    .map((e) => e.metrics.final_rmse || Infinity)
                    .filter((v) => v !== Infinity)
            )
            : 0;

    const avgTime =
        totalCompleted > 0
            ? completedExperiments.reduce(
                (sum, e) => sum + (e.metrics.training_time_seconds || 0),
                0
            ) / totalCompleted
            : 0;

    const cards = [
        {
            title: "Total Completed Runs",
            value: totalCompleted.toString(),
            icon: Activity,
            metric: "date" as const,
            description: "Successfully finished experiments",
        },
        {
            title: "Average RMSE",
            value: avgRmse.toFixed(4),
            icon: Zap,
            metric: "rmse" as const,
            description: "Lower is better",
        },
        {
            title: "Best RMSE",
            value: bestRmse === Infinity ? "N/A" : bestRmse.toFixed(4),
            icon: Trophy,
            metric: "rmse" as const,
            description: "All-time lowest error",
        },
        {
            title: "Avg Training Time",
            value: `${avgTime.toFixed(1)}s`,
            icon: Clock,
            metric: "time" as const,
            description: "Per completed experiment",
        },
    ];

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {cards.map((card) => (
                <Card
                    key={card.title}
                    className={`cursor-pointer transition-all hover:bg-muted/50 ${onSortChange ? "hover:scale-[1.02]" : ""
                        }`}
                    onClick={() => onSortChange?.(card.metric)}
                >
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            {card.title}
                        </CardTitle>
                        <card.icon className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{card.value}</div>
                        <p className="text-xs text-muted-foreground">
                            {card.description}
                        </p>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
