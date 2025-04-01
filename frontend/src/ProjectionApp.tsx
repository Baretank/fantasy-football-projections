import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import PlayerSelect from './components/playerselect';
import StatsDisplay from './components/statsdisplay';
import ProjectionAdjuster from './components/projectionadjuster';
import TeamAdjuster from './components/teamadjuster';
import ScenarioManager from './components/scenariomanager';
import Dashboard from './components/dashboard';
import { Button } from '@/components/ui/button';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

const ProjectionApp: React.FC = () => {
  const [isDataImportOpen, setIsDataImportOpen] = useState(false);

  return (
    <div className="container mx-auto py-4 px-2">
      <header className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Fantasy Football Projections</h1>
          <p className="text-muted-foreground">Enhanced statistical projection system</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            Documentation
          </Button>
          <Dialog open={isDataImportOpen} onOpenChange={setIsDataImportOpen}>
            <DialogTrigger asChild>
              <Button variant="secondary" size="sm">
                Import Data
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Import Projection Data</DialogTitle>
                <DialogDescription>
                  Import data from various sources to update your projections
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <p className="text-sm text-muted-foreground">
                  Select one of the following data import options:
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <Button>
                    Import from Excel
                  </Button>
                  <Button>
                    Import from CSV
                  </Button>
                  <Button>
                    Import from API
                  </Button>
                  <Button>
                    Manual Entry
                  </Button>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsDataImportOpen(false)}>
                  Cancel
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </header>
      
      <Tabs defaultValue="dashboard" className="w-full">
        <TabsList className="grid grid-cols-4 w-full">
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="players">Player Projections</TabsTrigger>
          <TabsTrigger value="scenarios">Scenarios</TabsTrigger>
          <TabsTrigger value="teams">Team Adjustments</TabsTrigger>
        </TabsList>
        
        <TabsContent value="dashboard" className="mt-4">
          <Dashboard />
        </TabsContent>
        
        <TabsContent value="players" className="mt-4">
          <ProjectionAdjuster />
        </TabsContent>
        
        <TabsContent value="scenarios" className="mt-4">
          <ScenarioManager />
        </TabsContent>
        
        <TabsContent value="teams" className="mt-4">
          <TeamAdjuster />
        </TabsContent>
      </Tabs>
      
      <footer className="mt-8 pt-4 border-t text-center text-sm text-muted-foreground">
        <p>Fantasy Football Projections v0.2.0 | Enhanced Statistical Model</p>
      </footer>
    </div>
  );
};

export default ProjectionApp;