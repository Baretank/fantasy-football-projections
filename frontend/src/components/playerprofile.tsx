import React, { useState, useEffect } from 'react';
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardContent, 
  CardDescription,
  CardFooter
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

import { PlayerService } from '@/services/api';
import { Player, STAT_FORMATS } from '@/types/index';

interface PlayerProfileProps {
  playerId: string;
  onAddToWatchlist?: (playerId: string) => void;
}

const PlayerProfile: React.FC<PlayerProfileProps> = ({ 
  playerId,
  onAddToWatchlist
}) => {
  const [player, setPlayer] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [trends, setTrends] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [availableSeasons, setAvailableSeasons] = useState<number[]>([]);

  // Fetch player data on component mount
  useEffect(() => {
    const fetchPlayerData = async () => {
      if (!playerId) return;

      try {
        setLoading(true);
        setError(null);
        
        // Get player details with stats
        const playerData = await PlayerService.getPlayer(playerId);
        setPlayer(playerData);
        
        // If we have stats, set them up
        if (playerData.stats) {
          setStats(playerData.stats);
          
          // Get available seasons
          const seasons = Object.keys(playerData.stats).map(s => parseInt(s)).sort((a, b) => b - a);
          setAvailableSeasons(seasons);
          
          // Set the most recent season as selected
          if (seasons.length > 0 && !selectedSeason) {
            setSelectedSeason(seasons[0]);
          }
        }
        
        // Get trend data if available
        if (selectedSeason) {
          const trendData = await PlayerService.getPlayerStats(playerId, selectedSeason);
          setTrends(trendData);
        }
      } catch (err) {
        console.error('Error fetching player data:', err);
        setError('Failed to load player data');
      } finally {
        setLoading(false);
      }
    };

    fetchPlayerData();
  }, [playerId, selectedSeason]);

  // Format fantasy points
  const formatPoints = (points: number) => {
    return points ? points.toFixed(1) : "N/A";
  };
  
  // Format stats for display
  const formatStat = (stat: string, value: number | undefined) => {
    if (value === undefined || value === null) return "—";
    
    const formatter = STAT_FORMATS[stat]?.formatter;
    return formatter ? formatter(value) : value.toString();
  };
  
  // Generate trend chart data
  const generateTrendData = () => {
    if (!trends || !trends.trends) return [];
    
    // Find important stats based on position
    const position = player?.position;
    let keyStats: string[] = ['half_ppr'];
    
    if (position === 'QB') {
      keyStats = [...keyStats, 'pass_yards', 'pass_td', 'interceptions', 'rush_yards'];
    } else if (position === 'RB') {
      keyStats = [...keyStats, 'rush_yards', 'rush_td', 'receptions', 'rec_yards'];
    } else {
      keyStats = [...keyStats, 'targets', 'receptions', 'rec_yards', 'rec_td'];
    }
    
    // Get trends for these stats
    const statTrends: any = {};
    keyStats.forEach(stat => {
      if (trends.trends[stat]) {
        statTrends[stat] = trends.trends[stat];
      }
    });
    
    return statTrends;
  };
  
  // Generate chart for weekly performance
  const generateWeeklyChart = () => {
    if (!stats || !selectedSeason || !stats[selectedSeason]?.weekly_stats) {
      return [];
    }
    
    const weeklyStats = stats[selectedSeason].weekly_stats;
    const weeks = Object.keys(weeklyStats).sort((a, b) => parseInt(a) - parseInt(b));
    
    // Get important stat based on position
    const position = player?.position;
    let keyStat = 'half_ppr';
    
    if (position === 'QB') {
      keyStat = 'pass_yards';
    } else if (position === 'RB') {
      keyStat = 'rush_yards';
    } else {
      keyStat = 'rec_yards';
    }
    
    // Create data for chart
    return weeks.map(week => {
      const weekData = weeklyStats[week];
      return {
        week: `Week ${week}`,
        value: weekData[keyStat] || 0,
        opponent: weekData.game_data?.opponent || ''
      };
    });
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center h-64">
            <p>Loading player profile...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !player) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center h-64">
            <p className="text-red-500">{error || 'Failed to load player'}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-2xl">{player.name}</CardTitle>
            <CardDescription>
              <div className="flex items-center space-x-2 mt-1">
                <Badge>{player.position}</Badge>
                <span>{player.team}</span>
                <Badge 
                  variant={player.status === 'Active' ? 'default' : 
                    player.status === 'Rookie' ? 'secondary' : 'destructive'}
                >
                  {player.status || 'Active'}
                </Badge>
              </div>
            </CardDescription>
          </div>
          
          {onAddToWatchlist && (
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => onAddToWatchlist(playerId)}
            >
              Add to Watchlist
            </Button>
          )}
        </div>
      </CardHeader>
      
      <CardContent>
        <Tabs defaultValue="overview">
          <TabsList className="mb-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="stats">Statistics</TabsTrigger>
            <TabsTrigger value="trends">Performance Trends</TabsTrigger>
          </TabsList>
          
          {/* Overview Tab */}
          <TabsContent value="overview">
            <div className="grid grid-cols-2 gap-4 mb-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Fantasy Points</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">
                    {formatPoints(player.projection?.half_ppr)}
                  </div>
                  <p className="text-sm text-muted-foreground">Half PPR</p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Player Info</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1 text-sm">
                    {player.height && (
                      <div className="grid grid-cols-2">
                        <span className="text-muted-foreground">Height:</span>
                        <span>{Math.floor(player.height/12)}'{player.height % 12}"</span>
                      </div>
                    )}
                    {player.weight && (
                      <div className="grid grid-cols-2">
                        <span className="text-muted-foreground">Weight:</span>
                        <span>{player.weight} lbs</span>
                      </div>
                    )}
                    {player.date_of_birth && (
                      <div className="grid grid-cols-2">
                        <span className="text-muted-foreground">Born:</span>
                        <span>{new Date(player.date_of_birth).toLocaleDateString()}</span>
                      </div>
                    )}
                    <div className="grid grid-cols-2">
                      <span className="text-muted-foreground">Status:</span>
                      <span>{player.status || 'Active'}</span>
                    </div>
                    <div className="grid grid-cols-2">
                      <span className="text-muted-foreground">Depth Chart:</span>
                      <span>{player.depth_chart_position || 'N/A'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Key Stats Summary */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Key Statistics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {player.position === 'QB' && (
                    <>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('pass_yards', player.projection?.pass_yards)}
                        </div>
                        <div className="text-xs text-muted-foreground">Pass Yards</div>
                      </div>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('pass_td', player.projection?.pass_td)}
                        </div>
                        <div className="text-xs text-muted-foreground">Pass TD</div>
                      </div>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('interceptions', player.projection?.interceptions)}
                        </div>
                        <div className="text-xs text-muted-foreground">INT</div>
                      </div>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('comp_pct', player.projection?.comp_pct)}
                        </div>
                        <div className="text-xs text-muted-foreground">Completion %</div>
                      </div>
                    </>
                  )}
                  
                  {player.position === 'RB' && (
                    <>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('rush_yards', player.projection?.rush_yards)}
                        </div>
                        <div className="text-xs text-muted-foreground">Rush Yards</div>
                      </div>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('rush_td', player.projection?.rush_td)}
                        </div>
                        <div className="text-xs text-muted-foreground">Rush TD</div>
                      </div>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('receptions', player.projection?.receptions)}
                        </div>
                        <div className="text-xs text-muted-foreground">Receptions</div>
                      </div>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('rec_yards', player.projection?.rec_yards)}
                        </div>
                        <div className="text-xs text-muted-foreground">Rec Yards</div>
                      </div>
                    </>
                  )}
                  
                  {(player.position === 'WR' || player.position === 'TE') && (
                    <>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('targets', player.projection?.targets)}
                        </div>
                        <div className="text-xs text-muted-foreground">Targets</div>
                      </div>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('receptions', player.projection?.receptions)}
                        </div>
                        <div className="text-xs text-muted-foreground">Receptions</div>
                      </div>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('rec_yards', player.projection?.rec_yards)}
                        </div>
                        <div className="text-xs text-muted-foreground">Rec Yards</div>
                      </div>
                      <div className="text-center p-2 bg-secondary/20 rounded-md">
                        <div className="text-2xl font-semibold">
                          {formatStat('rec_td', player.projection?.rec_td)}
                        </div>
                        <div className="text-xs text-muted-foreground">Rec TD</div>
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
            
            {/* Season Performance Chart */}
            {generateWeeklyChart().length > 0 && (
              <Card className="mt-4">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Season Performance</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={generateWeeklyChart()}
                        margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="week" />
                        <YAxis />
                        <Tooltip 
                          formatter={(value) => [`${value}`, player.position === 'QB' ? 'Pass Yards' : player.position === 'RB' ? 'Rush Yards' : 'Rec Yards']}
                          labelFormatter={(label) => {
                            const index = generateWeeklyChart().findIndex(d => d.week === label);
                            const opponent = index >= 0 ? generateWeeklyChart()[index].opponent : '';
                            return `${label} vs ${opponent}`;
                          }}
                        />
                        <Bar dataKey="value" fill="#8884d8" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
          
          {/* Stats Tab */}
          <TabsContent value="stats">
            <div className="space-y-4">
              {availableSeasons.length > 0 ? (
                <div className="space-y-2">
                  <div className="flex space-x-2">
                    {availableSeasons.map(season => (
                      <Button
                        key={season}
                        variant={selectedSeason === season ? "default" : "outline"}
                        size="sm"
                        onClick={() => setSelectedSeason(season)}
                      >
                        {season}
                      </Button>
                    ))}
                  </div>
                  
                  {selectedSeason && stats && stats[selectedSeason] ? (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-lg">{selectedSeason} Statistics</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Statistic</TableHead>
                              <TableHead className="text-right">Value</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {stats[selectedSeason].season_totals && Object.entries(stats[selectedSeason].season_totals).map(([stat, value]) => {
                              const formatter = STAT_FORMATS[stat]?.formatter;
                              const formattedValue = formatter ? formatter(value as number) : value;
                              
                              return (
                                <TableRow key={stat}>
                                  <TableCell>{STAT_FORMATS[stat]?.label || stat}</TableCell>
                                  <TableCell className="text-right font-medium">
                                    {formattedValue}
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  ) : (
                    <p>No statistics available for selected season</p>
                  )}
                </div>
              ) : (
                <p>No historical statistics available</p>
              )}
            </div>
          </TabsContent>
          
          {/* Trends Tab */}
          <TabsContent value="trends">
            {trends && trends.trends ? (
              <div className="space-y-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg">Performance Trends</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="week" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          
                          {/* Generate trend lines for key stats */}
                          {Object.entries(generateTrendData()).map(([stat, data]) => (
                            <Line
                              key={stat}
                              type="monotone"
                              data={data as any[]}
                              dataKey="value"
                              name={STAT_FORMATS[stat]?.label || stat}
                              stroke={getStatColor(stat)}
                              activeDot={{ r: 8 }}
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    
                    <div className="mt-4 text-sm text-muted-foreground">
                      <p>This chart shows the player's performance trends over the selected season.</p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <p>No trend data available for this player</p>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
      
      <CardFooter className="flex justify-end border-t pt-4">
        <Button variant="outline" size="sm">
          View Game Log
        </Button>
      </CardFooter>
    </Card>
  );
};

// Helper function to get a color for a stat
function getStatColor(stat: string): string {
  const colorMap: Record<string, string> = {
    half_ppr: '#8884d8',
    pass_yards: '#82ca9d',
    pass_td: '#ffc658',
    rush_yards: '#ff8042',
    rush_td: '#0088fe',
    targets: '#00c49f',
    receptions: '#ffbb28',
    rec_yards: '#ff8042',
    rec_td: '#a4de6c',
    interceptions: '#d0ed57'
  };

  return colorMap[stat] || '#8884d8';
}

export default PlayerProfile;