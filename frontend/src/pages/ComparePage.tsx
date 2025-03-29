import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import PlayerSelect from '@/components/playerselect';
import { 
  ArrowsRightLeftIcon,
  TrashIcon,
  ArrowPathIcon,
  PlusIcon
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
  Radar
} from 'recharts';
import { ScenarioService, PlayerService, ProjectionService } from '@/services/api';
import { Player, Projection, Scenario } from '@/types/index';

const ComparePage: React.FC = () => {
  const [selectedPlayers, setSelectedPlayers] = useState<string[]>([]);
  const [playerData, setPlayerData] = useState<Record<string, any>>({});
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
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
        console.error("Error fetching scenarios:", err);
      }
    }
    
    fetchScenarios();
  }, []);
  
  // Load player data when selection changes
  useEffect(() => {
    async function fetchPlayerData() {
      if (selectedPlayers.length === 0 || !selectedScenario) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        const newPlayerData: Record<string, any> = {};
        
        for (const playerId of selectedPlayers) {
          if (playerData[playerId]) {
            newPlayerData[playerId] = playerData[playerId];
            continue;
          }
          
          // Fetch player details
          const player = await PlayerService.getPlayer(playerId);
          
          // Fetch projection for selected scenario
          const projections = await ProjectionService.getPlayerProjections(
            playerId, 
            selectedScenario
          );
          
          // Get projection range (confidence intervals)
          const range = await ProjectionService.getProjectionRange(
            projections[0].projection_id,
            0.80
          );
          
          // Store combined data
          newPlayerData[playerId] = {
            ...player,
            projection: projections[0],
            range
          };
        }
        
        setPlayerData({ ...playerData, ...newPlayerData });
      } catch (err) {
        console.error("Error fetching player data:", err);
        setError("Failed to load player data. Please try again.");
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchPlayerData();
  }, [selectedPlayers, selectedScenario]);
  
  // Handle adding a player to comparison
  const handleAddPlayer = (playerId: string) => {
    if (selectedPlayers.includes(playerId)) return;
    
    // Limit to 4 players for comparison
    if (selectedPlayers.length >= 4) {
      setSelectedPlayers([...selectedPlayers.slice(1), playerId]);
    } else {
      setSelectedPlayers([...selectedPlayers, playerId]);
    }
  };
  
  // Handle removing a player from comparison
  const handleRemovePlayer = (playerId: string) => {
    setSelectedPlayers(selectedPlayers.filter(id => id !== playerId));
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
    
    // Normalize all stats to 0-100 scale
    const statKeys = [
      { key: 'half_ppr', label: 'Fantasy Pts' },
      // QB stats
      { key: 'pass_yards', label: 'Pass Yards', posFilter: ['QB'] },
      { key: 'pass_td', label: 'Pass TD', posFilter: ['QB'] },
      // RB stats
      { key: 'rush_yards', label: 'Rush Yards', posFilter: ['RB', 'QB'] },
      { key: 'rush_td', label: 'Rush TD', posFilter: ['RB', 'QB'] },
      // Receiving stats
      { key: 'targets', label: 'Targets', posFilter: ['WR', 'TE', 'RB'] },
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
    const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300'];
    return colors[index % colors.length];
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
            onChange={(e) => setSelectedScenario(e.target.value)}
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
      
      {/* Player cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
                              <span className="text-muted-foreground">Rush:</span>{' '}
                              {player.projection.rush_yards?.toFixed(0)} yds
                            </div>
                            <div>
                              <span className="text-muted-foreground">Rush TDs:</span>{' '}
                              {player.projection.rush_td?.toFixed(1)}
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
                              <span className="text-muted-foreground">Rec:</span>{' '}
                              {player.projection.rec_yards?.toFixed(0)} yds
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
                              {player.projection.rec_yards?.toFixed(0)} yds
                            </div>
                            <div>
                              <span className="text-muted-foreground">Rec TDs:</span>{' '}
                              {player.projection.rec_td?.toFixed(1)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Targets:</span>{' '}
                              {player.projection.targets?.toFixed(0)}
                            </div>
                            <div>
                              <span className="text-muted-foreground">Receptions:</span>{' '}
                              {player.projection.receptions?.toFixed(0)}
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="h-32 flex items-center justify-center">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-muted-foreground"
                      disabled
                    >
                      <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                      Loading player data...
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
        
        {/* Empty card for adding players */}
        {selectedPlayers.length < 4 && (
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
      {getLoadedPlayers().length > 0 && (
        <div className="space-y-6">
          <Tabs defaultValue="fantasy" className="w-full">
            <TabsList>
              <TabsTrigger value="fantasy">Fantasy Points</TabsTrigger>
              <TabsTrigger value="yards">Yardage</TabsTrigger>
              <TabsTrigger value="touchdowns">Touchdowns</TabsTrigger>
              <TabsTrigger value="radar">Radar Comparison</TabsTrigger>
            </TabsList>
            
            <TabsContent value="fantasy" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Fantasy Point Comparison</CardTitle>
                  <CardDescription>
                    Compare projected fantasy points with uncertainty ranges
                  </CardDescription>
                </CardHeader>
                <CardContent className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={getComparisonData('half_ppr', 'Fantasy Points')}
                      margin={{ top: 20, right: 30, left: 20, bottom: 40 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="name" 
                        tick={{ fontSize: 12 }}
                        angle={-45}
                        textAnchor="end"
                      />
                      <YAxis 
                        label={{ 
                          value: 'Half PPR Fantasy Points', 
                          angle: -90, 
                          position: 'insideLeft' 
                        }}
                      />
                      <Tooltip
                        formatter={(value, name) => {
                          if (name === 'value') return [Number(value).toFixed(1), 'Projection'];
                          if (name === 'rangeLow') return [Number(value).toFixed(1), 'Low Range'];
                          if (name === 'rangeHigh') return [Number(value).toFixed(1), 'High Range'];
                          return [value, name];
                        }}
                        labelFormatter={(label) => label}
                      />
                      <Legend />
                      <Bar 
                        dataKey="value" 
                        name="Projected Points" 
                        fill="#8884d8"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar 
                        dataKey="rangeLow" 
                        name="Low Range" 
                        fill="#ffc658"
                        radius={[4, 4, 0, 0]}
                        stackId="range"
                        style={{ opacity: 0.4 }}
                      />
                      <Bar 
                        dataKey="rangeHigh" 
                        name="High Range" 
                        fill="#82ca9d"
                        radius={[4, 4, 0, 0]}
                        stackId="range"
                        style={{ opacity: 0.4 }}
                      />
                    </BarChart>
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
                      outerRadius={90} 
                      width={730} 
                      height={250} 
                      data={getRadarData()}
                    >
                      <PolarGrid />
                      <PolarAngleAxis dataKey="name" />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} />
                      
                      {getLoadedPlayers().map((player, index) => (
                        <Radar
                          key={player.player_id}
                          name={player.name}
                          dataKey={player.position === 'QB' ? 'Pass Yards' : 'Rec Yards'}
                          stroke={getPlayerColor(index)}
                          fill={getPlayerColor(index)}
                          fillOpacity={0.6}
                        />
                      ))}
                      
                      <Legend />
                      <Tooltip />
                    </RadarChart>
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
                Select up to 4 players to compare side-by-side.
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