import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
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
import { Logger } from '@/utils/logger';
import { getCurrentSeasonYear } from '@/utils/calculatioms';

import { ProjectionService, PlayerService } from '@/services/api';
import { Player, Projection } from '@/types/index';

interface TeamStat {
  name: string;
  value: number;
  league_avg?: number;
  current_value?: number;
}

const TeamAdjuster: React.FC = () => {
  const [selectedTeam, setSelectedTeam] = useState<string>('');
  const [teams, setTeams] = useState<string[]>([]);
  const [teamStats, setTeamStats] = useState<TeamStat[]>([]);
  const [teamProjections, setTeamProjections] = useState<Projection[]>([]);
  const [teamPlayers, setTeamPlayers] = useState<Player[]>([]);
  const [teamAdjustments, setTeamAdjustments] = useState<Record<string, number>>({
    pass_volume: 100,
    rush_volume: 100,
    offensive_efficiency: 100,
    defensive_efficiency: 100,
    redzone_efficiency: 100
  });
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [applyingChanges, setApplyingChanges] = useState<boolean>(false);

  // Fetch teams on component mount
  useEffect(() => {
    const fetchTeams = async () => {
      try {
        setIsLoading(true);
        // In a real implementation, you'd fetch teams from the API
        // For now, let's use a mock list of NFL teams
        const nflTeams = [
          'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE',
          'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAC', 'KC',
          'LAC', 'LAR', 'LV', 'MIA', 'MIN', 'NE', 'NO', 'NYG',
          'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS'
        ];
        setTeams(nflTeams);
      } catch (err) {
        Logger.error('Error fetching teams:', err);
        setError('Failed to load teams');
      } finally {
        setIsLoading(false);
      }
    };

    fetchTeams();
  }, []);

  // Fetch team stats and projections when a team is selected
  useEffect(() => {
    if (!selectedTeam) return;

    const fetchTeamData = async () => {
      try {
        setIsLoading(true);
        
        // In a real implementation, we'd fetch team stats from the API
        // For now, let's use some mock data
        const mockTeamStats: TeamStat[] = [
          { name: 'Pass Attempts', value: 550, league_avg: 530, current_value: 550 },
          { name: 'Pass Yards', value: 4100, league_avg: 3800, current_value: 4100 },
          { name: 'Pass TDs', value: 28, league_avg: 24, current_value: 28 },
          { name: 'Rush Attempts', value: 420, league_avg: 450, current_value: 420 },
          { name: 'Rush Yards', value: 1800, league_avg: 2000, current_value: 1800 },
          { name: 'Rush TDs', value: 15, league_avg: 16, current_value: 15 },
          { name: 'Red Zone Trips', value: 54, league_avg: 50, current_value: 54 },
          { name: 'Red Zone Success %', value: 55, league_avg: 52, current_value: 55 }
        ];
        setTeamStats(mockTeamStats);

        // Fetch players for this team
        const playersResponse = await PlayerService.getPlayers(undefined, selectedTeam);
        
        // Handle the response structure properly (playersResponse is { players: [], pagination: {} })
        const players = Array.isArray(playersResponse?.players) 
          ? playersResponse.players 
          : [];
        
        setTeamPlayers(players);
        
        // Fetch projections for these players
        const projections: Projection[] = [];
        if (Array.isArray(players)) {
          for (const player of players) {
            if (player && player.player_id) {
              const playerProjections = await ProjectionService.getPlayerProjections(player.player_id);
              if (Array.isArray(playerProjections) && playerProjections.length > 0) {
                projections.push(playerProjections[0]);
              }
            }
          }
        }
        setTeamProjections(projections);

      } catch (err) {
        Logger.error(`Error fetching data for team ${selectedTeam}:`, err);
        setError(`Failed to load data for ${selectedTeam}`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTeamData();
  }, [selectedTeam]);

  // Function to handle adjustment changes
  const handleAdjustmentChange = (adjustmentKey: string, value: number) => {
    setTeamAdjustments(prev => ({
      ...prev,
      [adjustmentKey]: value
    }));
  };

  // Function to apply team adjustments to all players
  const applyTeamAdjustments = async () => {
    if (!selectedTeam) return;

    try {
      setApplyingChanges(true);
      
      // In a real implementation, we'd send the adjustments to the API
      // Use utility function for consistent season handling
      await ProjectionService.applyTeamAdjustments(
        selectedTeam,
        getCurrentSeasonYear(), // Dynamic season year
        teamAdjustments
      );

      // Simulate updating team stats based on adjustments
      setTeamStats(prev => 
        prev.map(stat => {
          let adjustmentFactor = 1;
          
          // Apply relevant adjustment factor based on stat name
          if (stat.name.includes('Pass')) {
            adjustmentFactor = teamAdjustments.pass_volume / 100;
          } else if (stat.name.includes('Rush')) {
            adjustmentFactor = teamAdjustments.rush_volume / 100;
          } else if (stat.name.includes('Red Zone')) {
            adjustmentFactor = teamAdjustments.redzone_efficiency / 100;
          }
          
          return {
            ...stat,
            current_value: Math.round(stat.value * adjustmentFactor)
          };
        })
      );

      // Refetch team projections to show updated values
      const players = teamPlayers;
      const projections: Projection[] = [];
      
      if (Array.isArray(players)) {
        for (const player of players) {
          if (player && player.player_id) {
            const playerProjections = await ProjectionService.getPlayerProjections(player.player_id);
            if (Array.isArray(playerProjections) && playerProjections.length > 0) {
              projections.push(playerProjections[0]);
            }
          }
        }
      }
      
      setTeamProjections(projections);

    } catch (err) {
      Logger.error('Error applying team adjustments:', err);
      setError('Failed to apply team adjustments');
    } finally {
      setApplyingChanges(false);
    }
  };

  // Function to reset all adjustments to 100%
  const resetAdjustments = () => {
    setTeamAdjustments({
      pass_volume: 100,
      rush_volume: 100,
      offensive_efficiency: 100,
      defensive_efficiency: 100,
      redzone_efficiency: 100
    });
  };

  // Group team players by position
  const playersByPosition = Array.isArray(teamPlayers) 
    ? teamPlayers.reduce((acc, player) => {
        if (player && player.position) {
          if (!acc[player.position]) {
            acc[player.position] = [];
          }
          acc[player.position].push(player);
        }
        return acc;
      }, {} as Record<string, Player[]>)
    : {} as Record<string, Player[]>;

  // Get projection for a player
  const getProjectionForPlayer = (playerId: string) => {
    if (!playerId || !Array.isArray(teamProjections)) return null;
    return teamProjections.find(p => p && p.player_id === playerId);
  };

  // Calculate fantasy points by position
  const fantasyPointsByPosition = Object.entries(playersByPosition || {}).map(([position, players]) => {
    const totalPoints = Array.isArray(players) 
      ? players.reduce((sum, player) => {
          if (!player || !player.player_id) return sum;
          const projection = getProjectionForPlayer(player.player_id);
          return sum + (projection?.half_ppr || 0);
        }, 0)
      : 0;
    
    const playerCount = Array.isArray(players) ? players.length : 0;
    
    return {
      position,
      totalPoints,
      playerCount,
      avgPoints: playerCount > 0 ? totalPoints / playerCount : 0
    };
  });

  return (
    <div className="grid grid-cols-12 gap-4 p-4">
      {/* Team Selection and Stats */}
      <Card className="col-span-8">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Team Adjustments</CardTitle>
              <CardDescription>
                Adjust team-level stats to see impact on player projections
              </CardDescription>
            </div>
            <div className="w-48">
              <Select
                value={selectedTeam}
                onValueChange={(value) => setSelectedTeam(value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Team" />
                </SelectTrigger>
                <SelectContent>
                  {teams.map(team => (
                    <SelectItem key={team} value={team}>
                      {team}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {!selectedTeam ? (
            <div className="flex items-center justify-center h-96 text-muted-foreground">
              Select a team to begin making adjustments
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center h-96 text-muted-foreground">
              Loading team data...
            </div>
          ) : (
            <div className="space-y-6">
              {/* Team adjustment sliders */}
              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Offensive Adjustments</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <Label>Pass Volume</Label>
                        <span className="text-sm font-medium">
                          {teamAdjustments.pass_volume}%
                        </span>
                      </div>
                      <Slider
                        value={[teamAdjustments.pass_volume]}
                        min={70}
                        max={130}
                        step={5}
                        onValueChange={([value]) => handleAdjustmentChange('pass_volume', value)}
                      />
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <Label>Rush Volume</Label>
                        <span className="text-sm font-medium">
                          {teamAdjustments.rush_volume}%
                        </span>
                      </div>
                      <Slider
                        value={[teamAdjustments.rush_volume]}
                        min={70}
                        max={130}
                        step={5}
                        onValueChange={([value]) => handleAdjustmentChange('rush_volume', value)}
                      />
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <Label>Offensive Efficiency</Label>
                        <span className="text-sm font-medium">
                          {teamAdjustments.offensive_efficiency}%
                        </span>
                      </div>
                      <Slider
                        value={[teamAdjustments.offensive_efficiency]}
                        min={70}
                        max={130}
                        step={5}
                        onValueChange={([value]) => handleAdjustmentChange('offensive_efficiency', value)}
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Advanced Adjustments</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <Label>Defensive Efficiency</Label>
                        <span className="text-sm font-medium">
                          {teamAdjustments.defensive_efficiency}%
                        </span>
                      </div>
                      <Slider
                        value={[teamAdjustments.defensive_efficiency]}
                        min={70}
                        max={130}
                        step={5}
                        onValueChange={([value]) => handleAdjustmentChange('defensive_efficiency', value)}
                      />
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <Label>Red Zone Efficiency</Label>
                        <span className="text-sm font-medium">
                          {teamAdjustments.redzone_efficiency}%
                        </span>
                      </div>
                      <Slider
                        value={[teamAdjustments.redzone_efficiency]}
                        min={70}
                        max={130}
                        step={5}
                        onValueChange={([value]) => handleAdjustmentChange('redzone_efficiency', value)}
                      />
                    </div>

                    <div className="flex justify-between gap-2 pt-4">
                      <Button 
                        variant="outline" 
                        className="w-full"
                        onClick={resetAdjustments}
                      >
                        Reset
                      </Button>
                      <Button 
                        className="w-full"
                        onClick={applyTeamAdjustments}
                        disabled={applyingChanges}
                      >
                        Apply Adjustments
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Team stats */}
              <div>
                <h3 className="text-lg font-medium mb-4">Team Stat Impact</h3>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={teamStats.filter(stat => 
                        !stat.name.includes('%') && 
                        stat.current_value !== undefined
                      )}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip formatter={(value) => [Number(value).toFixed(0), 'Value']} />
                      <Legend />
                      <Bar dataKey="current_value" name="Adjusted" fill="#82ca9d" />
                      <Bar dataKey="value" name="Baseline" fill="#8884d8" />
                      <Bar dataKey="league_avg" name="League Avg" fill="#ffc658" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Team players table */}
              <div>
                <h3 className="text-lg font-medium mb-4">Team Players Impact</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Player</TableHead>
                      <TableHead>Pos</TableHead>
                      <TableHead>Half PPR</TableHead>
                      <TableHead>Change</TableHead>
                      <TableHead>Key Stats</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Array.isArray(teamPlayers) ? teamPlayers
                      .filter(player => player && player.player_id)
                      .sort((a, b) => {
                        const projA = getProjectionForPlayer(a.player_id);
                        const projB = getProjectionForPlayer(b.player_id);
                        const ptsA = projA?.half_ppr || 0;
                        const ptsB = projB?.half_ppr || 0;
                        return ptsB - ptsA;
                      })
                      .map(player => {
                        if (!player || !player.player_id) return null;
                        
                        const proj = getProjectionForPlayer(player.player_id);
                        if (!proj) return null;

                        let keyStats = '';
                        if (player.position === 'QB') {
                          keyStats = `${proj.pass_yards?.toFixed(0) || 0} yds, ${proj.pass_td?.toFixed(1) || 0} TD`;
                        } else if (player.position === 'RB') {
                          keyStats = `${proj.rush_yards?.toFixed(0) || 0} rush, ${proj.receptions?.toFixed(0) || 0} rec`;
                        } else {
                          keyStats = `${proj.receptions?.toFixed(0) || 0} rec, ${proj.rec_yards?.toFixed(0) || 0} yds`;
                        }

                        // Mocked change - in reality this would compare to pre-adjustment value
                        const change = (Math.random() * 10 - 5).toFixed(1);

                        return (
                          <TableRow key={player.player_id}>
                            <TableCell className="font-medium">
                              {player.name || 'Unknown Player'}
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {player.position || 'N/A'}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {(proj.half_ppr || 0).toFixed(1)}
                            </TableCell>
                            <TableCell>
                              <span className={Number(change) >= 0 ? "text-green-500" : "text-red-500"}>
                                {Number(change) >= 0 ? "+" : ""}{change}
                              </span>
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {keyStats}
                            </TableCell>
                          </TableRow>
                        );
                      }) : null}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Position Summary */}
      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Position Impact</CardTitle>
          <CardDescription>
            {selectedTeam 
              ? `Fantasy point distribution for ${selectedTeam} players` 
              : "Select a team to see position breakdown"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!selectedTeam ? (
            <div className="flex items-center justify-center h-96 text-muted-foreground">
              No team selected
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center h-96 text-muted-foreground">
              Loading team data...
            </div>
          ) : (
            <div className="space-y-6">
              {/* Fantasy points by position */}
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={fantasyPointsByPosition}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="position" />
                    <YAxis />
                    <Tooltip formatter={(value) => [Number(value).toFixed(1), 'Fantasy Points']} />
                    <Legend />
                    <Bar 
                      dataKey="avgPoints" 
                      name="Avg Points" 
                      fill="#8884d8" 
                    />
                    <Bar 
                      dataKey="totalPoints" 
                      name="Total Points" 
                      fill="#82ca9d" 
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <Separator />

              {/* Position stats */}
              <div>
                <h3 className="text-lg font-medium mb-4">Position Distribution</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Position</TableHead>
                      <TableHead>Players</TableHead>
                      <TableHead>Total Pts</TableHead>
                      <TableHead>Avg Pts</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {fantasyPointsByPosition.map(posStat => (
                      <TableRow key={posStat.position}>
                        <TableCell className="font-medium">
                          {posStat.position}
                        </TableCell>
                        <TableCell>{posStat.playerCount}</TableCell>
                        <TableCell>{posStat.totalPoints.toFixed(1)}</TableCell>
                        <TableCell>{posStat.avgPoints.toFixed(1)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <Separator />

              {/* Top players */}
              <div>
                <h3 className="text-lg font-medium mb-4">Top Players</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Player</TableHead>
                      <TableHead>Position</TableHead>
                      <TableHead>Fantasy Pts</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Array.isArray(teamPlayers) ? teamPlayers
                      .filter(player => player && player.player_id)
                      .map(player => ({
                        player,
                        projection: getProjectionForPlayer(player.player_id)
                      }))
                      .filter(item => item.projection && item.player)
                      .sort((a, b) => (b.projection?.half_ppr || 0) - (a.projection?.half_ppr || 0))
                      .slice(0, 5)
                      .map(({ player, projection }) => (
                        <TableRow key={player.player_id}>
                          <TableCell className="font-medium">
                            {player.name || 'Unknown Player'}
                          </TableCell>
                          <TableCell>{player.position || 'N/A'}</TableCell>
                          <TableCell>{(projection?.half_ppr || 0).toFixed(1)}</TableCell>
                        </TableRow>
                      )) : null}
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

export default TeamAdjuster;