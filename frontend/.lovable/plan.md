

# FedRec Dashboard - Implementation Plan

## Overview
A professional research dashboard for managing and visualizing federated learning experiments, designed for FYP academic presentation. The dashboard will connect to your existing FastAPI backend and provide full CRUD operations for experiments with beautiful data visualization.

---

## 🏠 Dashboard Home Page
The landing page showing a quick overview of your research experiments.

**Summary Cards:**
- Total Experiments count
- Running Experiments (with pulse animation)
- Completed Experiments
- Failed Experiments

**Recent Experiments Section:**
- Table showing 5 most recent experiments
- Columns: Name, Type (badge), Status (badge), Created Date
- Click row to view details

**Quick Actions:**
- "New Centralized Experiment" button
- "New Federated Experiment" button

---

## 📋 Experiments List Page
A comprehensive data table for browsing and managing all experiments.

**Features:**
- Sortable table with columns: Name, Type, Status, Created Date, Actions
- Color-coded status badges:
  - Pending: Gray
  - Running: Blue with subtle pulse
  - Completed: Green
  - Failed: Red
- Type badges distinguishing Centralized vs Federated
- Filter dropdowns by status and type
- Search input to filter by name
- Row click navigates to experiment detail
- Delete action with confirmation dialog

---

## ➕ Create Centralized Experiment Page
Form for creating standard single-server training experiments.

**Form Fields:**
- Name (text, required)
- Learning Rate (0.001-1.0, step 0.001, default 0.01)
- Batch Size (min 1, default 32)
- Epochs (min 1, default 10)
- Model Type (dropdown: "biased_svd")

**Behavior:**
- Inline validation with error messages
- Submit button disabled until valid
- On success: redirect to experiment detail page
- Toast notification on success/error

---

## ➕ Create Federated Experiment Page
Form for creating distributed federated learning experiments.

**Form Fields (includes all centralized fields plus):**
- Number of Clients (min 2, default 5)
- Number of Rounds (min 1, default 10)
- Aggregation Strategy (dropdown: "fedavg")

**Same validation and behavior as centralized form.**

---

## 🔍 Experiment Detail Page
Rich detail view for individual experiments with visualization.

**Header Section:**
- Large experiment name heading
- Type badge (Centralized/Federated)
- Status badge with appropriate color
- Created/Completed timestamps

**Configuration Panel:**
- Clean grid display of all hyperparameters
- Learning Rate, Batch Size, Epochs, Model Type
- Federated-specific: Clients, Rounds, Strategy

**Metrics Panel (when completed):**
- Final RMSE (4 decimal places)
- Final MAE (4 decimal places)
- Training Time (formatted as HH:MM:SS)

**Training Progress Chart:**
- Line chart showing RMSE/MAE over epochs/rounds
- X-axis: Epoch/Round number
- Y-axis: Metric value
- For federated: toggle to show per-client lines or averaged values
- Clean tooltips on hover
- Responsive sizing

**Action Buttons (context-aware):**
- Pending: "Start Experiment" button
- Running: "Mark as Failed" button
- All statuses: "Delete" button with confirmation

---

## 🎨 Design System
Professional research dashboard aesthetic.

**Colors:**
- Primary: Indigo (#4F46E5) for actions
- Success: Green (#10B981) for completed
- Warning: Amber (#F59E0B) for pending
- Error: Red (#EF4444) for failed
- Running: Blue (#3B82F6)

**Layout:**
- Collapsible sidebar navigation
- Clean card-based sections
- Generous whitespace
- Responsive design
- Dark mode support with system preference detection

---

## 🧭 Navigation Structure
**Sidebar:**
- Dashboard (home icon)
- Experiments (list icon) → All experiments
- New Experiment dropdown → Centralized | Federated

**Header:**
- App title/logo: "FedRec Dashboard"
- Dark mode toggle
- API health status indicator (green/red dot)

---

## 📊 Data Visualization Features
**Convergence Charts:**
- Recharts line charts with clean styling
- Subtle grid lines
- Clear axis labels with units
- Interactive tooltips
- Metric selector (RMSE/MAE toggle)
- Federated: per-client view vs aggregated view option

---

## ⚙️ Technical Implementation
**API Integration:**
- TanStack Query for all data fetching
- Proper loading skeletons
- Error handling with toast notifications
- Auto-refetch for running experiments
- Cache invalidation on mutations

**Form Handling:**
- React Hook Form with Zod validation
- Inline error messages
- Disabled submit until valid

**Components Built with shadcn/ui:**
- Cards, Tables, Forms, Buttons, Badges
- Dialogs for confirmations
- Toasts for notifications
- Sidebar for navigation

---

## 📱 Responsive Behavior
- Sidebar collapses to icons on tablet
- Mobile hamburger menu
- Charts resize appropriately
- Tables scroll horizontally on small screens

