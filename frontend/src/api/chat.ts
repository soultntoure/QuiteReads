/**
 * Chat API client with streaming support.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
}

export interface ChatRequest {
    message: string;
    history: ChatMessage[];
}

/**
 * Stream a chat response from the AI assistant.
 *
 * @param request - The chat request containing message and history
 * @param onChunk - Callback for each streamed chunk
 * @param onError - Callback for errors
 * @param onComplete - Callback when stream completes
 */
export async function streamChat(
    request: ChatRequest,
    onChunk: (chunk: string) => void,
    onError: (error: string) => void,
    onComplete: () => void
): Promise<void> {
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(request),
        });

        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({ detail: "Unknown error" }));
            onError(errorBody.detail || "Request failed");
            return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
            onError("No response body");
            return;
        }

        const decoder = new TextDecoder();

        let buffer = "";
        let eventData: string[] = [];

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");

            // Keep the last partial line in the buffer
            buffer = lines.pop() || "";

            for (const line of lines) {
                const trimmedLine = line.trim();

                if (!trimmedLine) {
                    // Empty line signals end of SSE event (double newline \n\n)
                    if (eventData.length > 0) {
                        onChunk(eventData.join("\n"));
                        eventData = [];
                    }
                    continue;
                }

                if (trimmedLine.startsWith("data: ")) {
                    const data = trimmedLine.slice(6);
                    if (data === "[DONE]") {
                        onComplete();
                        return;
                    }
                    if (data.startsWith("Error:")) {
                        onError(data);
                        return;
                    }
                    eventData.push(data);
                }
            }
        }

        // Final event check if stream ends without final newline
        if (eventData.length > 0) {
            onChunk(eventData.join("\n"));
        }

        onComplete();
    } catch (error) {
        onError(error instanceof Error ? error.message : "Unknown error");
    }
}
