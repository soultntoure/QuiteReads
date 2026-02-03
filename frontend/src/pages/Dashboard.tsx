import { Link } from "react-router-dom";
import { useExperiments } from "@/hooks/use-experiments";
import { SummaryCard } from "@/components/SummaryCard";
import { StatusBadge } from "@/components/StatusBadge";
import { TypeBadge } from "@/components/TypeBadge";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { FlaskConical, Play, CheckCircle, XCircle, Plus } from "lucide-react";
import { format } from "date-fns";

export default function Dashboard() {
  const { data, isLoading } = useExperiments();
  
  const experiments = data?.experiments ?? [];
  const recentExperiments = experiments.slice(0, 5);
  
  // Calculate summary stats
  const totalCount = experiments.length;
  const runningCount = experiments.filter((e) => e.status === "running").length;
  const completedCount = experiments.filter((e) => e.status === "completed").length;
  const failedCount = experiments.filter((e) => e.status === "failed").length;
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your federated learning experiments
          </p>
        </div>
        <div className="flex gap-3">
          <Button asChild>
            <Link to="/experiments/new/centralized">
              <Plus className="mr-2 h-4 w-4" />
              New Centralized
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/experiments/new/federated">
              <Plus className="mr-2 h-4 w-4" />
              New Federated
            </Link>
          </Button>
        </div>
      </div>
      
      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          title="Total Experiments"
          value={totalCount}
          icon={FlaskConical}
          loading={isLoading}
        />
        <SummaryCard
          title="Running"
          value={runningCount}
          icon={Play}
          iconClassName="text-running"
          loading={isLoading}
        />
        <SummaryCard
          title="Completed"
          value={completedCount}
          icon={CheckCircle}
          iconClassName="text-success"
          loading={isLoading}
        />
        <SummaryCard
          title="Failed"
          value={failedCount}
          icon={XCircle}
          iconClassName="text-destructive"
          loading={isLoading}
        />
      </div>
      
      {/* Recent Experiments */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Experiments</CardTitle>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/experiments">View all</Link>
          </Button>
        </CardHeader>
        <CardContent>
          {experiments.length === 0 ? (
            <EmptyState />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="hidden sm:table-cell">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentExperiments.map((experiment) => (
                  <TableRow
                    key={experiment.id}
                    className="cursor-pointer"
                    onClick={() => {
                      window.location.href = `/experiments/${experiment.id}`;
                    }}
                  >
                    <TableCell className="font-medium">
                      {experiment.name}
                    </TableCell>
                    <TableCell>
                      <TypeBadge type={experiment.type} />
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={experiment.status} />
                    </TableCell>
                    <TableCell className="hidden sm:table-cell text-muted-foreground">
                      {format(new Date(experiment.created_at), "MMM d, yyyy")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
