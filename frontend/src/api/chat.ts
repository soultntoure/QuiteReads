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

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value, { stream: true });
            const lines = text.split("\n");

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const data = line.slice(6);
                    if (data === "[DONE]") {
                        onComplete();
                        return;
                    }
                    if (data.startsWith("Error:")) {
                        onError(data);
                        return;
                    }
                    onChunk(data);
                }
            }
        }

        onComplete();
    } catch (error) {
        onError(error instanceof Error ? error.message : "Unknown error");
    }
}
