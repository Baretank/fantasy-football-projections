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
import ProjectionRangeChart from './visualization/ProjectionRangeChart';
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
import { Logger } from '@/utils/logger';
import { getCurrentSeasonYear, percentChange } from '@/utils/calculatioms';

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

// Use utility function from calculatioms.ts - adjusted to return percentage

const ProjectionAdjuster: React.FC = () => {
  // State for players, projections, and scenarios
  const [players, setPlayers] = useState<Player[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<string>('all_positions');
  const [selectedTeam, setSelectedTeam] = useState<string>('all_teams');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);
  
  const [baseProjection, setBaseProjection] = useState<Projection | null>(null);
  const [currentProjection, setCurrentProjection] = useState<Projection | null>(null);
  const [overrides, setOverrides] = useState<StatOverride[]>([]);
  
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // States for projection variance and range visualization
  const [showVariance, setShowVariance] = useState<boolean>(false);
  const [confidenceLevel, setConfidenceLevel] = useState<number>(0.8);
  const [rangeChartData, setRangeChartData] = useState<any[]>([]);
  
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
        const response = await PlayerService.getPlayers();
        // Check if response has players property and it's an array
        if (response && response.players && Array.isArray(response.players)) {
          setPlayers(response.players);
        } else if (Array.isArray(response)) {
          // Handle case where API might return an array directly
          setPlayers(response);
        } else {
          // Initialize as empty array if response format is unexpected
          Logger.error('Unexpected API response format:', response);
          setPlayers([]);
        }
      } catch (err) {
        setError('Failed to fetch players');
        Logger.error('Failed to fetch players', err);
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
        Logger.error('Failed to fetch scenarios', err);
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
        
        if (Array.isArray(projections) && projections.length > 0) {
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
              
              if (Array.isArray(baseProjections) && baseProjections.length > 0) {
                setBaseProjection(baseProjections[0]);
              }
            }
          }
          
          // Get overrides if any
          if (projections[0] && projections[0].has_overrides) {
            try {
              const projectionOverrides = await OverrideService.getProjectionOverrides(
                projections[0].projection_id
              );
              
              // Ensure overrides is an array before setting it
              if (Array.isArray(projectionOverrides)) {
                setOverrides(projectionOverrides);
              } else {
                Logger.error('Expected array of overrides but got:', projectionOverrides);
                setOverrides([]);
              }
            } catch (overrideErr) {
              Logger.error('Error fetching overrides:', overrideErr);
              setOverrides([]);
            }
          } else {
            setOverrides([]);
          }
          
          // If showing variance, load the range data
          if (showVariance) {
            fetchRangeData(projections[0]);
          }
        } else {
          // No projection exists, try to create one
          if (selectedScenario.is_baseline) {
            // Use the getCurrentSeasonYear function already imported at the top
            const seasonYear = getCurrentSeasonYear();
              
            const newProjection = await ProjectionService.createBaseProjection(
              selectedPlayer.player_id,
              seasonYear // Dynamic season year
            );
            
            setCurrentProjection(newProjection);
            setBaseProjection(newProjection);
          } else {
            setError('No projection available for this player in the selected scenario');
          }
        }
      } catch (err) {
        setError('Failed to fetch player projections');
        Logger.error('Failed to fetch player projections', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchProjections();
  }, [selectedPlayer, selectedScenario, scenarios]);
  
  // Fetch range data when showVariance changes or confidence level changes
  useEffect(() => {
    if (showVariance && currentProjection) {
      fetchRangeData(currentProjection);
    }
  }, [showVariance, confidenceLevel, currentProjection?.projection_id]);
  
  // Function to fetch range data for the projection variance chart
  const fetchRangeData = async (projection: Projection) => {
    if (!projection || !selectedPlayer) return;
    
    try {
      setIsLoading(true);
      const rangeData = await ProjectionService.getProjectionVariance(
        projection.projection_id,
        true // Use historical data
      );
      
      if (rangeData && rangeData.variance) {
        // Format data for the chart component
        const varianceData = rangeData.variance;
        const positionStats = getPositionStats();
        const allStats = Object.values(positionStats).flat();
        
        // Calculate confidence interval based on confidence level
        // Using Z-score approximation (e.g., 90% confidence = 1.645 standard deviations)
        const zScores: Record<number, number> = {
          0.7: 1.04, // 70% confidence
          0.8: 1.28, // 80% confidence
          0.9: 1.645, // 90% confidence
          0.95: 1.96 // 95% confidence
        };
        
        const zScore = zScores[confidenceLevel] || 1.28; // Default to 80% if not found
        
        // Format for the chart component - include half_ppr and key stats
        const chartData = [
          {
            name: "Half PPR", 
            position: selectedPlayer.position,
            team: selectedPlayer.team,
            value: projection.half_ppr,
            range: {
              low: Math.max(0, projection.half_ppr - (zScore * (varianceData.half_ppr?.stddev || 0))),
              high: projection.half_ppr + (zScore * (varianceData.half_ppr?.stddev || 0))
            }
          },
          ...Object.keys(varianceData)
            .filter(key => 
              key !== 'half_ppr' && 
              allStats.includes(key) &&
              projection[key as keyof Projection] !== undefined &&
              STAT_FORMATS[key] // Only include stats with defined formats
            )
            .slice(0, 5) // Limit to top 5 stats for better visualization
            .map(key => {
              const value = projection[key as keyof Projection] as number;
              const stddev = varianceData[key]?.stddev || 0;
              
              return {
                name: STAT_FORMATS[key]?.label || key,
                position: selectedPlayer.position,
                team: selectedPlayer.team,
                value: value,
                range: {
                  low: Math.max(0, value - (zScore * stddev)),
                  high: value + (zScore * stddev)
                }
              };
            })
        ];
        
        setRangeChartData(chartData);
      }
    } catch (error) {
      Logger.error("Error fetching variance data:", error);
      setError('Failed to load projection variance data');
    } finally {
      setIsLoading(false);
    }
  };

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
      
      // Reset variance data
      setRangeChartData([]);
      setShowVariance(false);
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
        Logger.error('Failed to update projection', err);
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
      Logger.error('Failed to create override', err);
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
      Logger.error('Failed to remove override', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter players based on position, team, and search query
  const filteredPlayers = Array.isArray(players) 
    ? players.filter(player => {
        // Make sure player is a valid object with required properties
        if (!player || typeof player !== 'object' || !player.name || !player.position || !player.team) {
          Logger.warn('Invalid player object:', player);
          return false;
        }
        
        // Filter by position if selected
        if (selectedPosition !== 'all_positions' && player.position !== selectedPosition) {
          return false;
        }
        
        // Filter by team if selected
        if (selectedTeam !== 'all_teams' && player.team !== selectedTeam) {
          return false;
        }
        
        // Filter by search query
        if (searchQuery && !player.name.toLowerCase().includes(searchQuery.toLowerCase())) {
          return false;
        }
        
        return true;
      }) 
    : [];

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
          const baseValue = baseProjection[stat as keyof Projection] as number || 0;
          const currentValue = currentProjection[stat as keyof Projection] as number || 0;
          
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
  
  // Generate range chart data for projection variance
  const generateRangeChartData = async () => {
    if (!currentProjection?.projection_id || !selectedPlayer) return [];
    
    try {
      // Get variance data from the API
      const rangeData = await ProjectionService.getProjectionVariance(
        currentProjection.projection_id,
        true // Use historical data
      );
      
      if (!rangeData || !rangeData.variance) return [];
      
      // Calculate confidence interval based on confidence level
      // Using Z-score approximation (e.g., 90% confidence = 1.645 standard deviations)
      const zScores: Record<number, number> = {
        0.7: 1.04, // 70% confidence
        0.8: 1.28, // 80% confidence
        0.9: 1.645, // 90% confidence
        0.95: 1.96 // 95% confidence
      };
      
      const zScore = zScores[confidenceLevel] || 1.28; // Default to 80% if not found
      const varianceData = rangeData.variance;
      
      // Format for the chart component
      return [
        {
          name: "Half PPR", 
          position: selectedPlayer.position,
          team: selectedPlayer.team,
          value: currentProjection.half_ppr,
          range: {
            low: Math.max(0, currentProjection.half_ppr - (zScore * (varianceData.half_ppr?.stddev || 0))),
            high: currentProjection.half_ppr + (zScore * (varianceData.half_ppr?.stddev || 0))
          }
        },
        ...Object.keys(varianceData)
          .filter(key => 
            key !== 'half_ppr' && 
            currentProjection[key as keyof Projection] !== undefined &&
            STAT_FORMATS[key] // Only include stats with defined formats
          )
          .slice(0, 5) // Limit to top 5 stats for better visualization
          .map(key => {
            const value = currentProjection[key as keyof Projection] as number;
            const stddev = varianceData[key]?.stddev || 0;
            
            return {
              name: STAT_FORMATS[key]?.label || key,
              position: selectedPlayer.position,
              team: selectedPlayer.team,
              value: value,
              range: {
                low: Math.max(0, value - (zScore * stddev)),
                high: value + (zScore * stddev)
              }
            };
          })
      ];
    } catch (error) {
      Logger.error("Error generating range chart data:", error);
      return [];
    }
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
                    <SelectItem value="all_positions">All Positions</SelectItem>
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
                    <SelectItem value="all_teams">All Teams</SelectItem>
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
                            
                            const baseValue = baseProjection[stat as keyof Projection] as number || 0;
                            const currentValue = currentProjection[stat as keyof Projection] as number || 0;
                            const format = STAT_FORMATS[stat];
                            const displayLabel = format?.label || stat;
                            const formatValue = format?.formatter || ((val: number) => {
                              return val !== null && val !== undefined ? val.toString() : '0';
                            });
                            
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
                                      : (currentValue !== null && currentValue !== undefined) ? (format?.color?.(currentValue) || "") : ""
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
                {!overrides || !Array.isArray(overrides) || overrides.length === 0 ? (
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
                        if (!override || typeof override !== 'object') {
                          return null; // Skip invalid overrides
                        }
                        
                        const format = override.stat_name ? STAT_FORMATS[override.stat_name] : null;
                        const displayLabel = format?.label || override.stat_name || 'Unknown';
                        const formatValue = format?.formatter || ((val: number) => {
                          return val !== null && val !== undefined ? val.toString() : "0";
                        });
                        const pctChange = percentChange(
                          override.manual_value || 0,
                          override.calculated_value || 0
                        );
                        
                        return (
                          <TableRow key={override.override_id || Math.random().toString()}>
                            <TableCell>{displayLabel}</TableCell>
                            <TableCell>{formatValue(override.calculated_value || 0)}</TableCell>
                            <TableCell className="font-medium text-primary">
                              {formatValue(override.manual_value || 0)}
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
                                onClick={() => override.override_id && handleRemoveOverride(override.override_id)}
                                disabled={!override.override_id}
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
          <CardTitle className="flex justify-between">
            <span>Impact Analysis</span>
            <div className="flex items-center space-x-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowVariance(!showVariance)}
                disabled={!currentProjection}
              >
                {showVariance ? "Hide Variance" : "Show Variance"}
              </Button>
              {showVariance && (
                <Select
                  value={confidenceLevel.toString()}
                  onValueChange={(value) => setConfidenceLevel(parseFloat(value))}
                >
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="Confidence" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0.7">70% Confidence</SelectItem>
                    <SelectItem value="0.8">80% Confidence</SelectItem>
                    <SelectItem value="0.9">90% Confidence</SelectItem>
                    <SelectItem value="0.95">95% Confidence</SelectItem>
                  </SelectContent>
                </Select>
              )}
            </div>
          </CardTitle>
          <CardDescription>
            {baseProjection && currentProjection
              ? `Half PPR: ${(baseProjection.half_ppr || 0).toFixed(1)} → ${(currentProjection.half_ppr || 0).toFixed(1)} (${percentChange(currentProjection.half_ppr || 0, baseProjection.half_ppr || 0).toFixed(1)}%)`
              : "Projection impact analysis"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {baseProjection && currentProjection ? (
            <>
              <Tabs defaultValue={showVariance ? "variance" : "comparison"}>
                <TabsList className="mb-4 grid w-full grid-cols-2">
                  <TabsTrigger value="comparison">Comparison</TabsTrigger>
                  <TabsTrigger value="variance" disabled={!showVariance}>Variance</TabsTrigger>
                </TabsList>
                
                <TabsContent value="comparison">
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
                          {(currentProjection.half_ppr || 0).toFixed(1)}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Half PPR Points
                        </div>
                      </div>
                      <div className="bg-muted p-3 rounded-md">
                        <div className="text-2xl font-bold text-primary">
                          {(
                            percentChange(
                              currentProjection.half_ppr || 0,
                              baseProjection.half_ppr || 0
                            ) >= 0 ? "+" : ""
                          )}
                          {percentChange(
                            currentProjection.half_ppr || 0,
                            baseProjection.half_ppr || 0
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
                            const formatValue = format?.formatter || ((val: number) => {
                              return val !== null && val !== undefined ? val.toString() : '0';
                            });
                            
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
                </TabsContent>
                
                <TabsContent value="variance">
                  {showVariance && (
                    <div className="space-y-4">
                      <Card>
                        <CardHeader className="py-3">
                          <CardTitle className="text-lg">Projection Confidence Range</CardTitle>
                          <CardDescription>
                            {(confidenceLevel * 100).toFixed(0)}% confidence interval
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          {rangeChartData.length > 0 ? (
                            <div className="h-64">
                              <ProjectionRangeChart 
                                data={rangeChartData} 
                                title="Projection Range"
                                yAxisLabel="Value"
                                height={250}
                                showAverage={false}
                              />
                            </div>
                          ) : (
                            <div className="flex justify-center items-center h-60">
                              Loading variance data...
                            </div>
                          )}
                        </CardContent>
                      </Card>
                      
                      <div className="text-sm text-muted-foreground">
                        <p>
                          The chart above shows the projection range for {selectedPlayer?.name} at {(confidenceLevel * 100).toFixed(0)}% confidence level. 
                          This range is calculated using historical variance data for similar players.
                        </p>
                        <p className="mt-2">
                          The central point represents the current projection, while the error bars show the possible 
                          range of outcomes based on historical performance.
                        </p>
                      </div>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
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