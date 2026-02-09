/**
 * Suggestion chips for the AI assistant.
 */

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SuggestionChipsProps {
    onSelect: (suggestion: string) => void;
    disabled?: boolean;
}

const SUGGESTIONS = [
    "What is matrix factorization?",
    "Explain latent factors",
    "Federated vs centralized learning",
    "What is the MovieLens dataset?",
    "How does FedAvg work?",
    "Types of recommender systems",
];

export function SuggestionChips({ onSelect, disabled }: SuggestionChipsProps) {
    return (
        <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((suggestion) => (
                <Button
                    key={suggestion}
                    variant="outline"
                    size="sm"
                    className={cn(
                        "text-[11px] h-auto py-2 px-4 whitespace-normal text-left transition-all duration-300",
                        "bg-background/50 hover:bg-emerald-500 hover:text-white hover:border-emerald-500 hover:shadow-lg hover:shadow-emerald-500/20",
                        "rounded-xl border-border/50"
                    )}
                    onClick={() => onSelect(suggestion)}
                    disabled={disabled}
                >
                    {suggestion}
                </Button>
            ))}
        </div>
    );
}
