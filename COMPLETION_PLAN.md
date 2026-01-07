# FedRec Dashboard - 15-Day Completion Plan

**Start Date:** January 7, 2026
**Target Completion:** January 22, 2026
**Project:** Federated Learning Book Recommendation System (FYP)

---

## Executive Summary

The project has a **solid foundation** with API, database, and service layers fully implemented. The remaining work focuses on:
1. **ML Pipeline** - Recommender model, data handling, training orchestration
2. **Federated Learning** - Flower-based FL simulation
3. **Testing** - Fix configuration issues, add missing tests
4. **Frontend** - Dashboard for visualization

---

## Phase 1: Core ML Pipeline (Days 1-4)

### Day 1-2: Data Handler & Recommender Model

**Goal:** Implement the foundational ML components

#### Task 1.1: Data Handler (`app/application/data/data_handler.py`)
- [ ] Load book ratings dataset (CSV/Parquet)
- [ ] Data validation and preprocessing
- [ ] Train/test split functionality
- [ ] User-based data partitioning for federated learning (IID and non-IID)
- [ ] Dataset statistics and summary

**Acceptance Criteria:**
- Can load Book-Crossing or similar dataset
- Provides clean train/test splits
- Supports partitioning data across N simulated clients

#### Task 1.2: Recommender Model (`app/core/models/recommender.py`)
- [ ] Implement Biased SVD matrix factorization
- [ ] `fit(ratings)` method for training
- [ ] `predict(user_id, item_id)` method
- [ ] Model serialization/deserialization for FL
- [ ] Get/set model parameters (for FedAvg aggregation)

**Acceptance Criteria:**
- Model trains on rating data
- Produces RMSE < 1.0 on test set
- Parameters can be extracted and aggregated

#### Task 1.3: Unit Tests
- [ ] `tests/unit/test_data_handler.py` - Data loading, splitting, partitioning
- [ ] `tests/unit/test_recommender.py` - Model fit, predict, parameter extraction

---

### Day 3-4: Centralized Training

**Goal:** Complete end-to-end centralized training pipeline

#### Task 2.1: Centralized Trainer (`app/application/training/centralized_trainer.py`)
- [ ] Initialize trainer with configuration
- [ ] Training loop with epoch iterations
- [ ] Per-epoch metric recording (RMSE, MAE, loss)
- [ ] Early stopping support
- [ ] Integration with MetricsService for persistence
- [ ] Model checkpoint saving

**Acceptance Criteria:**
- Runs complete training experiment
- Records metrics to database
- Produces trained model file

#### Task 2.2: Integration with Experiment Lifecycle
- [ ] Wire CentralizedTrainer to ExperimentService
- [ ] Automatic status transitions (PENDING → RUNNING → COMPLETED)
- [ ] Error handling and FAILED state

#### Task 2.3: Tests
- [ ] `tests/unit/test_centralized_trainer.py` - Training loop, metrics recording
- [ ] `tests/integration/test_centralized_pipeline.py` - End-to-end centralized experiment

---

## Phase 2: Federated Learning (Days 5-7)

### Day 5-6: Federated Simulation Manager

**Goal:** Implement Flower-based federated learning simulation

#### Task 3.1: Federated Simulation Manager (`app/application/training/federated_simulation_manager.py`)
- [ ] Client class implementing Flower's `Client` interface
- [ ] Server-side aggregation (FedAvg strategy)
- [ ] Simulation orchestration with configurable rounds
- [ ] Per-round global metric aggregation
- [ ] Per-client metric tracking
- [ ] Integration with FederatedExperiment entity

**Acceptance Criteria:**
- Simulates FL with N clients for M rounds
- Records per-round and per-client metrics
- Implements FedAvg aggregation correctly

#### Task 3.2: Flower Integration
- [ ] Use `flwr.simulation.start_simulation()`
- [ ] Custom strategy for metric collection
- [ ] Client data partitioning using DataHandler

#### Task 3.3: Tests
- [ ] `tests/unit/test_federated_simulation.py` - FL client, aggregation
- [ ] `tests/integration/test_federated_pipeline.py` - End-to-end FL experiment

---

### Day 7: Experiment Manager & Reporting

**Goal:** High-level orchestration and results export

#### Task 4.1: Experiment Manager (`app/application/experiment_manager.py`)
- [ ] Unified interface for running experiments
- [ ] `run_centralized_experiment(config)` method
- [ ] `run_federated_experiment(config)` method
- [ ] Error recovery and logging
- [ ] Progress callbacks

#### Task 4.2: Metrics Calculator (`app/application/reporting/metrics_calculator.py`)
- [ ] Calculate convergence rate
- [ ] Communication efficiency metrics
- [ ] Statistical significance tests
- [ ] Client contribution analysis

#### Task 4.3: Export Manager (`app/application/reporting/export_manager.py`)
- [ ] Export results to CSV
- [ ] Export results to JSON
- [ ] Generate comparison tables

#### Task 4.4: Metrics Logger (`app/application/reporting/metrics_logger.py`)
- [ ] Structured logging during training
- [ ] Progress bar integration
- [ ] File-based log output

---

## Phase 3: Testing & Bug Fixes (Days 8-9)

### Day 8: Fix Test Infrastructure

**Goal:** Get all tests passing

#### Task 5.1: Fix pytest-asyncio Configuration
- [ ] Update `pyproject.toml` with correct asyncio_mode
- [ ] Fix async test fixtures
- [ ] Verify all 149 tests run (not skipped)

#### Task 5.2: Fix API Tests
- [ ] Update `tests/api/test_api_structure.py` TestClient usage
- [ ] Add proper async client setup

#### Task 5.3: Add Missing Integration Tests
- [ ] `tests/integration/test_api_routes.py` - Full API workflow
- [ ] `tests/integration/test_experiment_manager.py` - Orchestration tests

---

### Day 9: Comprehensive Testing

**Goal:** Achieve >80% test coverage

#### Task 6.1: End-to-End Tests
- [ ] Test: Create experiment → Run training → Get results
- [ ] Test: Centralized vs Federated comparison
- [ ] Test: API → Service → Repository → Database flow

#### Task 6.2: Edge Cases
- [ ] Test invalid configurations
- [ ] Test experiment failure scenarios
- [ ] Test concurrent experiment execution

---

## Phase 4: Frontend Dashboard (Days 10-13)

### Day 10-11: Frontend Setup & Core Components

**Goal:** Basic React dashboard structure

#### Task 7.1: Project Setup
- [ ] Initialize React app with Vite
- [ ] Configure API client (axios/fetch)
- [ ] Set up routing (React Router)
- [ ] Install UI library (Tailwind CSS or Material UI)

#### Task 7.2: Core Components
- [ ] Layout component (header, sidebar, main content)
- [ ] Experiment list page
- [ ] Experiment detail page
- [ ] Create experiment form

---

### Day 12-13: Visualization & Polish

**Goal:** Charts and experiment comparison

#### Task 8.1: Metrics Visualization
- [ ] Training progress chart (RMSE/MAE over epochs/rounds)
- [ ] Client performance comparison (bar chart)
- [ ] Convergence visualization

#### Task 8.2: Comparison View
- [ ] Side-by-side centralized vs federated results
- [ ] Metrics comparison table
- [ ] Export results button

#### Task 8.3: UX Polish
- [ ] Loading states
- [ ] Error handling UI
- [ ] Responsive design

---

## Phase 5: Integration & Documentation (Days 14-15)

### Day 14: Full Integration Testing

**Goal:** Everything works together

#### Task 9.1: Integration Validation
- [ ] Run full centralized experiment through UI
- [ ] Run full federated experiment through UI
- [ ] Verify metrics display correctly
- [ ] Test export functionality

#### Task 9.2: Performance Testing
- [ ] Test with larger datasets
- [ ] Verify async operations don't block
- [ ] Database query optimization

---

### Day 15: Documentation & Demo

**Goal:** Project ready for submission

#### Task 10.1: Documentation
- [ ] Update README.md with setup instructions
- [ ] API documentation (auto-generated from FastAPI)
- [ ] Architecture diagram
- [ ] User guide for dashboard

#### Task 10.2: Demo Preparation
- [ ] Prepare sample dataset
- [ ] Pre-run experiments for demo
- [ ] Screenshot/video demo

#### Task 10.3: Final Cleanup
- [ ] Remove debug code
- [ ] Code formatting (black, isort)
- [ ] Type checking (mypy)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Flower integration complexity | Start with simple 2-client simulation, scale up |
| Dataset size issues | Use sampled subset for development |
| Frontend timeline pressure | Prioritize core features, skip polish if needed |
| Test failures | Fix incrementally, don't block on 100% coverage |

---

## Daily Deliverables Checklist

| Day | Deliverable | Verification |
|-----|-------------|--------------|
| 1 | DataHandler loads and partitions data | Unit tests pass |
| 2 | Recommender model trains and predicts | RMSE < 1.0 |
| 3 | CentralizedTrainer runs experiment | Metrics in database |
| 4 | End-to-end centralized pipeline | API → Training → Results |
| 5 | FL Client implementation | Flower simulation starts |
| 6 | FedAvg aggregation working | Global model improves |
| 7 | ExperimentManager + Reporting | Export CSV works |
| 8 | All tests passing | 0 skipped, 0 failed |
| 9 | >80% test coverage | Coverage report |
| 10 | React app structure | Routes work |
| 11 | Experiment CRUD in UI | Create/view experiments |
| 12 | Charts rendering | Training progress visible |
| 13 | Comparison view | Centralized vs Federated |
| 14 | Full integration | Demo scenario works |
| 15 | Documentation complete | README updated |

---

## Notes

- **Package Manager:** Use `uv` for all Python dependencies
- **Database:** PostgreSQL via Docker (`docker-compose up -d`)
- **Flower Version:** flwr>=1.25.0 (already in dependencies)
- **Test Command:** `uv run pytest -v`
- **API Server:** `uv run uvicorn app.api.main:app --reload`
