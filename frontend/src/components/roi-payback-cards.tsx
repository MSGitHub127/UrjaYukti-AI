import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, DollarSign, Activity, ArrowUpRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { colors } from '@/lib/utils';

interface ROIPaybackCardsProps {
  zoneId: string;
}

interface ROIMetric {
  label: string;
  value: number;
  target: number;
  color: string;
  trend: 'up' | 'down' | 'stable';
  icon: React.ReactNode;
}

export function ROIPaybackCards({ zoneId }: ROIPaybackCardsProps) {
  const [metrics, setMetrics] = useState<ROIMetric[]>([
    { label: 'Total Savings', value: 12500000, target: 10000000, color: colors.primary, trend: 'up', icon: <DollarSign className="h-4 w-4" /> },
    { label: 'Payback Period', value: 2.5, target: 3.0, color: colors.info, trend: 'down', icon: <ArrowUpRight className="h-4 w-4" /> },
    { label: 'Utilization Rate', value: 0.85, target: 0.80, color: colors.success, trend: 'up', icon: <Activity className="h-4 w-4" /> },
    { label: 'NPV', value: 450000, target: 400000, color: colors.primary, trend: 'up', icon: <TrendingUp className="h-4 w-4" /> },
  ]);

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">ROI & Payback Analysis</h3>
        <Badge variant="outline" className="text-xs">{zoneId}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {metrics.map((metric) => (
          <Card key={metric.label} className="p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {metric.icon}
                <span className="text-xs text-muted-foreground">{metric.label}</span>
              </div>
              <div className={`text-2xl font-bold text-foreground ${metric.color === colors.success ? 'text-green-500' : ''}`}>
                {metric.label === 'Payback Period' ? `${metric.value.toFixed(1)}y` : metric.label === 'Utilization Rate' ? formatPercent(metric.value) : formatCurrency(metric.value)}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className={`text-xs text-muted-foreground`}>Target: {metric.label === 'Payback Period' ? `${metric.target.toFixed(1)}y` : metric.label === 'Utilization Rate' ? formatPercent(metric.target) : formatCurrency(metric.target)}</span>
              <div className={`text-xs font-mono ${metric.value >= metric.target ? 'text-green-500' : 'text-red-500'}`}>
                {metric.value >= metric.target ? '✓' : '✗'}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${metric.trend === 'up' ? 'bg-green-500' : metric.trend === 'down' ? 'bg-red-500' : 'bg-muted'}`} />
              <span className={`text-xs font-mono ${metric.trend === 'up' ? 'text-green-500' : metric.trend === 'down' ? 'text-red-500' : 'text-muted-foreground'}`}>
                {metric.trend === 'up' ? '↑' : metric.trend === 'down' ? '↓' : '→'} {Math.abs((metric.value - metric.target) / metric.target * 100).toFixed(1)}%
              </span>
            </div>
          </Card>
        ))}
      </div>

      {/* Summary Card */}
      <Card className="p-3 mt-4">
        <div className="text-xs text-muted-foreground mb-2">Total ROI</div>
        <div className="text-2xl font-bold text-foreground">
          {formatCurrency(metrics.reduce((sum, m) => sum + m.value, 0))}
        </div>
        <div className="text-xs text-muted-foreground">
          {metrics.reduce((sum, m) => sum + m.value, 0) >= 0 ? 'Profitable' : 'Loss Making'}
        </div>
      </Card>
    </Card>
  );
}
