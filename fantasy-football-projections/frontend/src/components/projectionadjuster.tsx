import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const ProjectionAdjuster = () => {
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [adjustments, setAdjustments] = useState({
    snap_share: 100,
    target_share: 100,
    td_rate: 100
  });

  const handleAdjustment = (metric, value) => {
    setAdjustments(prev => ({
      ...prev,
      [metric]: value
    }));
    // This would trigger recalculation of projections
  };

  return (
    <div className="grid grid-cols-12 gap-4 p-4">
      {/* Player Selection Panel */}
      <Card className="col-span-3">
        <CardHeader>
          <CardTitle>Player Selection</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Player search/selection would go here */}
        </CardContent>
      </Card>

      {/* Adjustment Panel */}
      <Card className="col-span-5">
        <CardHeader>
          <CardTitle>Projection Adjustments</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div>
              <label className="block mb-2">Snap Share %</label>
              <Slider
                value={[adjustments.snap_share]}
                min={50}
                max={150}
                step={1}
                onValueChange={([value]) => handleAdjustment('snap_share', value)}
              />
              <div className="text-right text-sm text-gray-500">
                {adjustments.snap_share}% of baseline
              </div>
            </div>
            
            {/* Additional sliders for other metrics */}
          </div>
        </CardContent>
      </Card>

      {/* Impact Analysis Panel */}
      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Impact Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={[/* projected stats comparison */]}>
                <XAxis dataKey="week" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="baseline" stroke="#8884d8" />
                <Line type="monotone" dataKey="projected" stroke="#82ca9d" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <Table className="mt-4">
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead>Baseline</TableHead>
                <TableHead>Projected</TableHead>
                <TableHead>Δ%</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* Impact metrics would go here */}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default ProjectionAdjuster;