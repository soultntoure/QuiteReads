import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { FlaskConical, TrendingDown, Trophy, Clock } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import type { ExperimentResponse as Experiment } from "@/types/experiment";

// Consistent colors for paradigms
export const PARADIGM_COLORS = {
    centralized: "hsl(221, 83%, 53%)", // Blue
    federated: "hsl(142, 71%, 45%)",   // Green
};

interface OverviewStatsProps {
    experiments: Experiment[];
    loading?: boolean;
    onCardClick?: (sortBy: string) => void;
    activeSort?: string;
}

function calculateStats(experiments: Experiment[]) {
    const completed = experiments.filter(e => e.status === "completed");

    const rmseValues = completed
        .map(e => e.metrics?.final_rmse)
        .filter((v): v is number => v != null);

    const timeValues = completed
        .map(e => e.metrics?.training_time_seconds)
        .filter((v): v is number => v != null);

    const avgRmse = rmseValues.length > 0
        ? rmseValues.reduce((a, b) => a + b, 0) / rmseValues.length
        : null;

    const medianRmse = rmseValues.length > 0
        ? rmseValues.sort((a, b) => a - b)[Math.floor(rmseValues.length / 2)]
        : null;

    const bestRmse = rmseValues.length > 0
        ? Math.min(...rmseValues)
        : null;

    const avgTime = timeValues.length > 0
        ? timeValues.reduce((a, b) => a + b, 0) / timeValues.length
        : null;

    return {
        totalCompleted: completed.length,
        avgRmse,
        medianRmse,
        bestRmse,
        avgTime,
    };
}

function formatTime(seconds: number | null): string {
    if (seconds == null) return "-";
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
}

interface StatCardProps {
    title: string;
    value: string;
    subtitle?: string;
    icon: React.ElementType;
    iconClassName?: string;
    loading?: boolean;
    onClick?: () => void;
    active?: boolean;
}

function StatCard({ title, value, subtitle, icon: Icon, iconClassName, loading, onClick, active }: StatCardProps) {
    return (
        <Card
            className={`cursor-pointer transition-all hover:shadow-md hover:border-primary/50 ${active ? "ring-2 ring-primary border-primary" : ""
                }`}
            onClick={onClick}
        >
            <CardContent className="flex items-center gap-4 p-6">
                <div className={`rounded-full p-3 bg-muted ${iconClassName}`}>
                    <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1">
                    {loading ? (
                        <>
                            <Skeleton className="h-4 w-20 mb-2" />
                            <Skeleton className="h-6 w-16" />
                        </>
                    ) : (
                        <>
                            <p className="text-sm text-muted-foreground">{title}</p>
                            <p className="text-2xl font-bold">{value}</p>
                            {subtitle && (
                                <p className="text-xs text-muted-foreground">{subtitle}</p>
                            )}
                        </>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

export function OverviewStats({ experiments, loading, onCardClick, activeSort }: OverviewStatsProps) {
    const stats = useMemo(() => calculateStats(experiments), [experiments]);

    return (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
                title="Completed Runs"
                value={stats.totalCompleted.toString()}
                icon={FlaskConical}
                loading={loading}
                onClick={() => onCardClick?.("created_at")}
                active={activeSort === "created_at"}
            />
            <StatCard
                title="Avg RMSE"
                value={stats.avgRmse?.toFixed(4) ?? "-"}
                subtitle={stats.medianRmse ? `Median: ${stats.medianRmse.toFixed(4)}` : undefined}
                icon={TrendingDown}
                iconClassName="text-blue-600"
                loading={loading}
                onClick={() => onCardClick?.("rmse")}
                active={activeSort === "rmse"}
            />
            <StatCard
                title="Best RMSE"
                value={stats.bestRmse?.toFixed(4) ?? "-"}
                icon={Trophy}
                iconClassName="text-amber-500"
                loading={loading}
                onClick={() => onCardClick?.("rmse")}
                active={activeSort === "rmse"}
            />
            <StatCard
                title="Avg Training Time"
                value={formatTime(stats.avgTime)}
                icon={Clock}
                iconClassName="text-purple-600"
                loading={loading}
                onClick={() => onCardClick?.("time")}
                active={activeSort === "time"}
            />
        </div>
    );
}
