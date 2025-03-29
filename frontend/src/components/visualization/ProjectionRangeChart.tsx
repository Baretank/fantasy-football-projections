import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  ErrorBar,
  ReferenceLine,
  Label
} from 'recharts';

interface ProjectionRange {
  low: number;
  high: number;
}

interface ProjectionData {
  name: string;
  position: string;
  team: string;
  value: number;
  range: ProjectionRange;
}

interface ProjectionRangeChartProps {
  data: ProjectionData[];
  title?: string;
  yAxisLabel?: string;
  height?: number | string;
  showAverage?: boolean;
}

const ProjectionRangeChart: React.FC<ProjectionRangeChartProps> = ({
  data,
  title = "Projection Range",
  yAxisLabel = "Value",
  height = 300,
  showAverage = true
}) => {
  // Calculate average if needed
  const average = showAverage ? 
    data.reduce((sum, item) => sum + item.value, 0) / (data.length || 1) : null;

  // Format data for recharts with error bars
  const formattedData = data.map(item => ({
    name: item.name,
    position: item.position,
    team: item.team,
    value: item.value,
    errorY: [item.value - item.range.low, item.range.high - item.value]
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={formattedData}
        margin={{
          top: 20,
          right: 30,
          left: 20,
          bottom: 60
        }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          dataKey="name" 
          tick={{ fontSize: 12 }}
          interval={0}
          angle={-45}
          textAnchor="end"
        />
        <YAxis 
          label={{ 
            value: yAxisLabel, 
            angle: -90, 
            position: 'insideLeft',
            style: { textAnchor: 'middle' } 
          }} 
        />
        <Tooltip
          formatter={(value, name, props) => {
            if (name === 'value') {
              return [Number(value).toFixed(1), 'Projection'];
            }
            return [value, name];
          }}
          labelFormatter={(label) => label}
          content={({ active, payload, label }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload;
              const [lowError, highError] = data.errorY || [0, 0];
              const projValue = data.value;
              
              return (
                <div className="bg-background p-3 border shadow-sm rounded-md">
                  <p className="font-medium">{data.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {data.team} - {data.position}
                  </p>
                  <div className="space-y-1 pt-2">
                    <p className="text-primary font-medium">
                      <span className="text-muted-foreground text-xs mr-2">Projection:</span>
                      {projValue.toFixed(1)}
                    </p>
                    <p className="text-yellow-600">
                      <span className="text-muted-foreground text-xs mr-2">Low Range:</span>
                      {(projValue - lowError).toFixed(1)}
                    </p>
                    <p className="text-green-600">
                      <span className="text-muted-foreground text-xs mr-2">High Range:</span>
                      {(projValue + highError).toFixed(1)}
                    </p>
                  </div>
                </div>
              );
            }
            
            return null;
          }}
        />
        <Legend />
        
        {average !== null && (
          <ReferenceLine 
            y={average} 
            stroke="#ff7300"
            strokeDasharray="5 5"
          >
            <Label 
              value={`Avg: ${average.toFixed(1)}`} 
              position="insideBottomRight"
              fill="#ff7300"
            />
          </ReferenceLine>
        )}
        
        <Bar 
          dataKey="value" 
          fill="#8884d8" 
          name="Projection"
          isAnimationActive={true}
        >
          <ErrorBar 
            dataKey="errorY" 
            width={4} 
            strokeWidth={2}
            stroke="#ff7300" 
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default ProjectionRangeChart;