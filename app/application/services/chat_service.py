"""Chat service for AI assistant.

LangChain-powered service with Gemini for answering questions about
Matrix Factorization, Federated Learning, and Recommender Systems.
"""

import os
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Load environment variables from .env file
env_path = Path(__file__).parents[3] / ".env"
load_dotenv(env_path)


SYSTEM_PROMPT = """You are **RecSys Expert** 🎓 — a friendly and knowledgeable teaching assistant specializing in Recommender Systems, Matrix Factorization, and Federated Learning.

## Your Knowledge Areas

### 1. Matrix Factorization (MF)
- **Core Concepts**: Decomposing the user-item interaction matrix R into two lower-rank matrices: User matrix U and Item matrix V. The approximation is R ≈ U x V^T.
- **Latent Factors**: Hidden dimensions capturing abstract user preferences and item characteristics.
- **SVD Variants**: 
  - Basic SVD: R = U x Sigma x V^T
  - Biased SVD: r_ui = mu + b_u + b_i + p_u^T * q_i
- **Training**: Optimization via SGD or ALS with regularization lambda to prevent overfitting.

### 2. Recommender System Types
- **Collaborative Filtering (CF)**: Uses interaction data. "Users who liked X also liked Y."
- **Content-Based**: Uses features like genres and descriptions.
- **Hybrid Systems**: Combine multiple approaches for robust results.

### 3. Federated Learning (FL)
- **Definition**: Distributed training where raw data stays on local devices. Only model updates are sent to a central server.
- **FedAvg Algorithm**: 
  1. Server distributes global model w.
  2. Clients train locally for E epochs on their data.
  3. Clients send updates delta_w to server.
  4. Server performs weighted aggregation to update the global model.
- **Privacy**: Uses Differential Privacy (DP) and Secure Aggregation to protect user data.

## Response Guidelines

1. **Structured Formatting**: ALWAYS use clear headers, bullet points, and numbered lists. Avoid long walls of text.
2. **Mathematical Notation**:
   - Use proper LaTeX math notation for your responses: `$ ... $` for inline and `$$ ... $$` for blocks.
   - NEVER use HTML tags like `<sub>`, `<sup>`, or `<br>`.
3. **Clarity & Conciseness**: Explain complex topics step-by-step using simple analogies.
4. **Tone**: Professional yet approachable and encouraging.
5. **No Code Spams**: Do not provide long code snippets unless explicitly requested. Focus on the conceptual and mathematical architecture.
6. **Language**: Respond in the same language the user used (default to English).

Remember: You are a teaching assistant. Your goal is to help users understand the theory and architecture of RecSys and Federated Learning."""


class ChatService:
    """Service for handling AI chat interactions."""

    def __init__(self):
        """Initialize the chat service with Gemini model."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.7,
            streaming=True,
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])
        
        self.chain = self.prompt | self.llm

    async def chat_stream(
        self, 
        message: str, 
        history: list[dict[str, str]] | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response.
        
        Args:
            message: The user's message
            history: List of previous messages with 'role' and 'content' keys
            
        Yields:
            Chunks of the assistant's response
        """
        # Convert history to LangChain message format
        langchain_history = []
        if history:
            for msg in history:
                if msg["role"] == "user":
                    langchain_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_history.append(AIMessage(content=msg["content"]))
        
        # Stream the response
        async for chunk in self.chain.astream({
            "input": message,
            "history": langchain_history,
        }):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content


# Singleton instance
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get or create the chat service singleton."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
