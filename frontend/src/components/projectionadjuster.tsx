import React, { useState, useEffect } from 'react';
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardContent, 
  CardDescription 
} from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  Legend, 
  ReferenceLine 
} from 'recharts';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

import { 
  PlayerService, 
  ProjectionService, 
  ScenarioService, 
  OverrideService 
} from '@/services/api';
import { 
  Player, 
  Projection, 
  Scenario, 
  StatOverride,
  QB_STATS,
  RB_STATS,
  WR_TE_STATS,
  STAT_FORMATS
} from '@/types/index';

// Helper function to calculate percent change
const percentChange = (newValue: number, oldValue: number): number => {
  if (oldValue === 0) return 0;
  return ((newValue - oldValue) / oldValue) * 100;
};

const ProjectionAdjuster: React.FC = () => {
  // State for players, projections, and scenarios
  const [players, setPlayers] = useState<Player[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<string>('');
  const [selectedTeam, setSelectedTeam] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);
  
  const [baseProjection, setBaseProjection] = useState<Projection | null>(null);
  const [currentProjection, setCurrentProjection] = useState<Projection | null>(null);
  const [overrides, setOverrides] = useState<StatOverride[]>([]);
  
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // State for adjustments
  const [adjustments, setAdjustments] = useState<Record<string, number>>({
    snap_share: 100,
    target_share: 100,
    rush_share: 100,
    td_rate: 100,
    pass_volume: 100,
    rush_volume: 100
  });

  // Fetch players on component mount
  useEffect(() => {
    const fetchPlayers = async () => {
      try {
        setIsLoading(true);
        const playersData = await PlayerService.getPlayers();
        setPlayers(playersData);
      } catch (err) {
        setError('Failed to fetch players');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    const fetchScenarios = async () => {
      try {
        setIsLoading(true);
        const scenariosData = await ScenarioService.getScenarios();
        setScenarios(scenariosData);
        
        // Set default scenario (baseline)
        const baselineScenario = scenariosData.find(s => s.is_baseline);
        if (baselineScenario) {
          setSelectedScenario(baselineScenario);
        } else if (scenariosData.length > 0) {
          setSelectedScenario(scenariosData[0]);
        }
      } catch (err) {
        setError('Failed to fetch scenarios');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPlayers();
    fetchScenarios();
  }, []);

  // Fetch player projections when player or scenario changes
  useEffect(() => {
    if (!selectedPlayer || !selectedScenario) return;
    
    const fetchProjections = async () => {
      try {
        setIsLoading(true);
        
        // Get player projections for the selected scenario
        const projections = await ProjectionService.getPlayerProjections(
          selectedPlayer.player_id,
          selectedScenario.scenario_id
        );
        
        if (projections.length > 0) {
          setCurrentProjection(projections[0]);
          
          // Also get base projection if different
          if (selectedScenario.is_baseline) {
            setBaseProjection(projections[0]);
          } else {
            // Get base projection from baseline scenario
            const baseScenario = scenarios.find(s => s.is_baseline);
            if (baseScenario) {
              const baseProjections = await ProjectionService.getPlayerProjections(
                selectedPlayer.player_id,
                baseScenario.scenario_id
              );
              
              if (baseProjections.length > 0) {
                setBaseProjection(baseProjections[0]);
              }
            }
          }
          
          // Get overrides if any
          if (projections[0].has_overrides) {
            const projectionOverrides = await OverrideService.getProjectionOverrides(
              projections[0].projection_id
            );
            setOverrides(projectionOverrides);
          } else {
            setOverrides([]);
          }
        } else {
          // No projection exists, try to create one
          if (selectedScenario.is_baseline) {
            const newProjection = await ProjectionService.createBaseProjection(
              selectedPlayer.player_id,
              2024 // Current season - could make this dynamic
            );
            
            setCurrentProjection(newProjection);
            setBaseProjection(newProjection);
          } else {
            setError('No projection available for this player in the selected scenario');
          }
        }
      } catch (err) {
        setError('Failed to fetch player projections');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchProjections();
  }, [selectedPlayer, selectedScenario, scenarios]);

  // Handle player selection
  const handlePlayerSelect = (playerId: string) => {
    const player = players.find(p => p.player_id === playerId);
    if (player) {
      setSelectedPlayer(player);
      
      // Reset adjustments
      setAdjustments({
        snap_share: 100,
        target_share: 100,
        rush_share: 100,
        td_rate: 100,
        pass_volume: 100,
        rush_volume: 100
      });
    }
  };

  // Handle scenario selection
  const handleScenarioSelect = (scenarioId: string) => {
    const scenario = scenarios.find(s => s.scenario_id === scenarioId);
    if (scenario) {
      setSelectedScenario(scenario);
    }
  };

  // Handle adjustment changes
  const handleAdjustment = async (metric: string, value: number) => {
    // Update adjustment in state
    setAdjustments(prev => ({
      ...prev,
      [metric]: value
    }));
    
    // Apply adjustment to projection if player and projection are selected
    if (selectedPlayer && currentProjection) {
      try {
        setIsLoading(true);
        
        // Convert adjustment percentage to factor (e.g., 110% -> 1.1)
        const adjustmentFactor = value / 100;
        
        // Update projection via API
        const updatedProjection = await ProjectionService.updateProjection(
          currentProjection.projection_id,
          { [metric]: adjustmentFactor }
        );
        
        // Update current projection in state
        setCurrentProjection(updatedProjection);
        
        // Fetch updated overrides
        const projectionOverrides = await OverrideService.getProjectionOverrides(
          currentProjection.projection_id
        );
        setOverrides(projectionOverrides);
      } catch (err) {
        setError('Failed to update projection');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    }
  };

  // Handle direct stat override
  const handleStatOverride = async (statName: string, value: number) => {
    if (!selectedPlayer || !currentProjection) return;
    
    try {
      setIsLoading(true);
      
      // Create override via API
      await OverrideService.createOverride(
        selectedPlayer.player_id,
        currentProjection.projection_id,
        statName,
        value,
        'Manual adjustment'
      );
      
      // Fetch updated projection
      const updatedProjections = await ProjectionService.getPlayerProjections(
        selectedPlayer.player_id,
        selectedScenario?.scenario_id
      );
      
      if (updatedProjections.length > 0) {
        setCurrentProjection(updatedProjections[0]);
      }
      
      // Fetch updated overrides
      const projectionOverrides = await OverrideService.getProjectionOverrides(
        currentProjection.projection_id
      );
      setOverrides(projectionOverrides);
    } catch (err) {
      setError('Failed to create override');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle removing an override
  const handleRemoveOverride = async (overrideId: string) => {
    try {
      setIsLoading(true);
      
      // Delete override via API
      await OverrideService.deleteOverride(overrideId);
      
      // Fetch updated projection
      if (selectedPlayer && selectedScenario) {
        const updatedProjections = await ProjectionService.getPlayerProjections(
          selectedPlayer.player_id,
          selectedScenario.scenario_id
        );
        
        if (updatedProjections.length > 0) {
          setCurrentProjection(updatedProjections[0]);
        }
        
        // Fetch updated overrides
        if (currentProjection) {
          const projectionOverrides = await OverrideService.getProjectionOverrides(
            currentProjection.projection_id
          );
          setOverrides(projectionOverrides);
        }
      }
    } catch (err) {
      setError('Failed to remove override');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter players based on position, team, and search query
  const filteredPlayers = players.filter(player => {
    // Filter by position if selected
    if (selectedPosition && player.position !== selectedPosition) {
      return false;
    }
    
    // Filter by team if selected
    if (selectedTeam && player.team !== selectedTeam) {
      return false;
    }
    
    // Filter by search query
    if (searchQuery && !player.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    
    return true;
  });

  // Get position-specific stats
  const getPositionStats = () => {
    if (!selectedPlayer) return {};
    
    switch (selectedPlayer.position) {
      case 'QB':
        return QB_STATS;
      case 'RB':
        return RB_STATS;
      case 'WR':
      case 'TE':
        return WR_TE_STATS;
      default:
        return {};
    }
  };

  // Generate comparison data for charts
  const generateComparisonData = () => {
    if (!baseProjection || !currentProjection) return [];
    
    const posStats = getPositionStats();
    const result = [];
    
    // Generate data for each stat category
    Object.entries(posStats).forEach(([category, stats]) => {
      stats.forEach(stat => {
        if (baseProjection[stat as keyof Projection] !== undefined && 
            currentProjection[stat as keyof Projection] !== undefined) {
          const baseValue = baseProjection[stat as keyof Projection] as number;
          const currentValue = currentProjection[stat as keyof Projection] as number;
          
          result.push({
            stat,
            category,
            statName: STAT_FORMATS[stat]?.label || stat,
            baseline: baseValue,
            current: currentValue,
            change: percentChange(currentValue, baseValue)
          });
        }
      });
    });
    
    return result;
  };

  // Get unique teams from players
  const teams = [...new Set(players.map(p => p.team))].sort();

  // Determine which adjustment sliders to show based on position
  const getPositionAdjustments = () => {
    if (!selectedPlayer) return [];
    
    // Common adjustments
    const common = [
      { key: 'snap_share', label: 'Snap Share %' }
    ];
    
    // Position-specific adjustments
    switch (selectedPlayer.position) {
      case 'QB':
        return [
          ...common,
          { key: 'pass_volume', label: 'Pass Volume %' },
          { key: 'td_rate', label: 'TD Rate %' }
        ];
      case 'RB':
        return [
          ...common,
          { key: 'rush_share', label: 'Rush Share %' },
          { key: 'target_share', label: 'Target Share %' }
        ];
      case 'WR':
      case 'TE':
        return [
          ...common,
          { key: 'target_share', label: 'Target Share %' },
          { key: 'td_rate', label: 'TD Rate %' }
        ];
      default:
        return common;
    }
  };

  return (
    <div className="grid grid-cols-12 gap-4 p-4">
      {/* Player Selection Panel */}
      <Card className="col-span-3">
        <CardHeader>
          <CardTitle>Player Selection</CardTitle>
          <CardDescription>
            Select a player to view and adjust projections
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Search and filters */}
            <div className="space-y-2">
              <Input
                placeholder="Search players..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <div className="grid grid-cols-2 gap-2">
                <Select
                  value={selectedPosition}
                  onValueChange={setSelectedPosition}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Position" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Positions</SelectItem>
                    <SelectItem value="QB">QB</SelectItem>
                    <SelectItem value="RB">RB</SelectItem>
                    <SelectItem value="WR">WR</SelectItem>
                    <SelectItem value="TE">TE</SelectItem>
                  </SelectContent>
                </Select>
                <Select
                  value={selectedTeam}
                  onValueChange={setSelectedTeam}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Team" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Teams</SelectItem>
                    {teams.map(team => (
                      <SelectItem key={team} value={team}>
                        {team}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Player list */}
            <div className="h-96 overflow-y-auto border rounded-md">
              <Table>
                <TableBody>
                  {filteredPlayers.map((player) => (
                    <TableRow
                      key={player.player_id}
                      className={
                        selectedPlayer?.player_id === player.player_id
                          ? "bg-muted cursor-pointer"
                          : "cursor-pointer hover:bg-muted/50"
                      }
                      onClick={() => handlePlayerSelect(player.player_id)}
                    >
                      <TableCell className="font-medium">
                        {player.name}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {player.position}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {player.team}
                      </TableCell>
                    </TableRow>
                  ))}
                  {filteredPlayers.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-muted-foreground">
                        No players found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
            
            {/* Scenario selection */}
            <div className="space-y-2">
              <Label>Projection Scenario</Label>
              <Select
                value={selectedScenario?.scenario_id || ''}
                onValueChange={handleScenarioSelect}
                disabled={!selectedPlayer}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select scenario" />
                </SelectTrigger>
                <SelectContent>
                  {scenarios.map(scenario => (
                    <SelectItem key={scenario.scenario_id} value={scenario.scenario_id}>
                      {scenario.name}
                      {scenario.is_baseline && " (Baseline)"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Adjustment Panel */}
      <Card className="col-span-5">
        <CardHeader>
          <CardTitle>
            {selectedPlayer ? (
              <>
                <span className="text-xl">{selectedPlayer.name}</span>
                <span className="text-muted-foreground ml-2">
                  {selectedPlayer.team} | {selectedPlayer.position}
                </span>
              </>
            ) : (
              "Projection Adjustments"
            )}
          </CardTitle>
          <CardDescription>
            {selectedPlayer
              ? "Adjust metrics to see impact on projections"
              : "Select a player to begin adjusting projections"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {selectedPlayer && currentProjection ? (
            <Tabs defaultValue="adjustments">
              <TabsList className="mb-4">
                <TabsTrigger value="adjustments">Quick Adjustments</TabsTrigger>
                <TabsTrigger value="stats">Detailed Stats</TabsTrigger>
                <TabsTrigger value="overrides">
                  Overrides
                  {overrides.length > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {overrides.length}
                    </Badge>
                  )}
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="adjustments">
                <div className="space-y-6">
                  {getPositionAdjustments().map(adjustment => (
                    <div key={adjustment.key}>
                      <label className="block mb-2">{adjustment.label}</label>
                      <Slider
                        value={[adjustments[adjustment.key]]}
                        min={50}
                        max={150}
                        step={1}
                        onValueChange={([value]) => handleAdjustment(adjustment.key, value)}
                      />
                      <div className="text-right text-sm text-gray-500">
                        {adjustments[adjustment.key]}% of baseline
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>
              
              <TabsContent value="stats">
                <div className="space-y-6">
                  {Object.entries(getPositionStats()).map(([category, stats]) => (
                    <div key={category}>
                      <h3 className="text-lg font-medium capitalize mb-2">{category}</h3>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Stat</TableHead>
                            <TableHead>Baseline</TableHead>
                            <TableHead>Current</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {stats.map(stat => {
                            if (!baseProjection || !currentProjection) return null;
                            if (baseProjection[stat as keyof Projection] === undefined) return null;
                            
                            const baseValue = baseProjection[stat as keyof Projection] as number;
                            const currentValue = currentProjection[stat as keyof Projection] as number;
                            const format = STAT_FORMATS[stat];
                            const displayLabel = format?.label || stat;
                            const formatValue = format?.formatter || ((val: number) => val.toString());
                            
                            // Check if this stat has an override
                            const override = overrides.find(o => o.stat_name === stat);
                            
                            return (
                              <TableRow key={stat}>
                                <TableCell>
                                  {displayLabel}
                                  {override && (
                                    <Badge variant="outline" className="ml-2">
                                      Override
                                    </Badge>
                                  )}
                                </TableCell>
                                <TableCell>{formatValue(baseValue)}</TableCell>
                                <TableCell
                                  className={
                                    override
                                      ? "font-medium text-primary"
                                      : format?.color?.(currentValue) || ""
                                  }
                                >
                                  {formatValue(currentValue)}
                                </TableCell>
                                <TableCell className="text-right">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      // Show a prompt to enter a new value
                                      const newValue = window.prompt(
                                        `Enter new value for ${displayLabel}:`,
                                        currentValue.toString()
                                      );
                                      
                                      if (newValue && !isNaN(parseFloat(newValue))) {
                                        handleStatOverride(
                                          stat,
                                          parseFloat(newValue)
                                        );
                                      }
                                    }}
                                  >
                                    Edit
                                  </Button>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  ))}
                </div>
              </TabsContent>
              
              <TabsContent value="overrides">
                {overrides.length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground">
                    No overrides have been applied to this projection.
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Stat</TableHead>
                        <TableHead>Original</TableHead>
                        <TableHead>Override</TableHead>
                        <TableHead>Change</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {overrides.map(override => {
                        const format = STAT_FORMATS[override.stat_name];
                        const displayLabel = format?.label || override.stat_name;
                        const formatValue = format?.formatter || ((val: number) => val.toString());
                        const pctChange = percentChange(
                          override.manual_value,
                          override.calculated_value
                        );
                        
                        return (
                          <TableRow key={override.override_id}>
                            <TableCell>{displayLabel}</TableCell>
                            <TableCell>{formatValue(override.calculated_value)}</TableCell>
                            <TableCell className="font-medium text-primary">
                              {formatValue(override.manual_value)}
                            </TableCell>
                            <TableCell>
                              <span className={pctChange >= 0 ? "text-green-500" : "text-red-500"}>
                                {pctChange >= 0 ? "+" : ""}
                                {pctChange.toFixed(1)}%
                              </span>
                            </TableCell>
                            <TableCell className="text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleRemoveOverride(override.override_id)}
                              >
                                Remove
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                )}
              </TabsContent>
            </Tabs>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              {isLoading ? (
                "Loading projection data..."
              ) : (
                "Select a player to view and adjust projections"
              )}
              {error && (
                <div className="text-red-500 mt-2">{error}</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Impact Analysis Panel */}
      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Impact Analysis</CardTitle>
          <CardDescription>
            {baseProjection && currentProjection
              ? `Half PPR: ${baseProjection.half_ppr.toFixed(1)} → ${currentProjection.half_ppr.toFixed(1)} (${percentChange(currentProjection.half_ppr, baseProjection.half_ppr).toFixed(1)}%)`
              : "Projection impact analysis"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {baseProjection && currentProjection ? (
            <>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={generateComparisonData()}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
                  >
                    <XAxis type="number" />
                    <YAxis 
                      dataKey="statName" 
                      type="category" 
                      width={80}
                    />
                    <Tooltip 
                      formatter={(value: number, name: string) => {
                        const stat = (name === 'baseline' || name === 'current') ? 
                          [value.toFixed(1), name === 'baseline' ? 'Baseline' : 'Current'] : 
                          [`${value.toFixed(1)}%`, 'Change'];
                        return stat;
                      }}
                    />
                    <Legend />
                    <Bar dataKey="baseline" fill="#8884d8" name="Baseline" />
                    <Bar dataKey="current" fill="#82ca9d" name="Current" />
                    <ReferenceLine x={0} stroke="#666" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <Separator className="my-4" />

              <div className="space-y-4">
                <h3 className="text-lg font-medium">Summary</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-muted p-3 rounded-md">
                    <div className="text-2xl font-bold">
                      {currentProjection.half_ppr.toFixed(1)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Half PPR Points
                    </div>
                  </div>
                  <div className="bg-muted p-3 rounded-md">
                    <div className="text-2xl font-bold text-primary">
                      {(
                        percentChange(
                          currentProjection.half_ppr,
                          baseProjection.half_ppr
                        ) >= 0 ? "+" : ""
                      )}
                      {percentChange(
                        currentProjection.half_ppr,
                        baseProjection.half_ppr
                      ).toFixed(1)}%
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Change from Baseline
                    </div>
                  </div>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Key Stat</TableHead>
                      <TableHead>Current</TableHead>
                      <TableHead>Change</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {generateComparisonData()
                      .filter(stat => {
                        // Filter to the most important stats based on position
                        const pos = selectedPlayer?.position;
                        if (pos === 'QB') {
                          return ['pass_yards', 'pass_td', 'interceptions'].includes(stat.stat);
                        } else if (pos === 'RB') {
                          return ['rush_yards', 'rush_td', 'receptions'].includes(stat.stat);
                        } else {
                          return ['targets', 'receptions', 'rec_yards', 'rec_td'].includes(stat.stat);
                        }
                      })
                      .map(stat => {
                        const format = STAT_FORMATS[stat.stat];
                        const formatValue = format?.formatter || ((val: number) => val.toString());
                        
                        return (
                          <TableRow key={stat.stat}>
                            <TableCell>{stat.statName}</TableCell>
                            <TableCell>{formatValue(stat.current)}</TableCell>
                            <TableCell>
                              <span className={stat.change >= 0 ? "text-green-500" : "text-red-500"}>
                                {stat.change >= 0 ? "+" : ""}
                                {stat.change.toFixed(1)}%
                              </span>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                  </TableBody>
                </Table>
              </div>
            </>
          ) : (
            <div className="text-center py-24 text-muted-foreground">
              {isLoading ? (
                "Loading impact analysis..."
              ) : (
                "Select a player to view projection impact"
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ProjectionAdjuster;