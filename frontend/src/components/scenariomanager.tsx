import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  LineChart,
  Line
} from 'recharts';

import { ScenarioService, PlayerService } from '@/services/api';
import { Player, Projection, Scenario, COMPARISON_STATS } from '@/types/index';

interface ComparisonData {
  player_id: string;
  name: string;
  team: string;
  position: string;
  scenarios: Record<string, Record<string, number>>;
}

const ScenarioManager: React.FC = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [newScenarioName, setNewScenarioName] = useState<string>('');
  const [newScenarioDescription, setNewScenarioDescription] = useState<string>('');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('');
  const [selectedComparisonScenarioIds, setSelectedComparisonScenarioIds] = useState<string[]>([]);
  const [selectedPosition, setSelectedPosition] = useState<string>('all_positions');
  const [comparisonData, setComparisonData] = useState<ComparisonData[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState<boolean>(false);
  const [isCloneDialogOpen, setIsCloneDialogOpen] = useState<boolean>(false);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  
  // Fetch scenarios on component mount
  useEffect(() => {
    fetchScenarios();
  }, []);

  const fetchScenarios = async () => {
    try {
      setIsLoading(true);
      console.log("Fetching scenarios from API...");
      const data = await ScenarioService.getScenarios();
      console.log("Scenarios fetched successfully:", data);
      setScenarios(data);
      
      // Set default selected scenario to the baseline
      const baseline = data.find(s => s.is_baseline);
      if (baseline) {
        console.log("Found baseline scenario:", baseline.name);
        setSelectedScenarioId(baseline.scenario_id);
        setSelectedComparisonScenarioIds([baseline.scenario_id]);
      } else if (data.length > 0) {
        console.log("No baseline found, using first scenario:", data[0].name);
        setSelectedScenarioId(data[0].scenario_id);
        setSelectedComparisonScenarioIds([data[0].scenario_id]);
      } else {
        console.log("No scenarios found in response");
      }
    } catch (err) {
      console.error('Error fetching scenarios:', err);
      setError('Failed to load scenarios');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle creating a new scenario
  const handleCreateScenario = async () => {
    try {
      setIsLoading(true);
      await ScenarioService.createScenario(
        newScenarioName,
        newScenarioDescription,
        false // Not baseline
      );
      
      // Reset form
      setNewScenarioName('');
      setNewScenarioDescription('');
      setIsCreateDialogOpen(false);
      
      // Refresh scenarios
      await fetchScenarios();
    } catch (err) {
      console.error('Error creating scenario:', err);
      setError('Failed to create scenario');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle cloning a scenario
  const handleCloneScenario = async () => {
    if (!selectedScenarioId) return;
    
    try {
      setIsLoading(true);
      await ScenarioService.cloneScenario(
        selectedScenarioId,
        newScenarioName,
        newScenarioDescription
      );
      
      // Reset form
      setNewScenarioName('');
      setNewScenarioDescription('');
      setIsCloneDialogOpen(false);
      
      // Refresh scenarios
      await fetchScenarios();
    } catch (err) {
      console.error('Error cloning scenario:', err);
      setError('Failed to clone scenario');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle deleting a scenario
  const handleDeleteScenario = async (scenarioId: string) => {
    if (!window.confirm('Are you sure you want to delete this scenario?')) {
      return;
    }
    
    try {
      setIsLoading(true);
      await ScenarioService.deleteScenario(scenarioId);
      
      // If we deleted the selected scenario, select the baseline
      if (scenarioId === selectedScenarioId) {
        const baseline = scenarios.find(s => s.is_baseline);
        if (baseline) {
          setSelectedScenarioId(baseline.scenario_id);
        } else if (scenarios.length > 1) {
          // Find another scenario that's not the one we just deleted
          const anotherScenario = scenarios.find(s => s.scenario_id !== scenarioId);
          if (anotherScenario) {
            setSelectedScenarioId(anotherScenario.scenario_id);
          } else {
            setSelectedScenarioId('');
          }
        } else {
          setSelectedScenarioId('');
        }
      }
      
      // Update comparison selection if needed
      setSelectedComparisonScenarioIds(prev => 
        prev.filter(id => id !== scenarioId)
      );
      
      // Refresh scenarios
      await fetchScenarios();
    } catch (err) {
      console.error('Error deleting scenario:', err);
      setError('Failed to delete scenario');
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle a scenario for comparison
  const toggleScenarioForComparison = (scenarioId: string) => {
    setSelectedComparisonScenarioIds(prev => {
      if (prev.includes(scenarioId)) {
        return prev.filter(id => id !== scenarioId);
      } else {
        return [...prev, scenarioId];
      }
    });
  };

  // Compare scenarios
  const compareScenarios = async () => {
    if (selectedComparisonScenarioIds.length < 1) {
      setError('Select at least one scenario to compare');
      return;
    }
    
    try {
      setIsComparing(true);
      setIsLoading(true);
      
      console.log("Sending scenario comparison request with:", {
        scenarioIds: selectedComparisonScenarioIds,
        position: selectedPosition !== 'all_positions' ? selectedPosition : undefined
      });
      
      const response = await ScenarioService.compareScenarios(
        selectedComparisonScenarioIds,
        selectedPosition !== 'all_positions' ? selectedPosition : undefined
      );
      
      console.log("Received comparison response:", response);
      
      if (!response.players || !Array.isArray(response.players)) {
        console.error("Invalid comparison response format:", response);
        setError('Received invalid comparison data format');
        setComparisonData([]);
        return;
      }
      
      setComparisonData(response.players);
      console.log(`Successfully loaded comparison data for ${response.players.length} players`);
    } catch (err) {
      console.error('Error comparing scenarios:', err);
      setError(`Failed to compare scenarios: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setComparisonData([]);
    } finally {
      setIsLoading(false);
      setIsComparing(true);
    }
  };

  // Get formatted comparison data for chart
  const getChartData = () => {
    const chartData: any[] = [];
    
    // For each player in the comparison data
    comparisonData.slice(0, 10).forEach(player => {
      const playerData: any = {
        name: player.name,
        position: player.position,
        team: player.team
      };
      
      // Add each scenario's value for this player
      Object.entries(player.scenarios).forEach(([scenarioId, stats]) => {
        const scenario = scenarios.find(s => s.scenario_id === scenarioId);
        if (scenario) {
          playerData[scenario.name] = stats.half_ppr;
        }
      });
      
      chartData.push(playerData);
    });
    
    return chartData;
  };

  // Calculate the difference between scenarios for a player
  const calculateDifference = (player: ComparisonData) => {
    if (selectedComparisonScenarioIds.length < 2) return "N/A";
    
    const scenarioValues = selectedComparisonScenarioIds.map(id => {
      return player.scenarios[id]?.half_ppr || 0;
    });
    
    if (scenarioValues.length < 2) return "N/A";
    
    const diff = scenarioValues[1] - scenarioValues[0];
    const pctDiff = scenarioValues[0] === 0 ? 0 : (diff / scenarioValues[0]) * 100;
    
    return `${diff.toFixed(1)} pts (${pctDiff.toFixed(1)}%)`;
  };

  return (
    <div className="grid grid-cols-12 gap-4 p-4">
      {/* Scenario Management */}
      <Card className="col-span-4">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Scenarios</CardTitle>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm">New Scenario</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create New Scenario</DialogTitle>
                  <DialogDescription>
                    Create a new projection scenario for "what-if" analysis.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="scenario-name">Scenario Name</Label>
                    <Input
                      id="scenario-name"
                      placeholder="e.g., High Pass Volume"
                      value={newScenarioName}
                      onChange={(e) => setNewScenarioName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="scenario-description">Description (optional)</Label>
                    <Input
                      id="scenario-description"
                      placeholder="Brief description of this scenario"
                      value={newScenarioDescription}
                      onChange={(e) => setNewScenarioDescription(e.target.value)}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateScenario} disabled={!newScenarioName || isLoading}>
                    Create Scenario
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          <CardDescription>
            Manage "what-if" projection scenarios
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && !isComparing ? (
            <div className="flex items-center justify-center h-96 text-muted-foreground">
              Loading scenarios...
            </div>
          ) : scenarios.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-96 text-muted-foreground">
              <p className="mb-4">No scenarios found</p>
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                Create Your First Scenario
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[30px]"></TableHead>
                    <TableHead>Scenario</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scenarios.map(scenario => (
                    <TableRow 
                      key={scenario.scenario_id}
                      className={scenario.scenario_id === selectedScenarioId ? "bg-muted" : ""}
                    >
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selectedComparisonScenarioIds.includes(scenario.scenario_id)}
                          onChange={() => toggleScenarioForComparison(scenario.scenario_id)}
                          className="h-4 w-4 rounded border-gray-300"
                        />
                      </TableCell>
                      <TableCell 
                        className="font-medium cursor-pointer"
                        onClick={() => setSelectedScenarioId(scenario.scenario_id)}
                      >
                        {scenario.name}
                        {scenario.description && (
                          <p className="text-xs text-muted-foreground">
                            {scenario.description}
                          </p>
                        )}
                      </TableCell>
                      <TableCell>
                        {scenario.is_baseline ? (
                          <Badge>Baseline</Badge>
                        ) : (
                          <Badge variant="outline">Alternative</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => {
                              setSelectedScenarioId(scenario.scenario_id);
                              setNewScenarioName(`${scenario.name} Copy`);
                              setNewScenarioDescription(scenario.description || '');
                              setIsCloneDialogOpen(true);
                            }}
                          >
                            Clone
                          </Button>
                          {!scenario.is_baseline && (
                            <Button 
                              variant="ghost" 
                              size="sm"
                              className="text-red-500 hover:text-red-700"
                              onClick={() => handleDeleteScenario(scenario.scenario_id)}
                            >
                              Delete
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Clone dialog */}
              <Dialog open={isCloneDialogOpen} onOpenChange={setIsCloneDialogOpen}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Clone Scenario</DialogTitle>
                    <DialogDescription>
                      Create a copy of the selected scenario to make modifications.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="clone-name">New Scenario Name</Label>
                      <Input
                        id="clone-name"
                        placeholder="e.g., High Pass Volume (Modified)"
                        value={newScenarioName}
                        onChange={(e) => setNewScenarioName(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="clone-description">Description (optional)</Label>
                      <Input
                        id="clone-description"
                        placeholder="Brief description of this scenario"
                        value={newScenarioDescription}
                        onChange={(e) => setNewScenarioDescription(e.target.value)}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsCloneDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleCloneScenario} disabled={!newScenarioName || isLoading}>
                      Clone Scenario
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              {/* Comparison Controls */}
              <div className="pt-4 space-y-4">
                <div className="flex items-end gap-4">
                  <div className="flex-1">
                    <Label htmlFor="filter-position" className="mb-2 block">
                      Filter by Position
                    </Label>
                    <Select 
                      value={selectedPosition} 
                      onValueChange={setSelectedPosition}
                    >
                      <SelectTrigger id="filter-position">
                        <SelectValue placeholder="All Positions" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all_positions">All Positions</SelectItem>
                        <SelectItem value="QB">QB</SelectItem>
                        <SelectItem value="RB">RB</SelectItem>
                        <SelectItem value="WR">WR</SelectItem>
                        <SelectItem value="TE">TE</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button 
                    className="flex-1"
                    onClick={compareScenarios}
                    disabled={selectedComparisonScenarioIds.length < 1 || isLoading}
                  >
                    Compare Scenarios
                  </Button>
                </div>
                
                {selectedComparisonScenarioIds.length < 1 && (
                  <p className="text-sm text-muted-foreground">
                    Select at least one scenario to compare
                  </p>
                )}
                
                {selectedComparisonScenarioIds.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {selectedComparisonScenarioIds.map(id => {
                      const scenario = scenarios.find(s => s.scenario_id === id);
                      return scenario ? (
                        <Badge key={id} variant="secondary" className="text-xs">
                          {scenario.name}
                        </Badge>
                      ) : null;
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Comparison Results */}
      <Card className="col-span-8">
        <CardHeader>
          <CardTitle>Scenario Comparison</CardTitle>
          <CardDescription>
            {isComparing 
              ? `Comparing ${selectedComparisonScenarioIds.length} scenarios` 
              : "Select scenarios to compare"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && isComparing ? (
            <div className="flex items-center justify-center h-96 text-muted-foreground">
              Comparing scenarios...
            </div>
          ) : !isComparing ? (
            <div className="flex flex-col items-center justify-center h-96 text-muted-foreground">
              <p>Select scenarios and click "Compare Scenarios" to see results</p>
            </div>
          ) : comparisonData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-96 text-muted-foreground">
              <p>No players found for the selected criteria</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Comparison chart */}
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={getChartData()}
                    margin={{ top: 5, right: 20, left: 20, bottom: 60 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="name" 
                      angle={-45} 
                      textAnchor="end" 
                      height={80} 
                    />
                    <YAxis label={{ value: 'Half PPR', angle: -90, position: 'insideLeft' }} />
                    <Tooltip 
                      formatter={(value) => [Number(value).toFixed(1), 'Fantasy Points']}
                      labelFormatter={(label) => {
                        const player = getChartData().find(p => p.name === label);
                        return `${label} (${player?.team} - ${player?.position})`;
                      }}
                    />
                    <Legend />
                    {selectedComparisonScenarioIds.map(id => {
                      const scenario = scenarios.find(s => s.scenario_id === id);
                      if (!scenario) return null;
                      
                      return (
                        <Bar 
                          key={id} 
                          dataKey={scenario.name} 
                          fill={`#${(parseInt(id, 16) % 0xffffff).toString(16).padStart(6, '0')}`} 
                        />
                      );
                    })}
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Comparison table */}
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Player</TableHead>
                      <TableHead>Pos</TableHead>
                      <TableHead>Team</TableHead>
                      {selectedComparisonScenarioIds.map(id => {
                        const scenario = scenarios.find(s => s.scenario_id === id);
                        return scenario ? (
                          <TableHead key={id}>{scenario.name}</TableHead>
                        ) : null;
                      })}
                      {selectedComparisonScenarioIds.length > 1 && (
                        <TableHead>Difference</TableHead>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {comparisonData.map(player => (
                      <TableRow key={player.player_id}>
                        <TableCell className="font-medium">{player.name}</TableCell>
                        <TableCell>{player.position}</TableCell>
                        <TableCell>{player.team}</TableCell>
                        {selectedComparisonScenarioIds.map(id => {
                          const value = player.scenarios[id]?.half_ppr;
                          return (
                            <TableCell key={id}>
                              {value !== undefined ? value.toFixed(1) : 'N/A'}
                            </TableCell>
                          );
                        })}
                        {selectedComparisonScenarioIds.length > 1 && (
                          <TableCell>
                            <span className={
                              selectedComparisonScenarioIds.length < 2 || 
                              player.scenarios[selectedComparisonScenarioIds[1]]?.half_ppr === undefined ||
                              player.scenarios[selectedComparisonScenarioIds[0]]?.half_ppr === undefined
                                ? ""
                                : player.scenarios[selectedComparisonScenarioIds[1]]?.half_ppr > player.scenarios[selectedComparisonScenarioIds[0]]?.half_ppr
                                  ? "text-green-500"
                                  : "text-red-500"
                            }>
                              {calculateDifference(player)}
                            </span>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ScenarioManager;