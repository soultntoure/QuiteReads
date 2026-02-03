import { useHealthCheck } from "@/hooks/use-experiments";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function HealthIndicator() {
  const { data, isLoading, isError } = useHealthCheck();
  
  const isHealthy = data?.status === "healthy";
  
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "h-2.5 w-2.5 rounded-full",
              isLoading && "bg-warning animate-pulse",
              isError && "bg-destructive",
              isHealthy && "bg-success"
            )}
          />
          <span className="text-sm text-muted-foreground hidden sm:inline">
            {isLoading ? "Checking..." : isError ? "API Offline" : "API Online"}
          </span>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        {isLoading && "Checking API health..."}
        {isError && "Cannot connect to backend API"}
        {isHealthy && "Backend API is healthy"}
      </TooltipContent>
    </Tooltip>
  );
}
