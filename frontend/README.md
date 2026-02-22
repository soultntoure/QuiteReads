# QuiteReads Dashboard

A professional research dashboard for monitoring and managing federated learning experiments in recommendation systems.

## Project Overview

This project provides a comprehensive interface for:
- Creating and managing centralized and federated recommendation experiments.
- Real-time monitoring of training progress (loss, hits, etc.).
- Detailed comparison of experiments with side-by-side metric analysis.
- Dataset visualization and statistics.
- System health monitoring.

## Tech Stack

- **Frontend**: React, TypeScript, Vite
- **UI Components**: shadcn/ui, Tailwind CSS, Lucide React
- **Charts**: Recharts
- **Backend API**: FastAPI (Python)
- **Database**: PostgreSQL

## Getting Started

### Prerequisites

- Node.js (v18+)
- npm

### Installation

1. Clone the repository:
   ```sh
   git clone <repository-url>
   ```

2. Navigate to the frontend directory:
   ```sh
   cd frontend
   ```

3. Install dependencies:
   ```sh
   npm install
   ```

4. Start the development server:
   ```sh
   npm run dev
   ```

The dashboard will be available at `http://localhost:8080`.

## Architecture

The dashboard interacts with a FastAPI backend that orchestrates the federated learning simulations. Metrics are persisted in a PostgreSQL database and fetched via REST endpoints.
