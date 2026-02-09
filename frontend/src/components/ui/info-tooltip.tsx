import * as React from "react";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface InfoTooltipProps {
    title: string;
    description: string;
    tips?: string[];
    className?: string;
}

export function InfoTooltip({ title, description, tips, className }: InfoTooltipProps) {
    return (
        <TooltipProvider delayDuration={200}>
            <Tooltip>
                <TooltipTrigger asChild>
                    <button
                        type="button"
                        className={cn(
                            "inline-flex items-center justify-center rounded-full p-0.5 text-emerald-500 transition-all duration-200",
                            "hover:bg-emerald-100 hover:text-emerald-600 dark:hover:bg-emerald-900/30",
                            "focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2",
                            className
                        )}
                        aria-label={`More info about ${title}`}
                    >
                        <Info className="h-4 w-4" />
                    </button>
                </TooltipTrigger>
                <TooltipContent
                    side="top"
                    align="start"
                    className="max-w-xs border-emerald-200 bg-gradient-to-br from-white to-emerald-50 p-0 shadow-xl dark:border-emerald-800 dark:from-gray-900 dark:to-emerald-950"
                >
                    <div className="space-y-2 p-3">
                        {/* Header */}
                        <div className="flex items-center gap-2">
                            <div className="rounded-md bg-emerald-500/10 p-1.5">
                                <Info className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                            </div>
                            <span className="font-semibold text-emerald-700 dark:text-emerald-300">
                                {title}
                            </span>
                        </div>

                        {/* Description */}
                        <p className="text-sm leading-relaxed text-gray-600 dark:text-gray-300">
                            {description}
                        </p>

                        {/* Tips */}
                        {tips && tips.length > 0 && (
                            <div className="space-y-1 border-t border-emerald-100 pt-2 dark:border-emerald-800">
                                <span className="text-xs font-medium uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
                                    💡 Tips
                                </span>
                                <ul className="space-y-1">
                                    {tips.map((tip, index) => (
                                        <li
                                            key={index}
                                            className="flex items-start gap-1.5 text-xs text-gray-500 dark:text-gray-400"
                                        >
                                            <span className="mt-0.5 h-1 w-1 shrink-0 rounded-full bg-emerald-400" />
                                            {tip}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}
