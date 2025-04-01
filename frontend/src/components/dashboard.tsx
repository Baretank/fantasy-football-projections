import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
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
  Cell 
} from 'recharts';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { 
  PlayerService, 
  ProjectionService, 
  ScenarioService 
} from '@/services/api';
import { Player, Projection, Scenario } from '@/types/index';

const Dashboard: React.FC = () => {
  // State management for scenarios and top projections
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [topProjections, setTopProjections] = useState<Record<string, Projection[]>>({});
  const [players, setPlayers] = useState<Player[]>([]);
  const [baselineScenario, setBaselineScenario] = useState<Scenario | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [positionDistribution, setPositionDistribution] = useState<any[]>([]);
  const [teamDistribution, setTeamDistribution] = useState<any[]>([]);

  // Colors for charts
  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088FE', '#00C49F'];

  // Fetch data on component mount
  useEffect(() => {
    async function fetchData() {
      try {
        setIsLoading(true);
        setError(null);
        
        // Fetch all players first
        const playersData = await PlayerService.getPlayers();
        setPlayers(playersData);
        
        // Calculate position distribution
        const positionCounts: Record<string, number> = {};
        playersData.forEach(player => {
          positionCounts[player.position] = (positionCounts[player.position] || 0) + 1;
        });
        
        setPositionDistribution(
          Object.entries(positionCounts).map(([position, count], index) => ({
            name: position,
            value: count,
            color: COLORS[index % COLORS.length]
          }))
        );
        
        // Calculate team distribution
        const teamCounts: Record<string, number> = {};
        playersData.forEach(player => {
          teamCounts[player.team] = (teamCounts[player.team] || 0) + 1;
        });
        
        // Sort teams by player count
        setTeamDistribution(
          Object.entries(teamCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .map(([team, count], index) => ({
              name: team,
              players: count
            }))
        );
        
        // Fetch all scenarios
        const scenariosData = await ScenarioService.getScenarios();
        setScenarios(scenariosData);
        
        // Find baseline scenario
        const baseline = scenariosData.find(s => s.is_baseline) || scenariosData[0];
        setBaselineScenario(baseline);
        
        // For the selected/default scenario, get top projections by position
        if (baseline) {
          const byPosition: Record<string, Projection[]> = {};
          
          // Fetch top projections for each position
          for (const position of ['QB', 'RB', 'WR', 'TE']) {
            try {
              // Get projections for this position in the baseline scenario
              const projections = await ScenarioService.getScenarioProjections(
                baseline.scenario_id,
                position
              );
              
              // Sort by half PPR points
              const sorted = projections
                .sort((a, b) => b.half_ppr - a.half_ppr)
                .slice(0, 10);
                
              byPosition[position] = sorted;
            } catch (posError) {
              console.error(`Error fetching ${position} projections:`, posError);
              byPosition[position] = [];
            }
          }
          
          setTopProjections(byPosition);
        }
      } catch (err) {
        console.error("Error fetching dashboard data:", err);
        setError("Failed to load dashboard data. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchData();
  }, []);

  // Get player name from ID
  const getPlayerName = (playerId: string): string => {
    const player = players.find(p => p.player_id === playerId);
    return player ? player.name : 'Unknown Player';
  };

  // Get player team from ID
  const getPlayerTeam = (playerId: string): string => {
    const player = players.find(p => p.player_id === playerId);
    return player ? player.team : '';
  };

  // Calculate total fantasy points by position
  const getPositionFantasyPoints = () => {
    const result: any[] = [];
    
    for (const [position, projections] of Object.entries(topProjections)) {
      const totalPoints = projections.reduce((sum, proj) => sum + proj.half_ppr, 0);
      const avgPoints = projections.length > 0 ? totalPoints / projections.length : 0;
      
      result.push({
        position,
        totalPoints,
        avgPoints,
        playerCount: projections.length
      });
    }
    
    return result;
  };

  return (
    <div className="space-y-6 p-4">
      <div className="grid grid-cols-2 gap-4">
        {/* Scenarios summary */}
        <Card>
          <CardHeader>
            <CardTitle>Projection Scenarios</CardTitle>
            <CardDescription>
              {scenarios.length} total scenarios available
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">Loading scenarios...</div>
            ) : error ? (
              <div className="text-center py-8 text-red-500">{error}</div>
            ) : (
              <div className="space-y-4">
                <div className="border rounded-md">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Scenario</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {scenarios.map(scenario => (
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
                        </TableRow>
                      ))}
                      {scenarios.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={3} className="text-center text-muted-foreground">
                            No scenarios found
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
                
                {baselineScenario && (
                  <div className="bg-muted p-3 rounded-md">
                    <div className="font-medium">Current Baseline:</div>
                    <div className="text-lg mt-1">{baselineScenario.name}</div>
                    {baselineScenario.description && (
                      <div className="text-sm text-muted-foreground mt-1">
                        {baselineScenario.description}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Button variant="outline" className="w-full">
              Manage Scenarios
            </Button>
          </CardFooter>
        </Card>
        
        {/* Player distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Player Analysis</CardTitle>
            <CardDescription>
              Distribution and statistics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="positions">
              <TabsList className="mb-4">
                <TabsTrigger value="positions">Positions</TabsTrigger>
                <TabsTrigger value="teams">Teams</TabsTrigger>
                <TabsTrigger value="stats">Fantasy Points</TabsTrigger>
              </TabsList>
              
              <TabsContent value="positions" className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={positionDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={5}
                      dataKey="value"
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    >
                      {positionDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [`${value} players`, 'Count']} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </TabsContent>
              
              <TabsContent value="teams" className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={teamDistribution}
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
              </TabsContent>
              
              <TabsContent value="stats" className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={getPositionFantasyPoints()}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="position" />
                    <YAxis />
                    <Tooltip 
                      formatter={(value) => [
                        Number(value).toFixed(1),
                        'Fantasy Points'
                      ]}
                    />
                    <Legend />
                    <Bar name="Avg Fantasy Points" dataKey="avgPoints" fill="#82ca9d" />
                  </BarChart>
                </ResponsiveContainer>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
      
      {/* Top projections by position */}
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
                <div className="text-center py-4 text-red-500">Error loading data</div>
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
                    {(topProjections[position] || []).slice(0, 5).map(projection => (
                      <TableRow key={projection.projection_id}>
                        <TableCell className="py-1 font-medium">
                          {getPlayerName(projection.player_id)}
                        </TableCell>
                        <TableCell className="py-1">
                          {getPlayerTeam(projection.player_id)}
                        </TableCell>
                        <TableCell className="py-1 text-right">
                          {projection.half_ppr.toFixed(1)}
                        </TableCell>
                      </TableRow>
                    ))}
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
              <Button variant="ghost" size="sm" className="w-full">
                View All {position}s
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
      
      {/* Fantasy point trends */}
      <Card>
        <CardHeader>
          <CardTitle>Fantasy Point Distribution</CardTitle>
          <CardDescription>
            Fantasy point comparison across top players
          </CardDescription>
        </CardHeader>
        <CardContent className="h-80">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Loading fantasy point data...
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-500">
              {error}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={Object.entries(topProjections).flatMap(([position, projections]) =>
                  projections.slice(0, 3).map(proj => ({
                    name: getPlayerName(proj.player_id),
                    position,
                    team: getPlayerTeam(proj.player_id),
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
                        <div className="bg-white p-2 border shadow-sm rounded-md">
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
                  fill="#8884d8"
                  name="Fantasy Points"
                  // Color bars based on position
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
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;