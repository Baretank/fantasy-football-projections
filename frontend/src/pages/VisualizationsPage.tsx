import React, { useState, useEffect } from 'react';
import { Logger } from '@/utils/logger';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
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
  PieChart, 
  Pie, 
  Cell,
  AreaChart,
  Area
} from 'recharts';
import ProjectionRangeChart from '@/components/visualization/ProjectionRangeChart';
import { 
  ArrowUpIcon,
  ArrowDownIcon,
  ArrowRightIcon,
  ChartBarIcon,
  UserCircleIcon,
  ExclamationCircleIcon,
  ChartPieIcon
} from '@heroicons/react/24/outline';
import { 
  PlayerService, 
  ProjectionService, 
  ScenarioService 
} from '@/services/api';
import { Player, Projection, Scenario } from '@/types/index';

const VisualizationsPage: React.FC = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [topProjections, setTopProjections] = useState<Record<string, any[]>>({});
  const [positionData, setPositionData] = useState<any[]>([]);
  const [teamData, setTeamData] = useState<any[]>([]);
  const [baselineScenario, setBaselineScenario] = useState<Scenario | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [players, setPlayers] = useState<Record<string, Player>>({});
  const [playerCount, setPlayerCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [projectionRangeData, setProjectionRangeData] = useState<any[]>([]);
  
  // Color configurations
  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088FE', '#00C49F'];
  const POSITION_COLORS: Record<string, string> = {
    'QB': '#8884d8',
    'RB': '#82ca9d',
    'WR': '#ffc658',
    'TE': '#ff8042'
  };
  
  // Fetch initial data
  useEffect(() => {
    async function fetchData() {
      try {
        setIsLoading(true);
        setError(null);
        
        // Fetch all scenarios
        const scenariosData = await ScenarioService.getScenarios();
        Logger.debug("All scenarios:", scenariosData);
        setScenarios(scenariosData);
        
        // Find baseline scenario
        const baseline = scenariosData.find(s => s.is_baseline) || scenariosData[0];
        Logger.debug("Selected baseline scenario:", baseline);
        setBaselineScenario(baseline);
        setSelectedScenario(baseline?.scenario_id || null);
        
        // Fetch player overview data
        const playersData = await PlayerService.getPlayersOverview();
        
        // Create player map for quick lookups
        const playerMap: Record<string, Player> = {};
        if (Array.isArray(playersData)) {
          playersData.forEach((player: Player) => {
            if (player && player.player_id) {
              playerMap[player.player_id] = player;
            }
          });
          setPlayerCount(playersData.length);
        } else {
          setPlayerCount(0);
        }
        setPlayers(playerMap);
        
        // Calculate position distribution
        const positionCounts: Record<string, number> = {};
        if (Array.isArray(playersData)) {
          playersData.forEach((player: Player) => {
            if (player && player.position) {
              positionCounts[player.position] = (positionCounts[player.position] || 0) + 1;
            }
          });
        }
        
        setPositionData(
          Object.entries(positionCounts).map(([position, count], index) => ({
            name: position || 'Unknown',
            value: count,
            color: POSITION_COLORS[position] || COLORS[index % COLORS.length]
          }))
        );
        
        // Calculate team distribution
        const teamCounts: Record<string, number> = {};
        if (Array.isArray(playersData)) {
          playersData.forEach((player: Player) => {
            if (player && player.team) {
              teamCounts[player.team] = (teamCounts[player.team] || 0) + 1;
            }
          });
        }
        
        // Sort teams by player count
        setTeamData(
          Object.entries(teamCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .map(([team, count], index) => ({
              name: team || 'Unknown',
              players: count
            }))
        );
        
        // Fetch projection data if we have a baseline
        if (baseline) {
          const positionPromises: Record<string, Promise<any[]>> = {};
          
          // Fetch top projections for each position
          for (const position of ['QB', 'RB', 'WR', 'TE']) {
            positionPromises[position] = ScenarioService.getScenarioProjections(
              baseline.scenario_id,
              position
            );
          }
          
          // Wait for all position data to load
          const positionResults: Record<string, any[]> = {};
          
          for (const [position, promise] of Object.entries(positionPromises)) {
            try {
              const projections = await promise;
              Logger.debug(`Received ${position} projections:`, projections);
              
              // Check that projections is an array and has content
              if (!Array.isArray(projections) || projections.length === 0) {
                Logger.info(`No ${position} projections found.`);
                positionResults[position] = [];
                continue;
              }
              
              // Sort by half PPR points
              const sorted = projections
                .filter(p => p && typeof p === 'object' && p.half_ppr !== undefined && p.half_ppr !== null)
                .sort((a, b) => (b.half_ppr || 0) - (a.half_ppr || 0))
                .slice(0, 10);
              
              Logger.debug(`Sorted ${position} projections:`, sorted);
              positionResults[position] = sorted;
              
              // For top players, fetch projection ranges
              if ((position === 'QB' || position === 'RB') && Array.isArray(sorted) && sorted.length > 0) {
                const topPlayers = sorted.slice(0, 5);
                
                for (const projection of topPlayers) {
                  if (!projection || !projection.projection_id) continue;
                  
                  try {
                    const range = await ProjectionService.getProjectionRange(
                      projection.projection_id,
                      0.80
                    );
                    
                    // Add to ranges data
                    if (range && projection.player_id && playerMap[projection.player_id]) {
                      const halfPpr = projection.half_ppr || 0;
                      
                      setProjectionRangeData(prev => [
                        ...(Array.isArray(prev) ? prev : []),
                        {
                          name: playerMap[projection.player_id]?.name || 'Unknown',
                          position,
                          team: playerMap[projection.player_id]?.team || 'UNK',
                          value: halfPpr,
                          range: {
                            low: range.low?.half_ppr || halfPpr * 0.8,
                            high: range.high?.half_ppr || halfPpr * 1.2
                          }
                        }
                      ]);
                    }
                  } catch (rangeError) {
                    Logger.error(`Error fetching range for ${projection.projection_id}:`, rangeError);
                  }
                }
              }
            } catch (posError) {
              Logger.error(`Error fetching ${position} projections:`, posError);
              positionResults[position] = [];
            }
          }
          
          Logger.debug("Final position results before setting state:", positionResults);
          setTopProjections(positionResults);
          
          // Diagnostic for empty position results
          for (const [position, projections] of Object.entries(positionResults)) {
            if (!projections || projections.length === 0) {
              Logger.warn(`No projections found for position: ${position}`);
            }
          }
        }
      } catch (err) {
        Logger.error("Error fetching dashboard data:", err);
        setError("Failed to load dashboard data. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchData();
  }, []);
  
  // Handle scenario change
  const handleScenarioChange = async (scenarioId: string) => {
    setSelectedScenario(scenarioId);
    setIsLoading(true);
    setError(null);
    setProjectionRangeData([]);
    
    try {
      // Find the selected scenario object
      const selectedScen = scenarios.find(s => s.scenario_id === scenarioId);
      
      if (selectedScen) {
        const positionPromises: Record<string, Promise<any[]>> = {};
        
        // Fetch top projections for each position
        for (const position of ['QB', 'RB', 'WR', 'TE']) {
          positionPromises[position] = ScenarioService.getScenarioProjections(
            scenarioId,
            position
          );
        }
        
        // Wait for all position data to load
        const positionResults: Record<string, any[]> = {};
        
        for (const [position, promise] of Object.entries(positionPromises)) {
          try {
            const projections = await promise;
            
            // Check that projections is an array and has content
            if (!Array.isArray(projections) || projections.length === 0) {
              positionResults[position] = [];
              continue;
            }
            
            // Sort by half PPR points
            const sorted = projections
              .filter(p => p && typeof p === 'object' && p.half_ppr !== undefined && p.half_ppr !== null)
              .sort((a, b) => (b.half_ppr || 0) - (a.half_ppr || 0))
              .slice(0, 10);
            
            positionResults[position] = sorted;
            
            // For top players, fetch projection ranges
            if ((position === 'QB' || position === 'RB') && Array.isArray(sorted) && sorted.length > 0) {
              const topPlayers = sorted.slice(0, 5);
              
              for (const projection of topPlayers) {
                if (!projection || !projection.projection_id) continue;
                
                try {
                  const range = await ProjectionService.getProjectionRange(
                    projection.projection_id,
                    0.80
                  );
                  
                  // Add to ranges data
                  if (range && projection.player_id && players[projection.player_id]) {
                    const halfPpr = projection.half_ppr || 0;
                    
                    setProjectionRangeData(prev => [
                      ...(Array.isArray(prev) ? prev : []),
                      {
                        name: players[projection.player_id]?.name || 'Unknown',
                        position,
                        team: players[projection.player_id]?.team || 'UNK',
                        value: halfPpr,
                        range: {
                          low: range.low?.half_ppr || halfPpr * 0.8,
                          high: range.high?.half_ppr || halfPpr * 1.2
                        }
                      }
                    ]);
                  }
                } catch (rangeError) {
                  Logger.error(`Error fetching range for ${projection.projection_id}:`, rangeError);
                }
              }
            }
          } catch (posError) {
            Logger.error(`Error fetching ${position} projections:`, posError);
            positionResults[position] = [];
          }
        }
        
        setTopProjections(positionResults);
      }
    } catch (err) {
      Logger.error("Error changing scenario:", err);
      setError("Failed to change scenario. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };
  
  // Helper to get player info
  const getPlayerInfo = (playerId: string) => {
    if (!playerId || typeof playerId !== 'string') {
      return {
        name: 'Unknown Player',
        team: 'UNK',
        position: '?'
      };
    }
    
    const player = players[playerId];
    return {
      name: player?.name || 'Unknown Player',
      team: player?.team || 'UNK',
      position: player?.position || '?'
    };
  };
  
  // Calculate fantasy points distribution
  const getFantasyDistribution = () => {
    const pointRanges = [
      { name: '0-50', min: 0, max: 50, count: 0 },
      { name: '50-100', min: 50, max: 100, count: 0 },
      { name: '100-150', min: 100, max: 150, count: 0 },
      { name: '150-200', min: 150, max: 200, count: 0 },
      { name: '200-250', min: 200, max: 250, count: 0 },
      { name: '250-300', min: 250, max: 300, count: 0 },
      { name: '300+', min: 300, max: Infinity, count: 0 }
    ];
    
    // Count projections in each range
    if (topProjections && typeof topProjections === 'object') {
      Object.values(topProjections).forEach(projections => {
        if (Array.isArray(projections)) {
          projections.forEach(proj => {
            if (proj && typeof proj === 'object') {
              const points = proj.half_ppr || 0;
              const range = pointRanges.find(r => points >= r.min && points < r.max);
              if (range) range.count++;
            }
          });
        }
      });
    }
    
    return pointRanges;
  };
  
  // Prepare summary stats
  const getSummaryStats = () => {
    const stats = {
      totalPlayers: playerCount,
      totalScenarios: Array.isArray(scenarios) ? scenarios.length : 0,
      topQB: { name: 'N/A', value: 0, playerId: '' },
      topRB: { name: 'N/A', value: 0, playerId: '' },
      topWR: { name: 'N/A', value: 0, playerId: '' },
      topTE: { name: 'N/A', value: 0, playerId: '' }
    };
    
    // Find top players by position
    if (topProjections?.QB && Array.isArray(topProjections.QB) && topProjections.QB.length > 0) {
      const topQB = topProjections.QB[0];
      if (topQB && topQB.player_id) {
        const { name } = getPlayerInfo(topQB.player_id);
        stats.topQB = { 
          name, 
          value: topQB.half_ppr || 0, 
          playerId: topQB.player_id 
        };
      }
    }
    
    if (topProjections?.RB && Array.isArray(topProjections.RB) && topProjections.RB.length > 0) {
      const topRB = topProjections.RB[0];
      if (topRB && topRB.player_id) {
        const { name } = getPlayerInfo(topRB.player_id);
        stats.topRB = { 
          name, 
          value: topRB.half_ppr || 0, 
          playerId: topRB.player_id 
        };
      }
    }
    
    if (topProjections?.WR && Array.isArray(topProjections.WR) && topProjections.WR.length > 0) {
      const topWR = topProjections.WR[0];
      if (topWR && topWR.player_id) {
        const { name } = getPlayerInfo(topWR.player_id);
        stats.topWR = { 
          name, 
          value: topWR.half_ppr || 0, 
          playerId: topWR.player_id 
        };
      }
    }
    
    if (topProjections?.TE && Array.isArray(topProjections.TE) && topProjections.TE.length > 0) {
      const topTE = topProjections.TE[0];
      if (topTE && topTE.player_id) {
        const { name } = getPlayerInfo(topTE.player_id);
        stats.topTE = { 
          name, 
          value: topTE.half_ppr || 0, 
          playerId: topTE.player_id 
        };
      }
    }
    
    return stats;
  };
  
  const summaryStats = getSummaryStats();
  
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Visualizations</h1>
          <p className="text-muted-foreground">
            Visual analytics for fantasy football projections
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          <Select value={selectedScenario || ''} onValueChange={handleScenarioChange}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select Scenario" />
            </SelectTrigger>
            <SelectContent>
              {scenarios.map(scenario => (
                <SelectItem key={scenario.scenario_id} value={scenario.scenario_id}>
                  {scenario.name} {scenario.is_baseline ? '(Baseline)' : ''}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center h-96">
          <div className="text-center space-y-4">
            <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto"></div>
            <p className="text-muted-foreground">Loading visualization data...</p>
          </div>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-96">
          <div className="text-center space-y-4">
            <ExclamationCircleIcon className="h-16 w-16 text-destructive mx-auto" />
            <p className="text-xl font-medium text-destructive">{error}</p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Players
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{summaryStats.totalPlayers}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  In projection database
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Scenarios
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{summaryStats.totalScenarios}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Projection scenarios
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Top QB
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {summaryStats.topQB.name}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {summaryStats.topQB.value.toFixed(1)} fantasy points
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Top RB
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {summaryStats.topRB.name}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {summaryStats.topRB.value.toFixed(1)} fantasy points
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tabs for different visualizations */}
          <Tabs defaultValue="distribution" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="distribution">Position Distribution</TabsTrigger>
              <TabsTrigger value="points">Fantasy Points</TabsTrigger>
              <TabsTrigger value="projection-ranges">Projection Ranges</TabsTrigger>
            </TabsList>
            
            {/* Position Distribution */}
            <TabsContent value="distribution" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Player Distribution by Position</CardTitle>
                    <CardDescription>
                      Breakdown of roster by position
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={positionData}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        >
                          {positionData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => [`${value} players`, 'Count']} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle>Player Distribution by Team</CardTitle>
                    <CardDescription>
                      Top 10 teams by player count
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={teamData}
                        layout="vertical"
                        margin={{ top: 5, right: 30, left: 30, bottom: 5 }}
                      >
                        <XAxis type="number" />
                        <YAxis type="category" dataKey="name" />
                        <CartesianGrid strokeDasharray="3 3" />
                        <Tooltip formatter={(value) => [`${value} players`, 'Count']} />
                        <Bar dataKey="players" fill="#8884d8" />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            
            {/* Fantasy Points Distribution */}
            <TabsContent value="points" className="space-y-6">
              <div className="grid grid-cols-1 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Fantasy Point Distribution</CardTitle>
                    <CardDescription>
                      Fantasy point comparison across top players
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={Object.entries(topProjections).flatMap(([position, projections]) =>
                          projections.slice(0, 3).map(proj => ({
                            name: getPlayerInfo(proj.player_id).name,
                            position,
                            team: getPlayerInfo(proj.player_id).team,
                            points: proj.half_ppr
                          }))
                        )}
                        margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="name" 
                          tick={{ fontSize: 12 }}
                          interval={0}
                          angle={-45}
                          textAnchor="end"
                        />
                        <YAxis label={{ value: 'Half PPR Points', angle: -90, position: 'insideLeft' }} />
                        <Tooltip
                          formatter={(value, name, props) => {
                            if (name === 'points') {
                              return [`${Number(value).toFixed(1)} pts`, 'Fantasy Points'];
                            }
                            return [value, name];
                          }}
                          labelFormatter={(label) => label}
                          content={({ active, payload, label }) => {
                            if (active && payload && payload.length) {
                              const data = payload[0].payload;
                              return (
                                <div className="bg-background p-2 border shadow-sm rounded-md">
                                  <p className="font-medium">{data.name}</p>
                                  <p className="text-xs text-muted-foreground">{data.team} - {data.position}</p>
                                  <p className="text-primary font-medium">{data.points.toFixed(1)} pts</p>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Legend />
                        <Bar 
                          dataKey="points" 
                          name="Fantasy Points"
                          fill={(data) => {
                            switch (data.position) {
                              case 'QB': return '#8884d8';
                              case 'RB': return '#82ca9d';
                              case 'WR': return '#ffc658';
                              case 'TE': return '#ff8042';
                              default: return '#8884d8';
                            }
                          }}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle>Fantasy Point Range Distribution</CardTitle>
                    <CardDescription>
                      Distribution of fantasy points across ranges
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={getFantasyDistribution()}
                        margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip
                          formatter={(value) => [`${value} players`, 'Count']}
                        />
                        <Bar 
                          dataKey="count" 
                          name="Fantasy Point Distribution" 
                          fill="#8884d8" 
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            
            {/* Projection Ranges */}
            <TabsContent value="projection-ranges" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Projection Ranges</CardTitle>
                  <CardDescription>
                    Visualize projection ranges with 80% confidence intervals
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[400px]">
                    {projectionRangeData.length > 0 ? (
                      <ProjectionRangeChart 
                        data={projectionRangeData}
                        yAxisLabel="Fantasy Points (Half PPR)"
                        height="100%"
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-muted-foreground">
                        No projection range data available for the selected scenario
                      </div>
                    )}
                  </div>
                </CardContent>
                <CardFooter className="flex justify-between">
                  <p className="text-sm text-muted-foreground">
                    Showing top players with uncertainty ranges
                  </p>
                  <Button variant="outline" size="sm" asChild>
                    <a href="/compare">
                      <ArrowRightIcon className="h-4 w-4 mr-2" />
                      Compare Players
                    </a>
                  </Button>
                </CardFooter>
              </Card>
            </TabsContent>
          </Tabs>
          
          {/* Top Players by Position */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {['QB', 'RB', 'WR', 'TE'].map(position => (
              <Card key={position}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Top {position}s</CardTitle>
                  <CardDescription>
                    Highest projected {position}s
                  </CardDescription>
                </CardHeader>
                <CardContent className="px-2">
                  {isLoading ? (
                    <div className="text-center py-4 text-muted-foreground">Loading...</div>
                  ) : error ? (
                    <div className="text-center py-4 text-destructive">Error loading data</div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Player</TableHead>
                          <TableHead>Team</TableHead>
                          <TableHead className="text-right">Points</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(topProjections[position] || []).slice(0, 5).map(projection => {
                          const { name, team } = getPlayerInfo(projection.player_id);
                          return (
                            <TableRow key={projection.projection_id}>
                              <TableCell className="py-1 font-medium">
                                {name}
                              </TableCell>
                              <TableCell className="py-1">
                                {team}
                              </TableCell>
                              <TableCell className="py-1 text-right">
                                {projection.half_ppr.toFixed(1)}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                        {(!topProjections[position] || topProjections[position].length === 0) && (
                          <TableRow>
                            <TableCell colSpan={3} className="text-center text-muted-foreground py-4">
                              No projections available
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
                <CardFooter>
                  <Button variant="ghost" size="sm" className="w-full" asChild>
                    <a href="/players">
                      View All {position}s
                    </a>
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default VisualizationsPage;