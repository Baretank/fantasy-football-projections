import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';

const PlayerSelect = () => {
  const [players, setPlayers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    // Fetch players from API
    const fetchPlayers = async () => {
      try {
        const response = await fetch('/api/players');
        const data = await response.json();
        setPlayers(data);
      } catch (error) {
        console.error('Error fetching players:', error);
      }
    };
    
    fetchPlayers();
  }, []);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Select Player</CardTitle>
      </CardHeader>
      <CardContent>
        <Input 
          placeholder="Search players..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="mb-4"
        />
        <ScrollArea className="h-[300px]">
          {/* Player list implementation */}
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default PlayerSelect;