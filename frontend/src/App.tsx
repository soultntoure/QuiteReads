import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { DashboardLayout } from "@/components/DashboardLayout";
import Dashboard from "@/pages/Dashboard";
import ExperimentsList from "@/pages/ExperimentsList";
import ExperimentDetail from "@/pages/ExperimentDetail";
import CreateCentralizedExperiment from "@/pages/CreateCentralizedExperiment";
import CreateFederatedExperiment from "@/pages/CreateFederatedExperiment";
import DatasetPage from "@/pages/DatasetPage";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <DashboardLayout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dataset" element={<DatasetPage />} />
            <Route path="/experiments" element={<ExperimentsList />} />
            <Route path="/experiments/new/centralized" element={<CreateCentralizedExperiment />} />
            <Route path="/experiments/new/federated" element={<CreateFederatedExperiment />} />
            <Route path="/experiments/:id" element={<ExperimentDetail />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </DashboardLayout>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
