/**
 * Individual chat message component.
 */

import { cn } from "@/lib/utils";
import { User, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

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
                "flex gap-4 group animate-in fade-in slide-in-from-bottom-2 duration-300",
                isUser ? "flex-row-reverse" : "flex-row"
            )}
        >
            <div
                className={cn(
                    "flex-shrink-0 w-9 h-9 rounded-2xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-110",
                    isUser
                        ? "bg-primary text-primary-foreground shadow-primary/20"
                        : "bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-emerald-500/20"
                )}
            >
                {isUser ? (
                    <User className="w-5 h-5" />
                ) : (
                    <Sparkles className="w-5 h-5" />
                )}
            </div>

            <div className={cn(
                "flex flex-col gap-1.5 max-w-[85%]",
                isUser ? "items-end" : "items-start"
            )}>
                <div className="flex items-center gap-2 px-1">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
                        {isUser ? "You" : "RecSys Expert"}
                    </span>
                </div>

                <div
                    className={cn(
                        "relative p-4 rounded-3xl text-sm leading-relaxed shadow-sm",
                        isUser
                            ? "bg-primary text-primary-foreground rounded-tr-none"
                            : "bg-muted/50 backdrop-blur-sm border border-border/50 rounded-tl-none"
                    )}
                >
                    <div className={cn(
                        "prose prose-sm max-w-none dark:prose-invert",
                        "prose-headings:font-bold prose-headings:tracking-tight prose-headings:mb-2 prose-headings:mt-4",
                        "prose-p:leading-relaxed prose-p:mb-3",
                        "prose-ul:my-2 prose-li:my-0.5",
                        "prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none",
                        "prose-table:border prose-table:rounded-lg prose-th:bg-muted/50 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2",
                        isUser ? "prose-p:text-primary-foreground text-primary-foreground" : "text-foreground"
                    )}>
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm, remarkMath]}
                            rehypePlugins={[rehypeKatex]}
                        >
                            {content}
                        </ReactMarkdown>
                    </div>
                    {isStreaming && (
                        <span className="inline-flex gap-1 ml-2 translate-y-0.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" />
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
