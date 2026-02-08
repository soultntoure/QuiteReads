import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { GitCompare, X } from "lucide-react";

interface CompareBarProps {
    selectedIds: string[];
    onClear: () => void;
}

/**
 * Floating action bar that appears when 2+ experiments are selected.
 * Provides quick actions for comparison and clearing selection.
 */
export function CompareBar({ selectedIds, onClear }: CompareBarProps) {
    const navigate = useNavigate();
    const count = selectedIds.length;

    if (count < 2) return null;

    const handleCompare = () => {
        const queryParam = selectedIds.join(",");
        navigate(`/compare?ids=${queryParam}`);
    };

    return (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 animate-in slide-in-from-bottom-4 duration-300">
            <div className="flex items-center gap-3 rounded-full border bg-background/80 px-4 py-2 shadow-lg backdrop-blur-md">
                {/* Selection count */}
                <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                        {count}
                    </div>
                    <span className="text-sm font-medium">
                        experiment{count !== 1 ? "s" : ""} selected
                    </span>
                </div>

                {/* Divider */}
                <div className="h-6 w-px bg-border" />

                {/* Actions */}
                <Button
                    size="sm"
                    onClick={handleCompare}
                    className="gap-2"
                >
                    <GitCompare className="h-4 w-4" />
                    Compare
                </Button>

                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={onClear}
                >
                    <X className="h-4 w-4" />
                </Button>
            </div>
        </div>
    );
}
