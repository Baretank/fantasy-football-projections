import React, { useState, useEffect } from 'react';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle, 
  CardDescription 
} from '@/components/ui/card';
import { 
  Table, 
  TableHeader, 
  TableBody, 
  TableHead, 
  TableRow, 
  TableCell 
} from '@/components/ui/table';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import { formatHeight, calculateAge } from '@/lib/utils';

// Define interfaces
interface Player {
  player_id: string;
  name: string;
  position: string;
  team: string;
  status: string;
  depth_chart_position: string;
  date_of_birth?: string;  // ISO date string format YYYY-MM-DD
  height?: number;         // Height in inches
  weight?: number;
  draft_position?: number;
  draft_round?: number;
  draft_pick?: number;
}


interface DraftDayToolProps {}

const DraftDayTool: React.FC<DraftDayToolProps> = () => {
  const { toast } = useToast();
  const [rookies, setRookies] = useState<Player[]>([]);
  const [filteredRookies, setFilteredRookies] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [positionFilter, setPositionFilter] = useState<string>('All');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [dirtyRookies, setDirtyRookies] = useState<Record<string, boolean>>({});
  const [savingInProgress, setSavingInProgress] = useState<Record<string, boolean>>({});
  const [draftRound, setDraftRound] = useState<number>(1);
  const [draftPick, setDraftPick] = useState<number>(1);

  const teams = [
    'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 
    'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC', 
    'LV', 'LAC', 'LAR', 'MIA', 'MIN', 'NE', 'NO', 'NYG', 
    'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS'
  ];

  useEffect(() => {
    fetchRookies();
  }, []);

  useEffect(() => {
    filterRookies();
  }, [rookies, positionFilter, searchTerm]);

  const fetchRookies = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/players/rookies');
      if (!response.ok) {
        throw new Error('Failed to fetch rookies');
      }
      const data = await response.json();
      setRookies(data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load rookies',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const filterRookies = () => {
    let filtered = [...rookies];
    
    // Apply position filter
    if (positionFilter !== 'All') {
      filtered = filtered.filter(rookie => rookie.position === positionFilter);
    }
    
    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(rookie => 
        rookie.name.toLowerCase().includes(term) || 
        rookie.position.toLowerCase().includes(term) ||
        rookie.team.toLowerCase().includes(term)
      );
    }
    
    setFilteredRookies(filtered);
  };

  const handleTeamChange = (playerId: string, team: string) => {
    setRookies(prev => 
      prev.map(rookie => 
        rookie.player_id === playerId 
          ? { ...rookie, team } 
          : rookie
      )
    );
    
    // Mark as dirty (unsaved)
    setDirtyRookies(prev => ({
      ...prev,
      [playerId]: true
    }));
  };

  const handleDraftPositionChange = (playerId: string, positionStr: string) => {
    const draftPosition = parseInt(positionStr);
    if (isNaN(draftPosition)) return;
    
    setRookies(prev => 
      prev.map(rookie => 
        rookie.player_id === playerId 
          ? { ...rookie, draft_position: draftPosition } 
          : rookie
      )
    );
    
    // Mark as dirty (unsaved)
    setDirtyRookies(prev => ({
      ...prev,
      [playerId]: true
    }));
  };

  const saveRookieDraft = async (playerId: string) => {
    const rookie = rookies.find(r => r.player_id === playerId);
    if (!rookie) return;
    
    setSavingInProgress(prev => ({ ...prev, [playerId]: true }));
    
    try {
      // Calculate overall draft position if not set
      const defaultDraftPosition = (draftRound * 32) - (32 - draftPick);
      
      const response = await fetch(`http://localhost:8000/api/players/rookies/${playerId}/draft`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          team: rookie.team,
          draft_position: rookie.draft_position || defaultDraftPosition,
          round: draftRound,
          pick: draftPick,
          auto_project: true
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update rookie');
      }
      
      const result = await response.json();
      
      // Successfully updated
      toast({
        title: 'Success',
        description: `Updated ${rookie.name} to ${rookie.team}`,
      });
      
      // Clear dirty flag
      setDirtyRookies(prev => {
        const updated = { ...prev };
        delete updated[playerId];
        return updated;
      });
      
      // Update draft position for next pick
      setDraftPick(prev => {
        if (prev < 32) {
          return prev + 1;
        } else {
          setDraftRound(r => r + 1);
          return 1;
        }
      });

      // If projection was created, show message
      if (result.projection_created) {
        toast({
          title: 'Projection Created',
          description: `Created projection for ${rookie.name} (${result.fantasy_points.toFixed(1)} points)`,
        });
      }
      
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save draft information',
        variant: 'destructive',
      });
    } finally {
      setSavingInProgress(prev => {
        const updated = { ...prev };
        delete updated[playerId];
        return updated;
      });
    }
  };

  const handleBatchUpdate = async () => {
    const dirtyIds = Object.keys(dirtyRookies);
    if (dirtyIds.length === 0) return;
    
    try {
      const updates = dirtyIds.map(id => {
        const rookie = rookies.find(r => r.player_id === id);
        return {
          player_id: id,
          team: rookie?.team,
          draft_position: rookie?.draft_position,
          status: 'Rookie'
        };
      });
      
      const response = await fetch('http://localhost:8000/api/players/batch-update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update rookies');
      }
      
      const result = await response.json();
      
      // Successfully updated
      toast({
        title: 'Success',
        description: `Updated ${result.updated_count} rookies`,
      });
      
      // Clear all dirty flags
      setDirtyRookies({});
      
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save batch updates',
        variant: 'destructive',
      });
    }
  };

  const getTeamColor = (team: string) => {
    if (team === 'FA') return 'bg-gray-200 text-gray-700';
    
    // Team-specific colors (simplified for example)
    const teamColorMap: Record<string, string> = {
      'KC': 'bg-red-600 text-white',
      'SF': 'bg-red-700 text-white',
      'DAL': 'bg-blue-700 text-white',
      'BUF': 'bg-blue-600 text-white',
      'GB': 'bg-green-600 text-white',
      'PHI': 'bg-green-700 text-white',
    };
    
    return teamColorMap[team] || 'bg-slate-600 text-white';
  };

  const getPositionColor = (position: string) => {
    switch(position) {
      case 'QB': return 'bg-green-100 text-green-800 border-green-300';
      case 'RB': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'WR': return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'TE': return 'bg-red-100 text-red-800 border-red-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">NFL Draft Day Tool</h1>
      <p className="text-gray-500 mb-6">
        Quickly update rookie team assignments during the NFL draft
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Draft Controls</CardTitle>
            <CardDescription>Current position in the draft</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium">Round</label>
                <Input 
                  type="number" 
                  min={1} 
                  max={7}
                  value={draftRound}
                  onChange={(e) => setDraftRound(parseInt(e.target.value) || 1)}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Pick</label>
                <Input 
                  type="number" 
                  min={1} 
                  max={32}
                  value={draftPick}
                  onChange={(e) => setDraftPick(parseInt(e.target.value) || 1)}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Overall</label>
                <div className="h-9 flex items-center px-3 border rounded-md text-center">
                  #{(draftRound - 1) * 32 + draftPick}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Filters</CardTitle>
            <CardDescription>Filter rookie list</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Position</label>
                <Select 
                  value={positionFilter} 
                  onValueChange={setPositionFilter}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All Positions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All Positions</SelectItem>
                    <SelectItem value="QB">QB</SelectItem>
                    <SelectItem value="RB">RB</SelectItem>
                    <SelectItem value="WR">WR</SelectItem>
                    <SelectItem value="TE">TE</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Search</label>
                <Input
                  placeholder="Search rookies..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Actions</CardTitle>
            <CardDescription>Save changes</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Button 
                onClick={handleBatchUpdate}
                disabled={Object.keys(dirtyRookies).length === 0}
                className="flex-1"
              >
                Save All Changes ({Object.keys(dirtyRookies).length})
              </Button>
              <Button 
                variant="outline" 
                onClick={fetchRookies}
                className="flex-1"
              >
                Refresh
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Position</TableHead>
              <TableHead>Age</TableHead>
              <TableHead>Height/Weight</TableHead>
              <TableHead>Team</TableHead>
              <TableHead>Draft Position</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-4">
                  Loading rookies...
                </TableCell>
              </TableRow>
            ) : filteredRookies.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-4">
                  No rookies found
                </TableCell>
              </TableRow>
            ) : (
              filteredRookies.map((rookie) => (
                <TableRow 
                  key={rookie.player_id}
                  className={dirtyRookies[rookie.player_id] ? "bg-blue-50" : ""}
                >
                  <TableCell className="font-medium">{rookie.name}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs border ${getPositionColor(rookie.position)}`}>
                      {rookie.position}
                    </span>
                  </TableCell>
                  <TableCell>
                    {calculateAge(rookie.date_of_birth)}
                  </TableCell>
                  <TableCell>
                    {formatHeight(rookie.height)} / {rookie.weight || '-'}
                  </TableCell>
                  <TableCell>
                    <Select 
                      value={rookie.team === 'FA' ? '' : rookie.team} 
                      onValueChange={(value) => handleTeamChange(rookie.player_id, value || 'FA')}
                    >
                      <SelectTrigger className="w-24">
                        <SelectValue placeholder="FA" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">FA</SelectItem>
                        {teams.map(team => (
                          <SelectItem key={team} value={team}>{team}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      className="w-20"
                      value={rookie.draft_position || ''}
                      onChange={(e) => handleDraftPositionChange(rookie.player_id, e.target.value)}
                      placeholder="#"
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant={dirtyRookies[rookie.player_id] ? "default" : "outline"}
                      onClick={() => saveRookieDraft(rookie.player_id)}
                      disabled={savingInProgress[rookie.player_id]}
                    >
                      {savingInProgress[rookie.player_id] ? 'Saving...' : 'Save'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default DraftDayTool;