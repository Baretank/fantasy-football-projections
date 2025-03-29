## Next Steps

### 1. Complete the ProjectionAdjuster Component

Your `projectionadjuster.tsx` file is coming along nicely, but it needs full API integration with your backend services. The implementation you've started is good but requires:

- Completing the error handling for API requests
- Adding loading states to provide feedback during API calls
- Implementing all the adjustment features defined in your services

### 2. Build the Dashboard Component

Create a dashboard to provide an overview of your projections:

```jsx
// src/components/Dashboard.tsx
import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ProjectionService, ScenarioService } from '@/services/api';

const Dashboard = () => {
  // State management for scenarios and top projections
  const [scenarios, setScenarios] = useState([]);
  const [topProjections, setTopProjections] = useState({});
  const [isLoading, setIsLoading] = useState(true);

  // Fetch data on component mount
  useEffect(() => {
    async function fetchData() {
      try {
        setIsLoading(true);
        const scenariosData = await ScenarioService.getScenarios();
        setScenarios(scenariosData);
        
        // For the selected/default scenario, get top projections by position
        if (scenariosData.length > 0) {
          const baselineScenario = scenariosData.find(s => s.is_baseline) || scenariosData[0];
          const byPosition = {};
          
          for (const position of ['QB', 'RB', 'WR', 'TE']) {
            const projections = await ProjectionService.getScenarioProjections(
              baselineScenario.scenario_id, 
              position
            );
            // Sort by half PPR points
            const sorted = projections.sort((a, b) => b.half_ppr - a.half_ppr).slice(0, 10);
            byPosition[position] = sorted;
          }
          
          setTopProjections(byPosition);
        }
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchData();
  }, []);

  return (
    <div className="grid grid-cols-2 gap-4 p-4">
      {/* Scenarios summary */}
      <Card>
        <CardHeader>
          <CardTitle>Projection Scenarios</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Scenario list with summary stats */}
          {/* Implementation details */}
        </CardContent>
      </Card>
      
      {/* Top projections by position */}
      {['QB', 'RB', 'WR', 'TE'].map(position => (
        <Card key={position}>
          <CardHeader>
            <CardTitle>Top {position}s</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Top players for this position */}
            {/* Implementation details */}
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default Dashboard;
```

### 3. Develop a ScenarioManager Component

Add a component for managing scenarios:

```jsx
// src/components/ScenarioManager.tsx
import React, { useState, useEffect } from 'react';
import { ScenarioService } from '@/services/api';
import { Scenario } from '@/types/index';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

const ScenarioManager = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [newScenario, setNewScenario] = useState({ name: '', description: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);

  // Fetch scenarios on mount
  useEffect(() => {
    fetchScenarios();
  }, []);

  const fetchScenarios = async () => {
    try {
      setIsLoading(true);
      const data = await ScenarioService.getScenarios();
      setScenarios(data);
    } catch (error) {
      console.error("Error fetching scenarios:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateScenario = async () => {
    try {
      setIsLoading(true);
      await ScenarioService.createScenario(
        newScenario.name,
        newScenario.description
      );
      // Reset form and refresh list
      setNewScenario({ name: '', description: '' });
      await fetchScenarios();
    } catch (error) {
      console.error("Error creating scenario:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloneScenario = async (scenarioId: string) => {
    try {
      setIsLoading(true);
      const name = prompt("Enter name for the new scenario:");
      if (!name) return;
      
      await ScenarioService.cloneScenario(scenarioId, name);
      await fetchScenarios();
    } catch (error) {
      console.error("Error cloning scenario:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Component implementation with forms, scenario list, etc.
  return (
    <div className="p-4">
      <div className="grid grid-cols-3 gap-4">
        {/* Create new scenario form */}
        <Card>
          <CardHeader>
            <CardTitle>Create New Scenario</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Form fields */}
          </CardContent>
          <CardFooter>
            <Button onClick={handleCreateScenario}>Create Scenario</Button>
          </CardFooter>
        </Card>
        
        {/* Scenario list */}
        <div className="col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Scenarios</CardTitle>
            </CardHeader>
            <CardContent>
              {/* List of scenarios with actions */}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default ScenarioManager;
```

### 4. Implement the TeamAdjuster Component

Create a component for applying team-level adjustments:

```jsx
// src/components/TeamAdjuster.tsx
import React, { useState, useEffect } from 'react';
import { PlayerService, ProjectionService } from '@/services/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const TeamAdjuster = () => {
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState('');
  const [adjustments, setAdjustments] = useState({
    pass_volume: 100,
    rush_volume: 100,
    scoring_rate: 100
  });
  const [affectedPlayers, setAffectedPlayers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch teams on mount
  useEffect(() => {
    async function fetchTeams() {
      try {
        const players = await PlayerService.getPlayers();
        const uniqueTeams = [...new Set(players.map(p => p.team))].sort();
        setTeams(uniqueTeams);
      } catch (error) {
        console.error("Error fetching teams:", error);
      }
    }
    
    fetchTeams();
  }, []);

  // Fetch affected players when team changes
  useEffect(() => {
    if (!selectedTeam) return;
    
    async function fetchPlayers() {
      try {
        setIsLoading(true);
        const players = await PlayerService.getPlayers(undefined, selectedTeam);
        setAffectedPlayers(players);
      } catch (error) {
        console.error("Error fetching team players:", error);
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchPlayers();
  }, [selectedTeam]);

  const handleAdjustment = (key, value) => {
    setAdjustments(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const applyTeamAdjustments = async () => {
    if (!selectedTeam) return;
    
    try {
      setIsLoading(true);
      
      // Convert percentages to factors
      const adjustmentFactors = Object.fromEntries(
        Object.entries(adjustments).map(([key, value]) => [key, value / 100])
      );
      
      await ProjectionService.applyTeamAdjustments(
        selectedTeam,
        2024, // Current season
        adjustmentFactors
      );
      
      // Could refresh affected player projections here
      
    } catch (error) {
      console.error("Error applying team adjustments:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4">
      <Card>
        <CardHeader>
          <CardTitle>Team-Level Adjustments</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Team selection */}
            <div>
              <label className="block mb-2">Select Team</label>
              <Select
                value={selectedTeam}
                onValueChange={setSelectedTeam}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select team" />
                </SelectTrigger>
                <SelectContent>
                  {teams.map(team => (
                    <SelectItem key={team} value={team}>{team}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Adjustment sliders */}
            {selectedTeam && (
              <>
                <div>
                  <label className="block mb-2">Pass Volume %</label>
                  <Slider
                    value={[adjustments.pass_volume]}
                    min={70}
                    max={130}
                    step={1}
                    onValueChange={([value]) => handleAdjustment('pass_volume', value)}
                  />
                  <div className="text-right text-sm text-gray-500">
                    {adjustments.pass_volume}% of baseline
                  </div>
                </div>
                
                <div>
                  <label className="block mb-2">Rush Volume %</label>
                  <Slider
                    value={[adjustments.rush_volume]}
                    min={70}
                    max={130}
                    step={1}
                    onValueChange={([value]) => handleAdjustment('rush_volume', value)}
                  />
                  <div className="text-right text-sm text-gray-500">
                    {adjustments.rush_volume}% of baseline
                  </div>
                </div>
                
                <div>
                  <label className="block mb-2">Scoring Rate %</label>
                  <Slider
                    value={[adjustments.scoring_rate]}
                    min={70}
                    max={130}
                    step={1}
                    onValueChange={([value]) => handleAdjustment('scoring_rate', value)}
                  />
                  <div className="text-right text-sm text-gray-500">
                    {adjustments.scoring_rate}% of baseline
                  </div>
                </div>
                
                <Button 
                  onClick={applyTeamAdjustments} 
                  disabled={isLoading}
                >
                  Apply Adjustments
                </Button>
                
                {/* Display affected players */}
                <div className="mt-6">
                  <h3 className="text-lg font-medium mb-2">Affected Players</h3>
                  {/* List of players */}
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default TeamAdjuster;
```

### 5. Create Main App Layout

Build the main app layout to tie everything together:

```jsx
// src/ProjectionApp.tsx
import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import PlayerSelect from './components/playerselect';
import StatsDisplay from './components/statsdisplay';
import ProjectionAdjuster from './components/projectionadjuster';
import Dashboard from './components/Dashboard';
import ScenarioManager from './components/ScenarioManager';
import TeamAdjuster from './components/TeamAdjuster';

const ProjectionApp = () => {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Fantasy Football Projections</h1>
      
      <Tabs defaultValue="dashboard" className="w-full">
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="players">Player Projections</TabsTrigger>
          <TabsTrigger value="scenarios">Scenarios</TabsTrigger>
          <TabsTrigger value="teams">Team Adjustments</TabsTrigger>
          <TabsTrigger value="import">Data Import</TabsTrigger>
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
        
        <TabsContent value="import" className="mt-4">
          {/* Data import component */}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ProjectionApp;
```

### 6. Create a Data Import Component

Build a component for importing data:

```jsx
// src/components/DataImport.tsx
import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const DataImport = () => {
  const [season, setSeason] = useState(2024);
  const [position, setPosition] = useState('');
  const [verifyData, setVerifyData] = useState(true);
  const [isImporting, setIsImporting] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });

  const handleImport = async () => {
    try {
      setIsImporting(true);
      setStatus({ type: 'info', message: 'Importing data...' });
      
      // Mock API call (implement actual API when ready)
      // await importService.importData(season, position, verifyData);
      
      // Simulate import process
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      setStatus({ 
        type: 'success', 
        message: `Successfully imported ${position || 'all positions'} for ${season} season.` 
      });
    } catch (error) {
      console.error("Import error:", error);
      setStatus({ 
        type: 'error', 
        message: `Error importing data: ${error.message}` 
      });
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="p-4">
      <Card>
        <CardHeader>
          <CardTitle>Import Season Data</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block mb-2">Season Year</label>
              <Input
                type="number"
                value={season}
                onChange={(e) => setSeason(Number(e.target.value))}
                min={2020}
                max={2030}
              />
            </div>
            
            <div>
              <label className="block mb-2">Position (Optional)</label>
              <Select
                value={position}
                onValueChange={setPosition}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Positions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Positions</SelectItem>
                  <SelectItem value="QB">Quarterbacks</SelectItem>
                  <SelectItem value="RB">Running Backs</SelectItem>
                  <SelectItem value="WR">Wide Receivers</SelectItem>
                  <SelectItem value="TE">Tight Ends</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-center space-x-2">
              <Checkbox
                id="verify"
                checked={verifyData}
                onCheckedChange={setVerifyData}
              />
              <label htmlFor="verify">Verify data consistency</label>
            </div>
            
            {status.message && (
              <Alert variant={status.type === 'error' ? 'destructive' : 'default'}>
                <AlertTitle>
                  {status.type === 'success' ? 'Success' : 
                   status.type === 'error' ? 'Error' : 'Status'}
                </AlertTitle>
                <AlertDescription>
                  {status.message}
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
        <CardFooter>
          <Button 
            onClick={handleImport} 
            disabled={isImporting}
          >
            {isImporting ? 'Importing...' : 'Import Data'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default DataImport;
```

### 7. Backend Improvements

Several areas of your backend could be improved:

1. Complete the fill player system in `scenario_service.py` to maintain team-level stat consistency
2. Add more field-level validation to API endpoints
3. Improve error handling with more specific error types
4. Implement API pagination for player lists

### 8. Testing Enhancements

Add comprehensive testing for both frontend and backend:

1. Create React component tests with React Testing Library
2. Add more integration tests for complete workflows
3. Implement end-to-end tests with tools like Cypress

## Implementation Strategy

1. First, complete the core `ProjectionAdjuster` component
2. Implement the main app layout
3. Build the Dashboard for an overview of data
4. Create the ScenarioManager for managing projection scenarios
5. Implement the TeamAdjuster for team-level changes
6. Add the DataImport component for data management
7. Refine the backend with improved error handling and validation
8. Add comprehensive testing