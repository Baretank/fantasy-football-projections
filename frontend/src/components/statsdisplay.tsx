import React, { useState, useEffect } from 'react';
import { Logger } from '@/utils/logger';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Stats {
  week: number;
  attempts?: number;
  completions?: number;
  passing_yards?: number;
  passing_td?: number;
  rushing_yards?: number;
  rushing_td?: number;
  receptions?: number;
  targets?: number;
  receiving_yards?: number;
  receiving_td?: number;
}

interface StatsDisplayProps {
  playerId: string;
  position: 'QB' | 'RB' | 'WR' | 'TE';
  season: number;
}

const StatsDisplay: React.FC<StatsDisplayProps> = ({ playerId, position, season }) => {
  const [stats, setStats] = useState<Stats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState('');
  const [view, setView] = useState<'weekly' | 'trend'>('weekly');

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch(`/api/players/${playerId}/stats?season=${season}`);
        const data = await response.json();
        setStats(processStats(data.stats));
        setIsLoading(false);
      } catch (error) {
        Logger.error('Error fetching stats:', error);
        setIsLoading(false);
      }
    };

    fetchStats();
  }, [playerId, season]);

  const processStats = (rawStats: any): Stats[] => {
    // Convert API response to weekly stats array
    const weeklyStats: Stats[] = [];
    if (rawStats[season]?.weeks) {
      Object.entries(rawStats[season].weeks).forEach(([week, stats]: [string, any]) => {
        weeklyStats.push({
          week: parseInt(week),
          ...stats
        });
      });
    }
    return weeklyStats.sort((a, b) => a.week - b.week);
  };

  const getPositionMetrics = () => {
    switch (position) {
      case 'QB':
        return [
          { key: 'passing_yards', label: 'Passing Yards' },
          { key: 'passing_td', label: 'Passing TD' },
          { key: 'rushing_yards', label: 'Rushing Yards' }
        ];
      case 'RB':
        return [
          { key: 'rushing_yards', label: 'Rushing Yards' },
          { key: 'rushing_td', label: 'Rushing TD' },
          { key: 'receptions', label: 'Receptions' }
        ];
      default: // WR/TE
        return [
          { key: 'targets', label: 'Targets' },
          { key: 'receptions', label: 'Receptions' },
          { key: 'receiving_yards', label: 'Receiving Yards' }
        ];
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Player Statistics</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="weekly" className="w-full">
          <TabsList>
            <TabsTrigger value="weekly">Weekly Stats</TabsTrigger>
            <TabsTrigger value="trend">Trend Analysis</TabsTrigger>
          </TabsList>

          <TabsContent value="weekly">
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={stats}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="week" />
                  <YAxis />
                  <Tooltip />
                  {getPositionMetrics().map(metric => (
                    <Line
                      key={metric.key}
                      type="monotone"
                      dataKey={metric.key}
                      name={metric.label}
                      stroke={`#${Math.floor(Math.random()*16777215).toString(16)}`}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            <Table className="mt-4">
              <TableHeader>
                <TableRow>
                  <TableHead>Week</TableHead>
                  {getPositionMetrics().map(metric => (
                    <TableHead key={metric.key}>{metric.label}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {stats.map((stat) => (
                  <TableRow key={stat.week}>
                    <TableCell>{stat.week}</TableCell>
                    {getPositionMetrics().map(metric => (
                      <TableCell key={metric.key}>
                        {stat[metric.key as keyof Stats]}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>

          <TabsContent value="trend">
            {/* Trend analysis visualization will go here */}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};

export default StatsDisplay;