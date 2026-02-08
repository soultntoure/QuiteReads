import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useExperiments, useDeleteExperiment } from "@/hooks/use-experiments";
import { StatusBadge } from "@/components/StatusBadge";
import { TypeBadge } from "@/components/TypeBadge";
import { EmptyState } from "@/components/EmptyState";
import { PageLoader } from "@/components/LoadingSpinner";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CompareBar } from "@/components/CompareBar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Search, Trash2, Eye } from "lucide-react";
import { format } from "date-fns";
import type { ExperimentStatus, ExperimentType } from "@/types/experiment";

export default function ExperimentsList() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [experimentToDelete, setExperimentToDelete] = useState<string | null>(null);
  const [selectedExperiments, setSelectedExperiments] = useState<Set<string>>(new Set());
  const [searchParams, setSearchParams] = useSearchParams();

  // Handle preselect from CTA navigation
  useEffect(() => {
    const preselect = searchParams.get("preselect");
    if (preselect) {
      setSelectedExperiments(new Set([preselect]));
      // Clean up the URL after applying
      searchParams.delete("preselect");
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  // Selection handlers
  const toggleSelection = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSelectedExperiments(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedExperiments.size === filteredExperiments.length) {
      setSelectedExperiments(new Set());
    } else {
      setSelectedExperiments(new Set(filteredExperiments.map(e => e.id)));
    }
  };

  const clearSelection = () => setSelectedExperiments(new Set());

  const { data, isLoading } = useExperiments({
    status_filter: statusFilter !== "all" ? statusFilter : undefined,
    type_filter: typeFilter !== "all" ? typeFilter : undefined,
  });

  const deleteExperiment = useDeleteExperiment();

  // Filter by search query
  const filteredExperiments = data?.experiments.filter((exp) =>
    exp.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) ?? [];

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setExperimentToDelete(id);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (experimentToDelete) {
      deleteExperiment.mutate(experimentToDelete, {
        onSuccess: () => {
          setDeleteDialogOpen(false);
          setExperimentToDelete(null);
        },
      });
    }
  };

  if (isLoading) {
    return <PageLoader />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Experiments</h1>
          <p className="text-muted-foreground">
            Manage and monitor all your training experiments
          </p>
        </div>
        <div className="flex gap-3">
          <Button asChild>
            <Link to="/experiments/new/centralized">
              <Plus className="mr-2 h-4 w-4" />
              Centralized
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/experiments/new/federated">
              <Plus className="mr-2 h-4 w-4" />
              Federated
            </Link>
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search experiments..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-[150px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="centralized">Centralized</SelectItem>
                <SelectItem value="federated">Federated</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Experiments Table */}
      <Card>
        <CardContent className="p-0">
          {filteredExperiments.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title={searchQuery || statusFilter !== "all" || typeFilter !== "all"
                  ? "No experiments found"
                  : "No experiments yet"}
                description={
                  searchQuery || statusFilter !== "all" || typeFilter !== "all"
                    ? "Try adjusting your filters or search query"
                    : "Create your first experiment to get started"
                }
                showActions={!searchQuery && statusFilter === "all" && typeFilter === "all"}
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50px]">
                    <Checkbox
                      checked={filteredExperiments.length > 0 && selectedExperiments.size === filteredExperiments.length}
                      onCheckedChange={toggleSelectAll}
                      aria-label="Select all"
                    />
                  </TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="hidden md:table-cell">Config</TableHead>
                  <TableHead className="hidden sm:table-cell">Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredExperiments.map((experiment) => (
                  <TableRow
                    key={experiment.id}
                    className={`cursor-pointer ${selectedExperiments.has(experiment.id) ? 'bg-muted/50' : ''}`}
                    onClick={() => navigate(`/experiments/${experiment.id}`)}
                  >
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selectedExperiments.has(experiment.id)}
                        onCheckedChange={() => toggleSelection({ stopPropagation: () => { } } as React.MouseEvent, experiment.id)}
                        aria-label={`Select ${experiment.name}`}
                      />
                    </TableCell>
                    <TableCell className="font-medium">
                      {experiment.name}
                    </TableCell>
                    <TableCell>
                      <TypeBadge type={experiment.type} />
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={experiment.status} />
                    </TableCell>
                    <TableCell className="hidden md:table-cell text-muted-foreground text-sm">
                      LR: {experiment.config.learning_rate} |
                      Epochs: {experiment.config.epochs}
                      {experiment.type === "federated" && (
                        <> | Clients: {experiment.n_clients}</>
                      )}
                    </TableCell>
                    <TableCell className="hidden sm:table-cell text-muted-foreground">
                      {format(new Date(experiment.created_at), "MMM d, yyyy")}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/experiments/${experiment.id}`);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => handleDeleteClick(e, experiment.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Experiment"
        description="Are you sure you want to delete this experiment? This action cannot be undone and all associated metrics will be lost."
        confirmLabel="Delete"
        variant="destructive"
        isLoading={deleteExperiment.isPending}
        onConfirm={handleDeleteConfirm}
      />

      {/* Comparison Bar */}
      <CompareBar
        selectedIds={Array.from(selectedExperiments)}
        onClear={clearSelection}
      />
    </div>
  );
}
