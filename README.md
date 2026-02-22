<div align="center">

# 📚 QuiteReads

**A federated learning research dashboard for book recommendations**

*Comparing privacy-preserving federated training against centralized approaches — Final Year Project, Multimedia University (MMU)*

<br/>

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

[![PyTorch](https://img.shields.io/badge/PyTorch_Lightning-792EE5?style=for-the-badge&logo=lightning&logoColor=white)](https://lightning.ai/)
[![Flower](https://img.shields.io/badge/Flower_FL-FF6F61?style=for-the-badge&logo=flower&logoColor=white)](https://flower.ai/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Google Gemini](https://img.shields.io/badge/Gemini_AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)

</div>

---

## What is QuiteReads?

QuiteReads is a full-stack research platform that answers one central question:

> **Can a federated learning approach — where user reading data never leaves their device — still produce book recommendations competitive with centralized training?**

Using the **Goodreads dataset** and a **Matrix Factorization** model, the dashboard lets you run both approaches, watch them train in real time, and compare the results side-by-side. It also includes an AI assistant to help you interpret your findings.

---

## Features

| | Feature | Description |
|---|---|---|
| 🧪 | **Run Experiments** | Create centralized or federated training runs with custom hyperparameters |
| 📈 | **Live Training Monitor** | Watch RMSE and MAE metrics update epoch-by-epoch during training |
| ⚖️ | **Experiment Comparison** | Compare any two experiments side-by-side with charts and metric tables |
| 📉 | **Convergence Charts** | Visualize model convergence over time with interactive line charts |
| 📊 | **Dataset Explorer** | Browse Goodreads dataset statistics and distribution |
| 🤖 | **AI Assistant** | Ask questions about your experiment results using Gemini-powered chat |
| 🩺 | **Health Monitoring** | Real-time backend and database status indicators |
| 🌙 | **Dark / Light Mode** | Full theme support across the dashboard |

---

## Tech Stack

<table>
<tr>
<td valign="top" width="50%">

**Backend**
- **[FastAPI](https://fastapi.tiangolo.com/)** — async REST API
- **[Flower](https://flower.ai/)** — federated learning simulation
- **[PyTorch Lightning](https://lightning.ai/)** — matrix factorization training
- **[SQLAlchemy](https://www.sqlalchemy.org/)** (async) — ORM & database access
- **PostgreSQL** — experiment and metrics storage
- **[LangChain](https://langchain.com/) + Gemini** — AI assistant

</td>
<td valign="top" width="50%">

**Frontend**
- **[React](https://react.dev/) + TypeScript** — UI framework
- **[Vite](https://vitejs.dev/)** — build tool and dev server
- **[Tailwind CSS](https://tailwindcss.com/) + [shadcn/ui](https://ui.shadcn.com/)** — styling and components
- **[Recharts](https://recharts.org/)** — training metric charts

</td>
</tr>
</table>

---

## Project Structure

```
QuiteReads/
│
├── app/                        # Python backend (FastAPI)
│   ├── api/                    #   REST endpoints and request/response schemas
│   ├── application/            #   Experiment orchestration and training logic
│   ├── core/                   #   Domain entities, business rules, interfaces
│   ├── infrastructure/         #   Database models and repository implementations
│   └── utils/                  #   Shared utilities and logging
│
├── frontend/                   # React dashboard (TypeScript + Vite)
│   └── src/
│       ├── pages/              #   Dashboard, Experiments, Compare, Dataset, AI Assistant
│       ├── components/         #   Reusable UI components (charts, cards, badges)
│       └── api/                #   API client functions
│
├── alembic/                    # Database migration scripts
├── tests/                      # Unit and integration tests
├── data/                       # Raw Goodreads dataset (not committed to git)
├── scripts/                    # Utility and validation scripts
├── docs/                       # Additional documentation
└── project-notes/              # Research notes, architecture decisions, retrospectives
```

> Each subdirectory has its own `README.md` with deeper technical details.

---

## Getting Started

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| [Python](https://www.python.org/) | 3.12+ | Backend runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager |
| [Node.js](https://nodejs.org/) | 18+ | Frontend tooling |
| [Docker](https://www.docker.com/) | any | Running PostgreSQL |

### 1. Clone the repository

```bash
git clone <repository-url>
cd QuiteReads
```

### 2. Start the database

```bash
docker-compose up -d
```

<details>
<summary>No Docker? Run PostgreSQL manually instead.</summary>

Ensure PostgreSQL is running and reachable at:
```
postgresql://postgres:postgres@localhost:5432/fedrec
```
</details>

### 3. Set up the backend

```bash
# Install Python dependencies
uv sync

# Apply database migrations
uv run alembic upgrade head

# Start the API server
uv run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

> API available at **http://localhost:8000** · Swagger docs at **http://localhost:8000/docs**

### 4. Set up the frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

> Dashboard available at **http://localhost:8080**

### 5. Configure the AI Assistant *(optional)*

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

---

## How It Works

```
  Create Experiment          Train                    Analyze
  ─────────────────    ──────────────────    ──────────────────────────
  Choose: centralized  Backend trains the    View RMSE/MAE, convergence
  or federated         model, streaming      charts, compare experiments,
  Set hyperparameters  metrics per epoch     ask the AI assistant
```

1. **Create an experiment** — pick centralized or federated, set learning rate, embedding factors, and epochs
2. **Training runs** — the backend trains the model and captures metrics at every epoch/round
3. **View results** — inspect convergence charts and final RMSE/MAE on the experiment detail page
4. **Compare** — select any two experiments for a side-by-side metric breakdown
5. **Ask the AI** — use the built-in assistant to explain or summarize your results

---

## Federated Learning Approach

In the federated setup, **user data never leaves the client**. Each simulated client trains locally on their own reading history. Only **item embeddings** are aggregated across clients using a custom `FedAvgItemsOnly` strategy — user embeddings stay local, preserving privacy.

```
  Client A  ──┐
  Client B  ──┼──► Aggregate item embeddings ──► Global item model
  Client C  ──┘         (FedAvg)
  (user embeddings stay local on each client)
```

This simulates a real-world deployment where a user's reading history never needs to be shared with a central server.

---

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with HTML coverage report
uv run pytest --cov=app --cov-report=html

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/
```

---

## License

This project was developed as a Final Year Project at **Multimedia University (MMU)**. All rights reserved.
