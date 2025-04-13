import React, { useState, useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import MainNav from '@/components/navigation/MainNav';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { 
  MagnifyingGlassIcon, 
  ArrowDownTrayIcon,
  BellIcon,
  PlayIcon
} from '@heroicons/react/24/outline';
import { Input } from '@/components/ui/input';
import { Toaster } from '@/components/ui/toaster';
import { useToast } from '@/components/ui/use-toast';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { ScenarioService } from '@/services/api';

const AppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [isCreatingProjection, setIsCreatingProjection] = useState(false);
  
  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <div className="hidden md:flex flex-col border-r w-64">
        <div className="p-4">
          <h1 className="text-xl font-bold">FF Projections</h1>
          <p className="text-sm text-muted-foreground">Enhanced Projection System</p>
        </div>
        <Separator />
        <ScrollArea className="flex-1 p-4">
          <MainNav currentPath={location.pathname} />
        </ScrollArea>
        <Separator />
        <div className="p-4">
          <p className="text-xs text-muted-foreground text-center">
            Version 0.2.0
          </p>
        </div>
      </div>
      
      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Top header */}
        <header className="border-b py-3 px-6 bg-background">
          <div className="flex items-center justify-between">
            <div className="md:hidden">
              <h1 className="text-lg font-bold">FF Projections</h1>
            </div>
            
            <div className="flex-1 px-4 max-w-md mx-auto md:ml-0">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Search players or teams..." 
                  className="pl-8 bg-muted/50"
                />
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <ThemeToggle />
              <Button size="icon" variant="ghost">
                <BellIcon className="h-5 w-5" />
              </Button>
              <Button size="sm" variant="outline" className="hidden md:flex items-center gap-2">
                <ArrowDownTrayIcon className="h-4 w-4" />
                Export
              </Button>
              <Button 
                size="sm" 
                onClick={() => navigate('/scenarios')}
                disabled={isCreatingProjection}
              >
                {isCreatingProjection ? 
                  "Creating..." : 
                  <span className="flex items-center gap-1">
                    <PlayIcon className="h-4 w-4" />
                    New Scenario
                  </span>
                }
              </Button>
            </div>
          </div>
        </header>
        
        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
        
        {/* Footer */}
        <footer className="border-t py-3 px-6 text-center text-sm text-muted-foreground">
          <p>Fantasy Football Projections © 2025 | Enhanced Statistical Model</p>
        </footer>
      </div>
      
      {/* Toast notifications */}
      <Toaster />
    </div>
  );
};

export default AppLayout;