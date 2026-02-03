import { FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

interface EmptyStateProps {
  title?: string;
  description?: string;
  showActions?: boolean;
}

export function EmptyState({
  title = "No experiments yet",
  description = "Create your first experiment to get started with training and evaluating machine learning models.",
  showActions = true,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="rounded-full bg-muted p-4">
        <FlaskConical className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        {description}
      </p>
      {showActions && (
        <div className="mt-6 flex gap-3">
          <Button asChild>
            <Link to="/experiments/new/centralized">
              New Centralized
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/experiments/new/federated">
              New Federated
            </Link>
          </Button>
        </div>
      )}
    </div>
  );
}
