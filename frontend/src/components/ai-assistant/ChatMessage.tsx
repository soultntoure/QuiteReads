/**
 * Individual chat message component.
 */

import { cn } from "@/lib/utils";
import { User, Sparkles } from "lucide-react";

interface ChatMessageProps {
    role: "user" | "assistant";
    content: string;
    isStreaming?: boolean;
}

export function ChatMessage({ role, content, isStreaming }: ChatMessageProps) {
    const isUser = role === "user";

    return (
        <div
            className={cn(
                "flex gap-3 p-3 rounded-lg",
                isUser ? "bg-primary/10 ml-4" : "bg-muted mr-4"
            )}
        >
            <div
                className={cn(
                    "flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center",
                    isUser ? "bg-primary text-primary-foreground" : "bg-gradient-to-br from-emerald-500 to-teal-600 text-white"
                )}
            >
                {isUser ? (
                    <User className="w-4 h-4" />
                ) : (
                    <Sparkles className="w-4 h-4" />
                )}
            </div>
            <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-muted-foreground mb-1">
                    {isUser ? "You" : "RecSys Expert"}
                </div>
                <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                    {content}
                    {isStreaming && (
                        <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
                    )}
                </div>
            </div>
        </div>
    );
}
