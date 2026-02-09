import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  LayoutDashboard,
  Database,
  FlaskConical,
  Plus,
  Server,
  Network,
  ChevronLeft,
  ChevronRight,
  Menu,
  BarChart3,
} from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { HealthIndicator } from "@/components/HealthIndicator";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { AIAssistantPanel } from "@/components/ai-assistant";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

interface NavItemProps {
  to: string;
  icon: typeof LayoutDashboard;
  label: string;
  collapsed?: boolean;
  active?: boolean;
}

function NavItem({ to, icon: Icon, label, collapsed, active }: NavItemProps) {
  return (
    <Link
      to={to}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        collapsed && "justify-center px-2"
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span>{label}</span>}
    </Link>
  );
}

function SidebarContent({ collapsed = false }: { collapsed?: boolean }) {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div className={cn(
        "flex h-16 items-center border-b px-4",
        collapsed && "justify-center px-2"
      )}>
        <Link to="/" className="flex items-center gap-2">
          <div className="rounded-lg bg-primary p-1.5">
            <FlaskConical className="h-5 w-5 text-primary-foreground" />
          </div>
          {!collapsed && (
            <span className="text-lg font-bold">FedRec</span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 px-3 py-4">
        <nav className="space-y-2">
          <NavItem
            to="/"
            icon={LayoutDashboard}
            label="Dashboard"
            collapsed={collapsed}
            active={isActive("/") && location.pathname === "/"}
          />
          <NavItem
            to="/dataset"
            icon={Database}
            label="Dataset"
            collapsed={collapsed}
            active={isActive("/dataset")}
          />
          <NavItem
            to="/experiments"
            icon={FlaskConical}
            label="Experiments"
            collapsed={collapsed}
            active={isActive("/experiments") && !location.pathname.includes("/new/")}
          />

          <NavItem
            to="/analytics"
            icon={BarChart3}
            label="Analytics"
            collapsed={collapsed}
            active={isActive("/analytics")}
          />

          {/* New Experiment Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  collapsed && "justify-center px-2"
                )}
              >
                <Plus className="h-4 w-4 shrink-0" />
                {!collapsed && <span>New Experiment</span>}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent side={collapsed ? "right" : "bottom"} align="start">
              <DropdownMenuItem asChild>
                <Link to="/experiments/new/centralized" className="flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  Centralized
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link to="/experiments/new/federated" className="flex items-center gap-2">
                  <Network className="h-4 w-4" />
                  Federated
                </Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </nav>
      </ScrollArea>
    </div>
  );
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex min-h-screen w-full">
      {/* Desktop Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-30 hidden h-screen border-r bg-card transition-all duration-300 lg:block",
          collapsed ? "w-16" : "w-64"
        )}
      >
        <SidebarContent collapsed={collapsed} />

        {/* Collapse Button */}
        <Button
          variant="ghost"
          size="icon"
          className="absolute -right-3 top-20 z-40 h-6 w-6 rounded-full border bg-background shadow-md"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-3 w-3" />
          ) : (
            <ChevronLeft className="h-3 w-3" />
          )}
        </Button>
      </aside>

      {/* Main Content */}
      <div
        className={cn(
          "flex flex-1 flex-col transition-all duration-300",
          collapsed ? "lg:pl-16" : "lg:pl-64"
        )}
      >
        {/* Header */}
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60 lg:px-6">
          {/* Mobile Menu */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              <SidebarContent />
            </SheetContent>
          </Sheet>

          {/* Spacer for desktop */}
          <div className="hidden lg:block" />

          {/* Right side */}
          <div className="flex items-center gap-4">
            <HealthIndicator />
            <ThemeToggle />
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-6">
          {children}
        </main>
      </div>

      {/* AI Assistant Panel */}
      <AIAssistantPanel />
    </div>
  );
}
