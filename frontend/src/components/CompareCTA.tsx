import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { GitCompare, Sparkles } from "lucide-react";

interface CompareCTAProps {
    experimentId: string;
    experimentName: string;
}

/**
 * Sticky CTA bar that appears at the bottom of the ExperimentDetail page
 * for completed experiments, prompting users to compare with other experiments.
 */
export function CompareCTA({ experimentId, experimentName }: CompareCTAProps) {
    return (
        <div className="fixed bottom-0 left-0 right-0 z-40 border-t bg-gradient-to-r from-primary/5 via-background to-primary/5 backdrop-blur-sm">
            <div className="container mx-auto flex items-center justify-between px-4 py-4 md:px-6">
                <div className="flex items-center gap-3">
                    <div className="hidden sm:flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                        <Sparkles className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                        <p className="text-sm font-medium">
                            Want to compare this experiment?
                        </p>
                        <p className="text-xs text-muted-foreground hidden sm:block">
                            See how it stacks up against other runs
                        </p>
                    </div>
                </div>
                <Button asChild className="gap-2">
                    <Link to={`/experiments?preselect=${experimentId}`}>
                        <GitCompare className="h-4 w-4" />
                        <span className="hidden sm:inline">Compare with Others</span>
                        <span className="sm:hidden">Compare</span>
                    </Link>
                </Button>
            </div>
        </div>
    );
}
