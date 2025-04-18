import React, { useState, useEffect } from 'react';
import { Logger } from '@/utils/logger';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { 
  Table, 
  TableHeader, 
  TableRow, 
  TableHead, 
  TableBody, 
  TableCell 
} from '@/components/ui/table';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Button } from '@/components/ui/button';

import { PlayerService } from '@/services/api';
import { Player } from '@/types/index';

interface PlayerSelectProps {
  onSelect?: (playerId: string) => void;
  initialPosition?: string;
  initialTeam?: string;
  showDetails?: boolean;
}

const PlayerSelect: React.FC<PlayerSelectProps> = ({ 
  onSelect, 
  initialPosition = 'all_positions',
  initialTeam = 'all_teams',
  showDetails = false
}) => {
  const [players, setPlayers] = useState<Player[]>([]);
  const [filteredPlayers, setFilteredPlayers] = useState<Player[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [position, setPosition] = useState(initialPosition);
  const [team, setTeam] = useState(initialTeam);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [teams, setTeams] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(20);

  // Fetch players from API
  const fetchPlayers = async (pageNum: number = 1) => {
    try {
      setLoading(true);
      setError(null);
      
      // Build query parameters
      const params = new URLSearchParams();
      if (position !== 'all_positions') {
        params.append('position', position);
      }
      if (team !== 'all_teams') {
        params.append('team', team);
      }
      params.append('page', pageNum.toString());
      params.append('page_size', pageSize.toString());
      
      const response = await PlayerService.getPlayers(
        position !== 'all_positions' ? position : undefined,
        team !== 'all_teams' ? team : undefined
      );
      
      // Extract players and pagination info
      if (response && response.players) {
        setPlayers(response.players);
        setFilteredPlayers(response.players);
        setTotalPages(response.pagination?.total_pages || 1);
        
        // Extract unique teams for dropdown
        const allTeams = [...new Set(response.players.map((p: Player) => p.team))];
        setTeams(allTeams.sort());
      }
    } catch (error) {
      Logger.error('Error fetching players:', error);
      setError('Failed to load players. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle player search
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    
    // If query is less than 2 characters, show all players
    if (query.length < 2) {
      setFilteredPlayers(players);
      return;
    }
    
    // Search players by name
    const searchResults = players.filter(player =>
      player.name.toLowerCase().includes(query.toLowerCase())
    );
    
    setFilteredPlayers(searchResults);
  };
  
  // Handle position filter change
  const handlePositionChange = (pos: string) => {
    setPosition(pos);
    setPage(1); // Reset to first page
  };
  
  // Handle team filter change
  const handleTeamChange = (tm: string) => {
    setTeam(tm);
    setPage(1); // Reset to first page
  };
  
  // Handle pagination
  const goToPage = (pageNum: number) => {
    if (pageNum < 1 || pageNum > totalPages) return;
    setPage(pageNum);
  };

  // Fetch players when filters change
  useEffect(() => {
    fetchPlayers(page);
  }, [position, team, page, pageSize]);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Select Player</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col space-y-4">
          {/* Search and filters */}
          <div className="flex space-x-2">
            <Input 
              placeholder="Search players..." 
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="flex-1"
            />
            
            <Select value={position} onValueChange={handlePositionChange}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Position" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all_positions">All</SelectItem>
                <SelectItem value="QB">QB</SelectItem>
                <SelectItem value="RB">RB</SelectItem>
                <SelectItem value="WR">WR</SelectItem>
                <SelectItem value="TE">TE</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={team} onValueChange={handleTeamChange}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Team" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all_teams">All Teams</SelectItem>
                {teams.map(t => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Player list */}
          <ScrollArea className="h-[400px]">
            {loading ? (
              <div className="flex justify-center py-4">Loading players...</div>
            ) : error ? (
              <div className="text-red-500 py-4">{error}</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Player</TableHead>
                    <TableHead>Position</TableHead>
                    <TableHead>Team</TableHead>
                    {showDetails && <TableHead>Status</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPlayers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={showDetails ? 4 : 3} className="text-center py-4">
                        No players found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredPlayers.map(player => (
                      <TableRow 
                        key={player.player_id}
                        className="cursor-pointer hover:bg-secondary/50"
                        onClick={() => onSelect && onSelect(player.player_id)}
                      >
                        <TableCell>{player.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{player.position}</Badge>
                        </TableCell>
                        <TableCell>{player.team}</TableCell>
                        {showDetails && (
                          <TableCell>
                            <Badge 
                              variant={player.status === 'Active' ? 'default' : 
                                player.status === 'Rookie' ? 'secondary' : 'destructive'}
                            >
                              {player.status || 'Active'}
                            </Badge>
                          </TableCell>
                        )}
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </ScrollArea>
          
          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center py-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
              >
                Previous
              </Button>
              
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => goToPage(page + 1)}
                disabled={page >= totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default PlayerSelect;