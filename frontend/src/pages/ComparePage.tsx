import React, { useState, useEffect } from 'react';
import { Logger } from '@/utils/logger';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import PlayerSelect from '@/components/playerselect';
import { 
  ArrowsRightLeftIcon,
  TrashIcon,
  ArrowPathIcon,
  PlusIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';
import {
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ComposedChart,
  ErrorBar,
  ReferenceLine
} from 'recharts';
import { ScenarioService, PlayerService, ProjectionService } from '@/services/api';
import { Player, Projection, Scenario } from '@/types/index';
import ProjectionRangeChart from '@/components/visualization/ProjectionRangeChart';
import { useToast } from '@/components/ui/use-toast';

const ComparePage: React.FC = () => {
  const { toast } = useToast();
  const [selectedPlayers, setSelectedPlayers] = useState<string[]>([]);
  const [playerData, setPlayerData] = useState<Record<string, any>>({});
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [projectionRangeData, setProjectionRangeData] = useState<any[]>([]);
  
  // Fetch scenarios on component mount
  useEffect(() => {
    async function fetchScenarios() {
      try {
        const data = await ScenarioService.getScenarios();
        setScenarios(data);
        
        // Set default scenario to baseline
        const baseline = data.find(s => s.is_baseline);
        if (baseline) {
          setSelectedScenario(baseline.scenario_id);
        } else if (data.length > 0) {
          setSelectedScenario(data[0].scenario_id);
        }
      } catch (err) {
        Logger.error("Error fetching scenarios:", err);
        toast({
          title: "Error",
          description: "Failed to load scenarios. Please try again.",
          variant: "destructive"
        });
      }
    }
    
    fetchScenarios();
  }, [toast]);
  
  // Load player data when selection changes
  useEffect(() => {
    async function fetchPlayerData() {
      if (selectedPlayers.length === 0 || !selectedScenario) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        const newPlayerData: Record<string, any> = {};
        const newRangeData: any[] = [];
        
        for (const playerId of selectedPlayers) {
          if (playerData[playerId]) {
            newPlayerData[playerId] = playerData[playerId];
            
            // Add existing player to range data if not already there
            const existingPlayer = playerData[playerId];
            const playerInRange = projectionRangeData.some(p => p.playerId === playerId);
            
            if (!playerInRange && existingPlayer.projection) {
              newRangeData.push({
                name: existingPlayer.name,
                position: existingPlayer.position,
                team: existingPlayer.team,
                playerId: playerId,
                value: existingPlayer.projection.half_ppr || 0,
                range: {
                  low: existingPlayer.range?.low?.half_ppr || 0,
                  high: existingPlayer.range?.high?.half_ppr || 0
                }
              });
            }
            
            continue;
          }
          
          // Fetch player details
          const player = await PlayerService.getPlayer(playerId);
          
          // Fetch projection for selected scenario
          const projections = await ProjectionService.getPlayerProjections(
            playerId, 
            selectedScenario
          );
          
          if (!projections || projections.length === 0) {
            toast({
              title: "No Projection",
              description: `No projection found for ${player.name} in the selected scenario.`,
              variant: "default"
            });
            continue;
          }
          
          // Get projection range (confidence intervals)
          let range = null;
          try {
            range = await ProjectionService.getProjectionRange(
              projections[0].projection_id,
              0.80
            );
          } catch (rangeErr) {
            Logger.warn(`Could not get range for ${player.name}:`, rangeErr);
            // Create a default range if API fails
            const halfPpr = projections[0].half_ppr || 0;
            range = {
              low: { half_ppr: halfPpr * 0.8 },
              high: { half_ppr: halfPpr * 1.2 }
            };
          }
          
          // Store combined data
          newPlayerData[playerId] = {
            ...player,
            projection: projections[0],
            range
          };
          
          // Add to range data for visualization
          newRangeData.push({
            name: player.name,
            position: player.position,
            team: player.team,
            playerId: playerId,
            value: projections[0].half_ppr || 0,
            range: {
              low: range?.low?.half_ppr || 0,
              high: range?.high?.half_ppr || 0
            }
          });
        }
        
        setPlayerData({ ...playerData, ...newPlayerData });
        setProjectionRangeData([...projectionRangeData, ...newRangeData]);
      } catch (err) {
        Logger.error("Error fetching player data:", err);
        setError("Failed to load player data. Please try again.");
        
        toast({
          title: "Error",
          description: "Failed to load player data. Please try again.",
          variant: "destructive"
        });
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchPlayerData();
  }, [selectedPlayers, selectedScenario, toast, playerData, projectionRangeData]);
  
  // Handle adding a player to comparison
  const handleAddPlayer = (playerId: string) => {
    if (selectedPlayers.includes(playerId)) {
      toast({
        title: "Already Selected",
        description: "This player is already in your comparison.",
        variant: "default"
      });
      return;
    }
    
    // Limit to 6 players for comparison
    if (selectedPlayers.length >= 6) {
      toast({
        title: "Limit Reached",
        description: "You can compare up to 6 players at once. Remove a player before adding another.",
        variant: "default"
      });
      return;
    }
    
    setSelectedPlayers([...selectedPlayers, playerId]);
  };
  
  // Handle removing a player from comparison
  const handleRemovePlayer = (playerId: string) => {
    setSelectedPlayers(selectedPlayers.filter(id => id !== playerId));
    setProjectionRangeData(projectionRangeData.filter(p => p.playerId !== playerId));
  };
  
  // Get all players with data loaded
  const getLoadedPlayers = () => {
    return selectedPlayers
      .filter(id => playerData[id])
      .map(id => playerData[id]);
  };
  
  // Generate stat comparison data
  const getComparisonData = (statKey: string, label: string) => {
    const players = getLoadedPlayers();
    
    return players.map(player => {
      const value = player.projection[statKey] || 0;
      const rangeLow = player.range?.low[statKey] || value * 0.8;
      const rangeHigh = player.range?.high[statKey] || value * 1.2;
      
      return {
        name: player.name,
        position: player.position,
        team: player.team,
        value,
        rangeLow,
        rangeHigh,
        label
      };
    });
  };
  
  // Generate radar chart data
  const getRadarData = () => {
    const players = getLoadedPlayers();
    if (players.length === 0) return [];
    
    // Define position-specific metrics
    const statKeys = [
      { key: 'half_ppr', label: 'Fantasy Pts', posFilter: ['QB', 'RB', 'WR', 'TE'] },
      // QB stats
      { key: 'pass_yards', label: 'Pass Yards', posFilter: ['QB'] },
      { key: 'pass_td', label: 'Pass TD', posFilter: ['QB'] },
      { key: 'completions', label: 'Completions', posFilter: ['QB'] },
      // RB stats
      { key: 'rush_yards', label: 'Rush Yards', posFilter: ['RB', 'QB'] },
      { key: 'rush_td', label: 'Rush TD', posFilter: ['RB', 'QB'] },
      { key: 'rush_att', label: 'Rush Att', posFilter: ['RB', 'QB'] },
      // Receiving stats
      { key: 'targets', label: 'Targets', posFilter: ['WR', 'TE', 'RB'] },
      { key: 'receptions', label: 'Receptions', posFilter: ['WR', 'TE', 'RB'] },
      { key: 'rec_yards', label: 'Rec Yards', posFilter: ['WR', 'TE', 'RB'] },
      { key: 'rec_td', label: 'Rec TD', posFilter: ['WR', 'TE', 'RB'] }
    ];
    
    // Get max values for normalization
    const maxValues: Record<string, number> = {};
    statKeys.forEach(({ key }) => {
      maxValues[key] = Math.max(
        ...players.map(p => p.projection[key] || 0),
        0.1 // Avoid division by zero
      );
    });
    
    // For each player, create a radar data point
    return players.map(player => {
      const radarPoint: Record<string, any> = {
        name: player.name,
        position: player.position,
        team: player.team
      };
      
      // Add normalized stats
      statKeys.forEach(({ key, label, posFilter }) => {
        // Skip stats that don't apply to this position
        if (posFilter && !posFilter.includes(player.position)) {
          radarPoint[label] = 0;
          return;
        }
        
        const value = player.projection[key] || 0;
        radarPoint[label] = (value / maxValues[key]) * 100;
      });
      
      return radarPoint;
    });
  };
  
  // Get color for a player (consistent across charts)
  const getPlayerColor = (index: number) => {
    const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00C49F', '#FFBB28'];
    return colors[index % colors.length];
  };
  
  // Handle scenario change
  const handleScenarioChange = (scenarioId: string) => {
    setSelectedScenario(scenarioId);
    
    // Clear existing projection data when scenario changes
    setPlayerData({});
    setProjectionRangeData([]);
    
    toast({
      title: "Scenario Changed",
      description: "Projections will be loaded for the new scenario.",
      variant: "default"
    });
  };
  
  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Player Comparison</h1>
          <p className="text-muted-foreground">
            Compare projections and statistics for multiple players
          </p>
        </div>
        
        <div className="flex flex-wrap gap-3">
          <div className="w-72">
            <PlayerSelect
              onSelect={handleAddPlayer}
              placeholder="Add player to compare..."
            />
          </div>
          
          <select
            className="border rounded py-2 px-3 bg-background"
            value={selectedScenario || ''}
            onChange={(e) => handleScenarioChange(e.target.value)}
          >
            <option value="" disabled>
              Select Scenario
            </option>
            {scenarios.map((scenario) => (
              <option key={scenario.scenario_id} value={scenario.scenario_id}>
                {scenario.name}
                {scenario.is_baseline ? ' (Baseline)' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      <Separator />
      
      {/* Projection Range Chart */}
      {projectionRangeData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Fantasy Point Comparison</CardTitle>
            <CardDescription>
              Projected half-PPR points with 80% confidence intervals
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[400px]">
              <ProjectionRangeChart 
                data={projectionRangeData}
                yAxisLabel="Half PPR Points"
                height="100%"
                showAverage={true}
              />
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <p className="text-sm text-muted-foreground">
              Showing projections with uncertainty ranges for selected players
            </p>
            <Button variant="outline" size="sm" onClick={() => setProjectionRangeData([])}>
              Clear Chart
            </Button>
          </CardFooter>
        </Card>
      )}
      
      {/* Player cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {selectedPlayers.map((playerId, index) => {
          const player = playerData[playerId];
          const isLoaded = !!player;
          
          return (
            <Card key={playerId} className="relative">
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2"
                onClick={() => handleRemovePlayer(playerId)}
              >
                <TrashIcon className="h-4 w-4" />
              </Button>
              
              <CardHeader className="pb-2">
                {isLoaded ? (
                  <>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle>{player.name}</CardTitle>
                        <CardDescription>{player.team} - {player.position}</CardDescription>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="h-12 flex items-center justify-center">
                    <span className="text-muted-foreground">Loading...</span>
                  </div>
                )}
              </CardHeader>
              
              <CardContent className="pb-4">
                {isLoaded ? (
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <div className="text-center">
                        <div className="text-3xl font-bold text-primary">
                          {player.projection.half_ppr.toFixed(1)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Fantasy Points
                        </div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-sm font-bold flex gap-2 items-baseline">
                          <span className="text-muted-foreground text-xs">Range:</span>
                          <span className="text-yellow-600">
                            {player.range?.low.half_ppr?.toFixed(1)}
                          </span>
                          <span>-</span>
                          <span className="text-green-600">
                            {player.range?.high.half_ppr?.toFixed(1)}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          80% Confidence
                        </div>
                      </div>
                    </div>
                    
                    <Separator />
                    
                    <div className="space-y-2">
                      {player.position === 'QB' && (
                        <>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="text-muted-foreground">Pass:</span>{' '}
                              {player.projection.pass_yards?.toFixed(0)} yds
                            </div>
                            <div>
                              <span className="text-muted-foreground">TDs:</span>{' '}
                              {player.projection.pass_td?.toFixed(1)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Comp/Att:</span>{' '}
                              {player.projection.completions?.toFixed(0)}/{player.projection.pass_attempts?.toFixed(0)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Rush:</span>{' '}
                              {player.projection.rush_yards?.toFixed(0)} yds
                            </div>
                          </div>
                        </>
                      )}
                      
                      {player.position === 'RB' && (
                        <>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="text-muted-foreground">Rush:</span>{' '}
                              {player.projection.rush_yards?.toFixed(0)} yds
                            </div>
                            <div>
                              <span className="text-muted-foreground">Rush TDs:</span>{' '}
                              {player.projection.rush_td?.toFixed(1)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Attempts:</span>{' '}
                              {player.projection.rush_att?.toFixed(0)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Rec:</span>{' '}
                              {player.projection.receptions?.toFixed(0)}/{player.projection.targets?.toFixed(0)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Rec Yards:</span>{' '}
                              {player.projection.rec_yards?.toFixed(0)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Rec TDs:</span>{' '}
                              {player.projection.rec_td?.toFixed(1)}
                            </div>
                          </div>
                        </>
                      )}
                      
                      {(player.position === 'WR' || player.position === 'TE') && (
                        <>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="text-muted-foreground">Rec:</span>{' '}
                              {player.projection.receptions?.toFixed(0)}/{player.projection.targets?.toFixed(0)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Yards:</span>{' '}
                              {player.projection.rec_yards?.toFixed(0)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">TDs:</span>{' '}
                              {player.projection.rec_td?.toFixed(1)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">YPR:</span>{' '}
                              {player.projection.receptions > 0 
                                ? (player.projection.rec_yards / player.projection.receptions).toFixed(1) 
                                : '0.0'}
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="h-32 flex items-center justify-center">
                    <div className="flex items-center text-muted-foreground">
                      <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                      Loading player data...
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
        
        {/* Empty card for adding players */}
        {selectedPlayers.length < 6 && (
          <Card className="border-dashed flex items-center justify-center">
            <CardContent className="p-6">
              <div className="text-center">
                <PlayerSelect
                  onSelect={handleAddPlayer}
                  buttonProps={{
                    variant: "outline",
                    size: "lg",
                    className: "w-full h-24 flex-col gap-2"
                  }}
                  buttonContent={
                    <>
                      <PlusIcon className="h-8 w-8 text-muted-foreground" />
                      <span className="text-muted-foreground">Add Player</span>
                    </>
                  }
                />
              </div>
            </CardContent>
          </Card>
        )}
      </div>
      
      {/* Comparison Charts */}
      {getLoadedPlayers().length > 1 && (
        <div className="space-y-6">
          <Tabs defaultValue="radar" className="w-full">
            <TabsList>
              <TabsTrigger value="radar">Performance Radar</TabsTrigger>
              <TabsTrigger value="yards">Yardage</TabsTrigger>
              <TabsTrigger value="touchdowns">Touchdowns</TabsTrigger>
              <TabsTrigger value="efficiency">Efficiency Metrics</TabsTrigger>
            </TabsList>
            
            <TabsContent value="radar" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Performance Radar</CardTitle>
                  <CardDescription>
                    Relative strengths across key metrics (normalized to 0-100 scale)
                  </CardDescription>
                </CardHeader>
                <CardContent className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart 
                      cx="50%"
                      cy="50%"
                      outerRadius={150}
                      width={500} 
                      height={500} 
                      data={getRadarData()}
                    >
                      <PolarGrid />
                      <PolarAngleAxis dataKey="name" />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} />
                      
                      {getLoadedPlayers().map((player, index) => {
                        const keyToUse = player.position === 'QB' 
                          ? 'Pass Yards' 
                          : player.position === 'RB'
                            ? 'Rush Yards'
                            : 'Rec Yards';
                        
                        return (
                          <Radar
                            key={player.player_id}
                            name={player.name}
                            dataKey={keyToUse}
                            stroke={getPlayerColor(index)}
                            fill={getPlayerColor(index)}
                            fillOpacity={0.6}
                          />
                        );
                      })}
                      
                      <Legend />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="yards" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Yardage Comparison</CardTitle>
                  <CardDescription>
                    Compare projected yards by category
                  </CardDescription>
                </CardHeader>
                <CardContent className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={[
                        ...getComparisonData('pass_yards', 'Pass Yards'),
                        ...getComparisonData('rush_yards', 'Rush Yards'),
                        ...getComparisonData('rec_yards', 'Receiving Yards')
                      ]}
                      margin={{ top: 20, right: 30, left: 20, bottom: 40 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis 
                        label={{ 
                          value: 'Yards', 
                          angle: -90, 
                          position: 'insideLeft' 
                        }}
                      />
                      <Tooltip
                        formatter={(value) => [Number(value).toFixed(0), 'Yards']}
                      />
                      <Legend />
                      <Bar 
                        dataKey="value" 
                        name="Yards" 
                        fill="#8884d8"
                        stackId="a"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="touchdowns" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Touchdown Comparison</CardTitle>
                  <CardDescription>
                    Compare projected touchdowns by category
                  </CardDescription>
                </CardHeader>
                <CardContent className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={[
                        ...getComparisonData('pass_td', 'Pass TDs'),
                        ...getComparisonData('rush_td', 'Rush TDs'),
                        ...getComparisonData('rec_td', 'Receiving TDs')
                      ]}
                      margin={{ top: 20, right: 30, left: 20, bottom: 40 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis 
                        label={{ 
                          value: 'Touchdowns', 
                          angle: -90, 
                          position: 'insideLeft' 
                        }}
                      />
                      <Tooltip
                        formatter={(value) => [Number(value).toFixed(1), 'TDs']}
                      />
                      <Legend />
                      <Bar 
                        dataKey="value" 
                        name="Touchdowns" 
                        fill="#8884d8"
                        stackId="a"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="efficiency" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Efficiency Metrics</CardTitle>
                  <CardDescription>
                    Compare key efficiency stats by position
                  </CardDescription>
                </CardHeader>
                <CardContent className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={getLoadedPlayers().map(player => {
                        // Different efficiency metrics by position
                        let effStat = 0;
                        let effLabel = '';
                        
                        if (player.position === 'QB') {
                          // Yards per attempt
                          effStat = player.projection.pass_attempts > 0 
                            ? player.projection.pass_yards / player.projection.pass_attempts 
                            : 0;
                          effLabel = 'Yards/Att';
                        } else if (player.position === 'RB') {
                          // Yards per carry
                          effStat = player.projection.rush_att > 0 
                            ? player.projection.rush_yards / player.projection.rush_att 
                            : 0;
                          effLabel = 'Yards/Carry';
                        } else {
                          // Yards per reception
                          effStat = player.projection.receptions > 0 
                            ? player.projection.rec_yards / player.projection.receptions 
                            : 0;
                          effLabel = 'Yards/Rec';
                        }
                        
                        return {
                          name: player.name,
                          position: player.position,
                          team: player.team,
                          value: effStat,
                          label: effLabel
                        };
                      })}
                      margin={{ top: 20, right: 30, left: 20, bottom: 40 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis 
                        label={{ 
                          value: 'Efficiency', 
                          angle: -90, 
                          position: 'insideLeft' 
                        }}
                      />
                      <Tooltip
                        formatter={(value, name, props) => {
                          if (name === 'value') {
                            return [Number(value).toFixed(2), props.payload.label];
                          }
                          return [value, name];
                        }}
                        labelFormatter={(label) => label}
                      />
                      <Legend />
                      <Bar 
                        dataKey="value" 
                        name="Efficiency" 
                        fill="#8884d8"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      )}
      
      {/* Empty state when no players selected */}
      {selectedPlayers.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="p-8">
            <div className="text-center space-y-4">
              <ArrowsRightLeftIcon className="h-12 w-12 text-muted-foreground mx-auto" />
              <h3 className="text-lg font-medium">No Players Selected</h3>
              <p className="text-muted-foreground max-w-md mx-auto">
                Add players to compare their projections, stats, and potential ranges.
                Select up to 6 players to compare side-by-side.
              </p>
              <div className="pt-4">
                <PlayerSelect
                  onSelect={handleAddPlayer}
                  buttonProps={{
                    size: "lg",
                    className: "mx-auto"
                  }}
                  buttonContent="Add First Player"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ComparePage;