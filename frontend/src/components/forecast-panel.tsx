import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Area, AreaChart, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { RefreshCw } from 'lucide-react';
import { formatKw, formatPercent } from '@/lib/utils';
import { colors } from '@/lib/utils';

interface ForecastPanelProps {
  zoneId: string;
}

interface ForecastData {
  time: string;
  prediction: number;
  upperBound?: number;
  lowerBound?: number;
  actual?: number;
}

export function ForecastPanel({ zoneId }: ForecastPanelProps) {
  const [forecastData, setForecastData] = useState<ForecastData[]>([]);
  const [timeRange, setTimeRange] = useState<'24h' | '72h'>('24h');

  // Generate synthetic forecast data
  useEffect(() => {
    const generateForecast = () => {
      const hours = timeRange === '24h' ? 24 : 72;
      const data: ForecastData[] = [];

      for (let i = 0; i < hours; i++) {
        const hour = i % 24;
        const base = 100 + 50 * Math.sin((i * 2 * Math.PI) / 24);
        const noise = (Math.random() - 0.5) * 10;
        const prediction = base + noise;
        const upperBound = prediction * 1.1;
        const lowerBound = prediction * 0.9;

        data.push({
          time: `${hour}:00`,
          prediction,
          upperBound,
          lowerBound,
          actual: Math.random() > 0.5 ? base + noise : undefined,
        });
      }

      setForecastData(data);
    };

    generateForecast();
  }, [timeRange, zoneId]);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return colors.success;
    if (confidence >= 0.6) return colors.info;
    return colors.warning;
  };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">72-Hour Demand Forecast</h3>
        <div className="flex items-center gap-2">
          <Badge variant={timeRange === '24h' ? 'default' : 'secondary'} className="text-xs">
            {timeRange.toUpperCase()}
          </Badge>
          <Button size="sm" variant="outline" className="text-xs">
            <RefreshCw className="h-3 w-3 mr-1" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={forecastData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={colors.chart.grid} />
            <XAxis
              dataKey="time"
              tick={{ fill: colors.chart.textDim, fontSize: 10 }}
              tickLine={{ stroke: colors.border }}
              axisLine={{ stroke: colors.border }}
            />
            <YAxis
              tick={{ fill: colors.chart.textDim, fontSize: 10 }}
              tickLine={{ stroke: colors.border }}
              axisLine={{ stroke: colors.border }}
              tickFormatter={(value) => `${value}:00`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: colors.card,
                border: `1px solid ${colors.border}`,
                borderRadius: 8,
                fontSize: 11,
                padding: 8,
              }}
            />
            <Area
              type="monotone"
              dataKey="prediction"
              stroke={colors.primary}
              strokeWidth={2}
              fill={colors.primaryDim}
              fillOpacity={0.2}
            />
            <Area
              type="monotone"
              dataKey="upperBound"
              stroke={colors.info}
              strokeWidth={1}
              strokeDasharray="3 3"
              fill={colors.infoDim}
              fillOpacity={0.1}
            />
            <Area
              type="monotone"
              dataKey="lowerBound"
              stroke={colors.warning}
              strokeWidth={1}
              strokeDasharray="3 3"
              fill={colors.warningDim}
              fillOpacity={0.1}
            />
            {forecastData.some(d => d.actual) && (
              <Line
                type="monotone"
                dataKey="actual"
                stroke={colors.danger}
                strokeWidth={2}
                dot={{ fill: colors.danger }}
                name="Actual"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between mt-4">
        <div className="text-xs text-muted-foreground">
          {forecastData.length} data points
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-success" />
            <span className="text-xs text-success">80% Confidence</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-info" />
            <span className="text-xs text-info">95% Confidence</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
