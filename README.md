# QuiteReads

A research dashboard for running, monitoring, and comparing **federated learning** and **centralized** book recommendation experiments — built as a Final Year Project (FYP) at Multimedia University (MMU).

---

## What is this?

QuiteReads is a full-stack research platform that lets you explore how *federated learning* compares against traditional *centralized* training for book recommendations. It uses the **Goodreads dataset** and a **Matrix Factorization** model at its core.

The key research question: *Can a federated approach — where user data never leaves the client — still produce recommendations competitive with centralized training?*

The dashboard makes it easy to run both approaches side-by-side, track training metrics in real time, and analyze the tradeoffs.

---

## Features

| Feature | Description |
|---|---|
| **Run Experiments** | Create centralized or federated training runs with configurable hyperparameters |
| **Live Training Monitor** | Watch loss and accuracy metrics update epoch-by-epoch during training |
| **Experiment Comparison** | Compare two experiments side-by-side with charts and metric tables |
| **Convergence Charts** | Visualize how models converge over time with interactive line charts |
| **Dataset Explorer** | Browse dataset statistics and distribution before running experiments |
| **AI Assistant** | Ask questions about your results using a built-in Gemini-powered chat |
| **Health Monitoring** | Check backend and database status at a glance |
| **Dark / Light Mode** | Full theme support across the dashboard |

---

## Tech Stack

**Backend**
- Python 3.12 with [FastAPI](https://fastapi.tiangolo.com/)
- [Flower](https://flower.ai/) — federated learning simulation framework
- [PyTorch Lightning](https://lightning.ai/) — matrix factorization model training
- SQLAlchemy (async) + PostgreSQL — experiment and metrics persistence
- LangChain + Google Gemini — AI assistant

**Frontend**
- React + TypeScript (Vite)
- Tailwind CSS + [shadcn/ui](https://ui.shadcn.com/)
- [Recharts](https://recharts.org/) — training metric visualizations

---

## Project Structure

```
quiteReads/
├── app/                   # Python backend (FastAPI)
│   ├── api/               # REST endpoints and request/response schemas
│   ├── application/       # Experiment orchestration and training logic
│   ├── core/              # Domain entities, business rules, interfaces
│   ├── infrastructure/    # Database models and repository implementations
│   └── utils/             # Shared utilities and logging
│
├── frontend/              # React dashboard (TypeScript + Vite)
│   └── src/
│       ├── pages/         # Dashboard, Experiments, Compare, Dataset, AI Assistant
│       ├── components/    # Reusable UI components (charts, cards, badges)
│       └── api/           # API client functions
│
├── alembic/               # Database migration scripts
├── tests/                 # Unit and integration tests
├── data/                  # Raw Goodreads dataset (not committed)
├── scripts/               # Utility and validation scripts
├── docs/                  # Additional documentation
└── project-notes/         # Research notes, architecture decisions, retrospectives
```

> Each subdirectory contains its own README with deeper technical details.

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+ and npm
- PostgreSQL running locally (or via Docker)

### 1. Clone the repo

```bash
git clone <repository-url>
cd quiteReads
```

### 2. Start the database

```bash
docker-compose up -d
```

Or ensure PostgreSQL is running and accessible at `postgresql://postgres:postgres@localhost:5432/fedrec`.

### 3. Set up the backend

```bash
# Install Python dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the API server
uv run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### 4. Set up the frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The dashboard will be available at `http://localhost:8080`.

### 5. Configure the AI Assistant (optional)

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

---

## How It Works

1. **Create an experiment** — choose centralized or federated, set learning rate, factors, and epochs
2. **Training runs** — the backend trains the model and streams metrics per epoch/round
3. **View results** — inspect RMSE, MAE, and convergence charts on the experiment detail page
4. **Compare** — pick two experiments to compare side-by-side
5. **Ask the AI** — use the assistant to summarize or explain your results

---

## Federated Learning Approach

In the federated setup, user data never leaves the client. Only **item embeddings** are aggregated across clients (using a custom FedAvg strategy) — user embeddings stay local, preserving privacy. This simulates a real-world federated deployment where each user's reading history is private.

---

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=app --cov-report=html
```

---

## License

This project is developed as part of a Final Year Project at Multimedia University (MMU). All rights reserved.
