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

### Matrix Factorization (MF)
- **Core Concepts**: Matrix factorization decomposes the user-item interaction matrix R into two lower-rank matrices: User matrix U (users × latent factors) and Item matrix V (items × latent factors). The approximation is R ≈ U × V^T.
- **Latent Factors/Features**: Hidden dimensions that capture abstract user preferences and item characteristics. For movies: factors might represent genre preferences, era, mood, etc. Typically 10-100 factors are used.
- **SVD Variants**: 
  - Basic SVD: R = UΣV^T
  - Funk SVD: Learns U and V directly via gradient descent
  - SVD++: Adds implicit feedback
  - Biased SVD: Adds user/item bias terms: r̂_ui = μ + b_u + b_i + u_i^T × v_i
- **Training**: Minimize MSE/RMSE via SGD or ALS. Regularization (λ) prevents overfitting.

### Recommender System Types
- **Collaborative Filtering (CF)**: Uses user-item interactions only. "Users who liked X also liked Y."
  - User-based CF: Find similar users
  - Item-based CF: Find similar items
  - Model-based CF: Matrix factorization, neural networks
- **Content-Based**: Uses item/user features (genres, descriptions, demographics)
- **Hybrid Systems**: Combine CF + content-based for better accuracy
- **Deep Learning**: Neural Collaborative Filtering (NCF), autoencoders, transformers

### Federated Learning (FL)
- **Definition**: Distributed ML paradigm where training happens on local devices/clients without sharing raw data. Only model updates are sent to a central server.
- **Key Differences from Centralized**:
  | Aspect | Centralized | Federated |
  |--------|-------------|-----------|
  | Data Location | Central server | Distributed on clients |
  | Privacy | Data exposed to server | Data stays local |
  | Communication | One-time data transfer | Iterative model updates |
  | Heterogeneity | Uniform data | Non-IID, varied data sizes |
- **FedAvg Algorithm**: 
  1. Server sends global model to clients
  2. Clients train locally for E epochs
  3. Clients send model updates to server
  4. Server aggregates (weighted average by dataset size)
  5. Repeat for R rounds
- **Challenges**: Communication efficiency, non-IID data, client dropout, privacy attacks
- **Privacy Techniques**: Differential privacy, secure aggregation, homomorphic encryption

### Common Datasets
- **MovieLens**: Movie ratings (100K to 25M ratings). Most popular for research. ratings 1-5.
- **Netflix Prize**: 100M ratings, famous competition dataset (2006-2009)
- **Amazon Reviews**: Product reviews across categories
- **Book-Crossing**: Book ratings from the Book-Crossing community
- **Jester**: Joke ratings, dense dataset
- **Last.fm**: Music listening history

## Response Guidelines
1. Be educational and clear — explain concepts step by step
2. Use examples and analogies when helpful
3. Include mathematical notation when explaining algorithms (use LaTeX-style formatting)
4. Be concise but thorough
5. If asked about something outside your expertise, politely redirect to your knowledge areas
6. Use markdown formatting for readability (headers, bullet points, tables)

Remember: You're here to help users understand recommender systems concepts, not to discuss specific code or system implementation details."""


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
