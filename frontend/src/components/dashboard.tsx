import React, { useState, useEffect } from 'react';
import { Logger } from '@/utils/logger';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowUpIcon, ArrowDownIcon, MagnifyingGlassIcon, ArrowsUpDownIcon } from '@heroicons/react/24/outline';
import { PlayerService, ScenarioService } from '@/services/api';
import { Player, Projection, Scenario, STAT_FORMATS } from '@/types/index';
import { useSeason } from '@/context/SeasonContext';

const Dashboard: React.FC = () => {
  // Get the current season from context
  const { season } = useSeason();
  
  // State management
  const [players, setPlayers] = useState<Player[]>([]);
  const [projections, setProjections] = useState<{ [key: string]: Projection }>({});
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortField, setSortField] = useState<string>('half_ppr');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [positionFilter, setPositionFilter] = useState<string>('ALL');
  const [teamFilter, setTeamFilter] = useState<string>('ALL');
  const [availableTeams, setAvailableTeams] = useState<string[]>([]);
  
  // Fetch data when component mounts or when season changes
  useEffect(() => {
    async function fetchData() {
      try {
        setIsLoading(true);
        setError(null);
        
        // Log the current season being used
        Logger.info(`Dashboard: Loading data for season ${season}`);
        
        // Fetch all scenarios first
        const scenariosData = await ScenarioService.getScenarios();
        setScenarios(Array.isArray(scenariosData) ? scenariosData : []);
        
        // Find baseline scenario
        const baseline = Array.isArray(scenariosData) && scenariosData.length > 0 
          ? scenariosData.find(s => s.is_baseline) || scenariosData[0]
          : null;
          
        if (baseline) {
          setSelectedScenario(baseline.scenario_id);
        }
        
        // Fetch all players that match fantasy-relevant positions for the current season
        Logger.info(`Dashboard: Fetching all fantasy-relevant players for season ${season}`);
        
        // Don't use status filter since the database has different status codes
        const fantasyPositions = ['QB', 'RB', 'WR', 'TE'];
        
        // Always explicitly pass the season parameter to ensure correct filtering
        Logger.info(`Dashboard: Explicitly using season ${season} for player filtering`);
        
        // Fetch all players with season parameter and filter by position client-side
        const allPlayersData = await PlayerService.getPlayers(undefined, undefined, undefined, season);
        
        Logger.info(`Dashboard: Received ${allPlayersData?.length || 0} players from API for season ${season}`);
        
        const fantasyPlayers = Array.isArray(allPlayersData) 
          ? allPlayersData.filter(p => p && p.position && fantasyPositions.includes(p.position))
          : Array.isArray(allPlayersData?.players)
              ? allPlayersData.players.filter(p => p && p.position && fantasyPositions.includes(p.position))
              : [];
              
        Logger.info(`Dashboard: Filtered to ${fantasyPlayers.length} fantasy players for season ${season}`);
        
        // Use the filtered players
        const playersData = fantasyPlayers
        
        Logger.info(`Dashboard: Received ${Array.isArray(playersData) ? playersData.length : 'unknown'} players`);
        
        // Ensure we always set an array for players
        setPlayers(Array.isArray(playersData) ? playersData : []);
        
        // Extract unique teams
        if (Array.isArray(playersData)) {
          const teams = Array.from(new Set(playersData.map(p => p.team).filter(Boolean)));
          teams.sort();
          setAvailableTeams(teams);
        }
        
        // If we have a baseline scenario, fetch projections
        if (baseline) {
          // Fetch projections for this scenario
          const allProjections = await ScenarioService.getScenarioProjections(baseline.scenario_id);
          
          // Create a lookup map for quick access
          const projectionsMap: { [key: string]: Projection } = {};
          if (Array.isArray(allProjections)) {
            allProjections.forEach(proj => {
              if (proj && proj.player_id) {
                projectionsMap[proj.player_id] = proj;
              }
            });
          }
          
          setProjections(projectionsMap);
        }
      } catch (err) {
        Logger.error("Error fetching dashboard data:", err);
        setError("Failed to load data. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchData();
  }, [season]); // Re-fetch data when season changes
  
  // Handle scenario change
  const handleScenarioChange = async (scenarioId: string) => {
    if (!scenarioId) return;
    
    try {
      setIsLoading(true);
      setSelectedScenario(scenarioId);
      
      // Fetch projections for this scenario
      const allProjections = await ScenarioService.getScenarioProjections(scenarioId);
      
      // Create a lookup map
      const projectionsMap: { [key: string]: Projection } = {};
      if (Array.isArray(allProjections)) {
        allProjections.forEach(proj => {
          if (proj && proj.player_id) {
            projectionsMap[proj.player_id] = proj;
          }
        });
      }
      
      setProjections(projectionsMap);
    } catch (err) {
      Logger.error("Error fetching scenario projections:", err);
      setError("Failed to load scenario projections.");
    } finally {
      setIsLoading(false);
    }
  };
  
  // Handle sort change
  const handleSortChange = (field: string) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, set to descending by default
      setSortField(field);
      setSortDirection('desc');
    }
  };
  
  // Filter and sort players
  const getFilteredAndSortedPlayers = () => {
    // Ensure players is an array before trying to filter it
    if (!players || !Array.isArray(players) || players.length === 0) {
      Logger.debug("getFilteredAndSortedPlayers: No players to filter!");
      return [];
    }
    
    Logger.debug(`getFilteredAndSortedPlayers: Starting with ${players.length} players`);
    
    // Check player types
    const samplePlayers = players.slice(0, 3);
    Logger.debug("Sample players:", samplePlayers);
    
    // Apply filters
    const filteredPlayers = players.filter(player => {
      if (!player) {
        Logger.debug("Found null/undefined player in array");
        return false;
      }
      
      // Search filter
      const matchesSearch = searchTerm === '' || 
        (player.name && player.name.toLowerCase().includes(searchTerm.toLowerCase()));
      
      // Position filter
      const matchesPosition = positionFilter === 'ALL' || 
        player.position === positionFilter;
      
      // Team filter
      const matchesTeam = teamFilter === 'ALL' || 
        player.team === teamFilter;
      
      const matches = matchesSearch && matchesPosition && matchesTeam;
      return matches;
    });
    
    Logger.debug(`getFilteredAndSortedPlayers: After filtering: ${filteredPlayers.length} players`);
    
    return filteredPlayers
      .sort((a, b) => {
        // Sort based on projection stats
        const projA = projections[a.player_id];
        const projB = projections[b.player_id];
        
        // Default to player name if no projections or different sort field
        if (!projA && !projB) {
          return (a.name || '').localeCompare(b.name || '');
        }
        
        if (!projA) return 1; // Push players without projections to end
        if (!projB) return -1;
        
        // Sort by the selected field
        const valueA = projA[sortField as keyof Projection] as number || 0;
        const valueB = projB[sortField as keyof Projection] as number || 0;
        
        return sortDirection === 'asc' 
          ? valueA - valueB 
          : valueB - valueA;
      });
  };

  // Determine the columns to show based on position filter
  const getColumnsForPosition = (position: string) => {
    if (position === 'QB') {
      return [
        // Fantasy points
        'half_ppr',
        // Game info
        'games',
        // Passing stats
        'pass_attempts', 'completions', 'pass_yards', 'pass_td', 'interceptions',
        'sacks', 'sack_yards', 'gross_pass_yards', 'net_pass_yards',
        // Rushing stats
        'rush_attempts', 'rush_yards', 'rush_td', 'fumbles',
        // Efficiency metrics
        'comp_pct', 'yards_per_att', 'net_yards_per_att', 
        'pass_td_rate', 'int_rate', 'sack_rate', 'yards_per_carry',
        // Usage metrics
        'snap_share', 'pass_att_pct',
        // Status
        'has_overrides', 'is_fill_player',
      ];
    } else if (position === 'RB') {
      return [
        // Fantasy points
        'half_ppr',
        // Game info
        'games',
        // Rushing stats
        'rush_attempts', 'rush_yards', 'rush_td', 'fumbles',
        // Receiving stats
        'targets', 'receptions', 'rec_yards', 'rec_td',
        // Efficiency metrics
        'yards_per_carry', 'net_yards_per_carry', 'rush_td_rate',
        'fumble_rate', 'catch_pct', 'yards_per_target', 'rec_td_rate',
        // Usage metrics
        'snap_share', 'target_share', 'rush_share', 'redzone_share', 'car_pct', 'tar_pct',
        // Status
        'has_overrides', 'is_fill_player',
      ];
    } else if (position === 'WR' || position === 'TE') {
      return [
        // Fantasy points
        'half_ppr',
        // Game info
        'games',
        // Receiving stats
        'targets', 'receptions', 'rec_yards', 'rec_td',
        // Rushing stats (for WRs with rushing)
        'rush_attempts', 'rush_yards', 'rush_td',
        // Efficiency metrics
        'catch_pct', 'yards_per_target', 'rec_td_rate',
        // Usage metrics
        'snap_share', 'target_share', 'redzone_share', 'tar_pct',
        // Status
        'has_overrides', 'is_fill_player',
      ];
    } else {
      // ALL positions - show the most relevant stats across positions
      return [
        // Fantasy points
        'half_ppr',
        // Game info
        'games',
        // Passing stats
        'pass_attempts', 'completions', 'pass_yards', 'pass_td', 'interceptions',
        // Rushing stats
        'rush_attempts', 'rush_yards', 'rush_td',
        // Receiving stats
        'targets', 'receptions', 'rec_yards', 'rec_td',
        // Key efficiency metrics
        'comp_pct', 'yards_per_att', 'yards_per_carry', 'catch_pct', 'yards_per_target',
        // Key usage metrics
        'target_share', 'rush_share',
        // Status
        'has_overrides',
      ];
    }
  };

  // Format the value of a stat based on the stat name
  const formatStatValue = (projection: Projection, statName: string) => {
    if (!projection || projection[statName as keyof Projection] === undefined) {
      return '-';
    }
    
    const value = projection[statName as keyof Projection] as number;
    
    // Use the predefined formatters from our types if available
    if (STAT_FORMATS[statName]) {
      return STAT_FORMATS[statName].formatter(value);
    }
    
    // Fallback formatting
    if (typeof value === 'number') {
      return value.toFixed(1);
    }
    
    return String(value);
  };

  const filteredPlayers = getFilteredAndSortedPlayers();
  
  return (
    <div className="space-y-6">
      {/* Top controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold">
            Player Projections - {season}
            <span className="text-sm font-normal text-muted-foreground ml-2">
              {season >= 2025 ? '(Current Season)' : '(Historical Season)'}
            </span>
          </h2>
          <p className="text-muted-foreground">
            {filteredPlayers.length} fantasy-relevant players found
            {season >= 2025 
              ? ' - Filtered by Active Player Roster' 
              : ' - Showing historical players with stats'}
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
          <Select 
            value={selectedScenario || ''} 
            onValueChange={handleScenarioChange}
          >
            <SelectTrigger className="w-full sm:w-[200px]">
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
          
          <div className="relative w-full sm:w-[250px]">
            <MagnifyingGlassIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search players..."
              className="pl-8"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div>
          <Select value={positionFilter} onValueChange={setPositionFilter}>
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="Position" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Positions</SelectItem>
              <SelectItem value="QB">QB</SelectItem>
              <SelectItem value="RB">RB</SelectItem>
              <SelectItem value="WR">WR</SelectItem>
              <SelectItem value="TE">TE</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        <div>
          <Select value={teamFilter} onValueChange={setTeamFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Team" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Teams</SelectItem>
              {availableTeams.map(team => (
                <SelectItem key={team} value={team}>{team}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <div className="ml-auto flex gap-2">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => {
              setSearchTerm('');
              setPositionFilter('ALL');
              setTeamFilter('ALL');
            }}
          >
            Reset Filters
          </Button>
        </div>
      </div>
      
      {/* Main Table */}
      <Card>
        <CardHeader className="p-4">
          <CardTitle>Player Projections</CardTitle>
          {selectedScenario && scenarios.length > 0 && (
            <CardDescription>
              Showing projections for: {scenarios.find(s => s.scenario_id === selectedScenario)?.name || 'Selected Scenario'}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-96">
              <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full"></div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-48 text-red-500">
              {error}
            </div>
          ) : (
            <div className="relative h-[65vh] border-t">
              <div className="absolute inset-0 overflow-x-auto overflow-y-auto">
                <div className="min-w-full"> 
                  <table className="min-w-full divide-y divide-gray-200 table-fixed">
                    <thead className="bg-background sticky top-0 z-10">
                      <tr>
                        <th className="w-12 py-3 px-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-background z-20 shadow-[1px_0_0_0_#e5e7eb]">
                          Rank
                        </th>
                        <th className="w-[180px] min-w-[180px] py-3 px-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-12 bg-background z-20 shadow-[1px_0_0_0_#e5e7eb]">
                          Player
                        </th>
                        <th className="w-16 py-3 px-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-[192px] bg-background z-20 shadow-[1px_0_0_0_#e5e7eb]">
                          Pos
                        </th>
                        <th className="w-16 py-3 px-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-[208px] bg-background z-20 shadow-[1px_0_0_0_#e5e7eb]">
                          Team
                        </th>
                        
                        {/* Dynamic Stat Columns Based on Position Filter */}
                        {getColumnsForPosition(positionFilter).map(statName => (
                          <th 
                            key={statName}
                            className="w-24 py-3 px-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer whitespace-nowrap"
                            onClick={() => handleSortChange(statName)}
                          >
                            <div className="flex items-center justify-end gap-1">
                              {STAT_FORMATS[statName]?.label || statName}
                              {sortField === statName ? (
                                sortDirection === 'asc' ? 
                                  <ArrowUpIcon className="h-3 w-3" /> : 
                                  <ArrowDownIcon className="h-3 w-3" />
                              ) : (
                                <ArrowsUpDownIcon className="h-3 w-3 text-muted-foreground opacity-50" />
                              )}
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-background divide-y divide-gray-200">
                      {filteredPlayers.length === 0 ? (
                        <tr>
                          <td colSpan={getColumnsForPosition(positionFilter).length + 4} className="px-3 py-4 text-center text-sm text-muted-foreground h-32">
                            {searchTerm || positionFilter !== 'ALL' || teamFilter !== 'ALL' ? 
                              'No players match the current filters.' : 
                              'No players found. Try a different scenario.'}
                          </td>
                        </tr>
                      ) : (
                        filteredPlayers.map((player, index) => {
                          const projection = projections[player.player_id];
                          return (
                            <tr key={player.player_id} className="hover:bg-muted/50">
                              <td className="px-3 py-2 text-sm sticky left-0 bg-background z-20 shadow-[1px_0_0_0_#e5e7eb] font-mono">
                                {index + 1}
                              </td>
                              <td className="px-3 py-2 text-sm font-medium sticky left-12 bg-background z-20 shadow-[1px_0_0_0_#e5e7eb] whitespace-nowrap">
                                <button className="text-blue-600 hover:text-blue-800 font-medium text-left w-full text-sm">
                                  {player.name}
                                </button>
                              </td>
                              <td className="px-3 py-2 text-sm text-center sticky left-[192px] bg-background z-20 shadow-[1px_0_0_0_#e5e7eb]">
                                {player.position}
                              </td>
                              <td className="px-3 py-2 text-sm sticky left-[208px] bg-background z-20 shadow-[1px_0_0_0_#e5e7eb]">
                                {player.team}
                              </td>
                              
                              {/* Dynamic Stat Values */}
                              {getColumnsForPosition(positionFilter).map(statName => {
                                // Get special formatting and colors based on the stat
                                const statFormat = STAT_FORMATS[statName];
                                const value = formatStatValue(projection, statName);
                                const colorClass = statFormat?.color && projection && projection[statName as keyof Projection] !== undefined
                                  ? statFormat.color(projection[statName as keyof Projection] as number) 
                                  : '';
                                
                                return (
                                  <td 
                                    key={statName} 
                                    className={`px-3 py-2 text-sm font-medium text-right whitespace-nowrap ${colorClass}`}
                                  >
                                    {value}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Custom scrollbar styling */}
      <style jsx global>{`
        .overflow-x-auto {
          scrollbar-width: thin;
          scrollbar-color: rgba(155, 155, 155, 0.5) transparent;
        }
        .overflow-x-auto::-webkit-scrollbar {
          height: 8px;
          width: 8px;
        }
        .overflow-x-auto::-webkit-scrollbar-track {
          background: transparent;
        }
        .overflow-x-auto::-webkit-scrollbar-thumb {
          background-color: rgba(155, 155, 155, 0.5);
          border-radius: 20px;
          border: transparent;
        }
        
        table {
          border-collapse: separate;
          border-spacing: 0;
        }
        
        .hover\:bg-muted\/50:hover {
          background-color: rgba(217, 217, 217, 0.1);
        }
      `}</style>
    </div>
  );
};

export default Dashboard;