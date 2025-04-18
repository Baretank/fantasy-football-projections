import React, { useState, useEffect } from 'react';
import { Logger } from '@/utils/logger';
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/components/ui/use-toast';
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
import { Link } from 'react-router-dom';
import { 
  ArrowUpIcon,
  ArrowDownIcon,
  ArrowRightIcon,
  ChartBarIcon,
  UserCircleIcon,
  ExclamationCircleIcon,
  ChartPieIcon
} from '@heroicons/react/24/outline';
// ArrowsRightLeftIcon is not needed anymore, since we've replaced it with ArrowRightIcon
import { 
  PlayerService, 
  ProjectionService, 
  ScenarioService 
} from '@/services/api';
import { Player, Projection, Scenario } from '@/types/index';

const DashboardPage: React.FC = () => {
  const { toast } = useToast();
  // State
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [topProjections, setTopProjections] = useState<Record<string, any[]>>({});
  const [positionData, setPositionData] = useState<any[]>([]);
  const [teamData, setTeamData] = useState<any[]>([]);
  const [baselineScenario, setBaselineScenario] = useState<Scenario | null>(null);
  const [players, setPlayers] = useState<Record<string, Player>>({});
  const [playerCount, setPlayerCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [projectionRangeData, setProjectionRangeData] = useState<any[]>([]);
  const [isRunningProjections, setIsRunningProjections] = useState<boolean>(false);
  
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
  
  // Function to run projections for all players
  const runBaselineProjections = async () => {
    if (!baselineScenario) return;
    
    try {
      setIsRunningProjections(true);
      setError(null);
      
      Logger.info("Starting to generate baseline projections");
      
      // Get all players first
      const playersData = await PlayerService.getPlayersOverview();
      if (!Array.isArray(playersData) || playersData.length === 0) {
        throw new Error("No players found to generate projections");
      }
      
      Logger.info(`Found ${playersData.length} players for projection generation`);
      
      // Create projections for each player
      let successCount = 0;
      let errorCount = 0;
      // Use 2023 as season year since that's what the API expects (>= 2023 according to API schema)
      const seasonYear = 2023;
      
      // Show additional info to user
      toast({
        title: "Generating Projections",
        description: "Creating projections for all players. This may take a moment...",
        variant: "default",
      });
      
      // Process players in batches of 5 to avoid overwhelming the API
      const batchSize = 5;
      for (let i = 0; i < playersData.length; i += batchSize) {
        const batch = playersData.slice(i, i + batchSize);
        
        // Process this batch in parallel
        const batchPromises = batch.map(async (player) => {
          if (!player || !player.player_id) return false;
          
          try {
            // Check if projection already exists
            const existingProjections = await ProjectionService.getPlayerProjections(
              player.player_id,
              baselineScenario.scenario_id,
              seasonYear
            );
            
            if (Array.isArray(existingProjections) && existingProjections.length > 0) {
              Logger.info(`Projection already exists for ${player.name}`);
              return true;
            }
            
            // Create a new projection
            const result = await ProjectionService.createBaseProjection(
              player.player_id,
              seasonYear,
              baselineScenario.scenario_id
            );
            
            Logger.info(`Created projection for ${player.name}:`, result);
            return true;
          } catch (error) {
            Logger.error(`Error creating projection for ${player?.name || player?.player_id || 'unknown player'}:`, error);
            return false;
          }
        });
        
        // Wait for this batch to complete
        const batchResults = await Promise.all(batchPromises);
        successCount += batchResults.filter(result => result).length;
        errorCount += batchResults.filter(result => !result).length;
        
        // Update progress log
        Logger.info(`Processed ${i + batchSize > playersData.length ? playersData.length : i + batchSize}/${playersData.length} players`);
        
        // Add a small delay to prevent overwhelming the API
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      Logger.info(`Projection generation complete: ${successCount} successful, ${errorCount} failed`);
      
      // Show toast notification
      toast({
        title: "Projections Complete",
        description: `Successfully generated ${successCount} projections with ${errorCount} failures.`,
        variant: "default",
      });
      
      // Reload the page data to show the new projections
      window.location.reload();
    } catch (err) {
      Logger.error("Error running projections:", err);
      setError(`Failed to run projections: ${err instanceof Error ? err.message : 'Unknown error'}`);
      
      // Show error toast
      toast({
        title: "Projection Error",
        description: `Failed to generate projections: ${err instanceof Error ? err.message : 'Unknown error'}`,
        variant: "destructive",
      });
    } finally {
      setIsRunningProjections(false);
    }
  };
  
  const summaryStats = getSummaryStats();
  
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your projection data and analytics
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-sm text-right">
            <div className="flex gap-2 items-center text-muted-foreground">
              <ChartPieIcon className="h-4 w-4" />
              <span>Active Scenario:</span>
            </div>
            <div className="font-medium">{baselineScenario?.name || 'None'}</div>
          </div>
          <Button size="sm" variant="default" onClick={runBaselineProjections} disabled={isRunningProjections || !baselineScenario}>
            {isRunningProjections ? "Running..." : "Run Projections"}
          </Button>
          <Button size="sm" variant="outline" asChild>
            <Link to="/scenarios">Manage Scenarios</Link>
          </Button>
        </div>
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center h-96">
          <div className="text-center space-y-4">
            <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto"></div>
            <p className="text-muted-foreground">Loading dashboard data...</p>
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
          
          {/* Main Content */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Top Players Section */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Top Players by Position</CardTitle>
                <CardDescription>
                  Top projected fantasy point scorers
                </CardDescription>
                {!baselineScenario && (
                  <div className="mt-2 p-2 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded-md text-sm">
                    No baseline scenario found. Create a scenario to see projections.
                  </div>
                )}
                {baselineScenario && Object.values(topProjections).every(arr => !arr || arr.length === 0) && (
                  <div className="mt-2 p-2 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded-md text-sm">
                    No projections found in the baseline scenario. Run projections to see players.
                  </div>
                )}
                {isRunningProjections && (
                  <div className="mt-2 p-2 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-md text-sm flex items-center">
                    <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full mr-2"></div>
                    Generating projections for all players... This may take a few moments.
                  </div>
                )}
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="QB" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="QB">Quarterbacks</TabsTrigger>
                    <TabsTrigger value="RB">Running Backs</TabsTrigger>
                    <TabsTrigger value="WR">Wide Receivers</TabsTrigger>
                    <TabsTrigger value="TE">Tight Ends</TabsTrigger>
                  </TabsList>
                  
                  {['QB', 'RB', 'WR', 'TE'].map(position => (
                    <TabsContent value={position} key={position}>
                      <ScrollArea className="h-[350px] pr-4">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Rank</TableHead>
                              <TableHead>Player</TableHead>
                              <TableHead>Team</TableHead>
                              <TableHead className="text-right">Fantasy Pts</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(topProjections[position] || []).map((projection, index) => {
                              if (!projection || !projection.player_id) return null;
                              const { name, team } = getPlayerInfo(projection.player_id);
                              return (
                                <TableRow key={projection.projection_id || `player-${index}`}>
                                  <TableCell className="font-medium">
                                    {index + 1}
                                  </TableCell>
                                  <TableCell>
                                    <Link 
                                      to={`/players/${projection.player_id}`}
                                      className="hover:underline text-primary"
                                    >
                                      {name}
                                    </Link>
                                  </TableCell>
                                  <TableCell>{team}</TableCell>
                                  <TableCell className="text-right font-medium">
                                    {(projection.half_ppr || 0).toFixed(1)}
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                            {(!topProjections[position] || topProjections[position].length === 0) && (
                              <TableRow>
                                <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                                  No projections available for {position}s
                                </TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </ScrollArea>
                      <div className="mt-4 flex justify-end">
                        <Button variant="outline" size="sm" asChild>
                          <Link to={`/players?position=${position}`}>
                            View All {position}s
                          </Link>
                        </Button>
                      </div>
                    </TabsContent>
                  ))}
                </Tabs>
              </CardContent>
            </Card>
            
            {/* Player Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Player Analysis</CardTitle>
                <CardDescription>
                  Distribution and statistics
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="h-[200px]">
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
                </div>
                
                <div className="h-[200px]">
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
                </div>
              </CardContent>
            </Card>
          </div>
          
          {/* Projection Ranges */}
          <Card>
            <CardHeader>
              <CardTitle>Projection Ranges</CardTitle>
              <CardDescription>
                Visualize projection ranges with 80% confidence intervals
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[400px]">
                <ProjectionRangeChart 
                  data={projectionRangeData}
                  yAxisLabel="Fantasy Points (Half PPR)"
                  height="100%"
                />
              </div>
            </CardContent>
            <CardFooter className="flex justify-between">
              <p className="text-sm text-muted-foreground">
                Showing top players from each position with uncertainty ranges
              </p>
              <Button variant="outline" size="sm" asChild>
                <Link to="/compare">
                  <ArrowRightIcon className="h-4 w-4 mr-2" />
                  Compare Players
                </Link>
              </Button>
            </CardFooter>
          </Card>
          
          {/* Scenario Comparison */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Scenarios</CardTitle>
              <CardDescription>
                Compare fantasy projections across scenarios
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Scenario</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scenarios.slice(0, 5).map(scenario => (
                    <TableRow key={scenario.scenario_id}>
                      <TableCell className="font-medium">
                        {scenario.name}
                      </TableCell>
                      <TableCell>
                        {scenario.is_baseline ? (
                          <Badge>Baseline</Badge>
                        ) : (
                          <Badge variant="outline">Alternative</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(scenario.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" asChild>
                          <Link to={`/scenarios/${scenario.scenario_id}`}>
                            View
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {scenarios.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                        No scenarios found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};

export default DashboardPage;