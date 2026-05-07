import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { TrendingUp, DollarSign, Activity, CheckCircle2, AlertCircle, RefreshCw, Zap } from 'lucide-react';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { colors } from '@/lib/utils';

interface ComplianceProbabilityProps {
  zoneId: string;
}

export function ComplianceProbability({ zoneId }: ComplianceProbabilityProps) {
  const [complianceRate, setComplianceRate] = useState(0.65);
  const [trend, setTrend] = useState<'increasing' | 'decreasing' | 'stable'>('increasing');
  const [targetRate, setTargetRate] = useState(0.75);

  const getTrendColor = () => {
    switch (trend) {
      case 'increasing': return colors.success;
      case 'decreasing': return colors.danger;
      case 'stable': return colors.info;
      default: return colors.muted;
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'increasing': return <TrendingUp className="h-4 w-4" />;
      case 'decreasing': return <Activity className="h-4 w-4" />;
      case 'stable': return <CheckCircle2 className="h-4 w-4" />;
      default: return <Activity className="h-4 w-4" />;
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">Compliance Probability</h3>
        <Badge variant="outline" className="text-xs">{zoneId}</Badge>
      </div>

      {/* Compliance Rate */}
      <div className="space-y-4">
        <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-border/50">
          <div className="flex items-center gap-2">
            <div className="flex-shrink-0">
              <div className={`w-2 h-2 rounded-full ${getTrendColor()}`} />
            </div>
            <span className="text-xs text-muted-foreground">Current Rate</span>
          </div>
          <div className="text-2xl font-bold text-foreground">{formatPercent(complianceRate)}</div>
        </div>

        <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-border/50">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Target Rate</span>
            <span className="text-xs font-mono text-foreground">{formatPercent(targetRate)}</span>
          </div>
          <div className="text-2xl font-bold text-foreground">{formatPercent(targetRate)}</div>
        </div>

        <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-border/50">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Gap to Target</span>
            <span className={`text-xs font-mono ${complianceRate >= targetRate ? 'text-green-500' : 'text-red-500'}`}>
              {complianceRate >= targetRate ? 'On Track' : 'Behind'}
            </span>
          </div>
          <div className="text-2xl font-bold text-foreground">
            {Math.abs(complianceRate - targetRate) >= 0.01 ? 'On Track' : 'Behind'}
          </div>
        </div>
      </div>

      {/* Trend Indicator */}
      <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-border/50">
        <div className="flex items-center gap-2">
          {getTrendIcon()}
          <span className="text-xs text-muted-foreground">Trend</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${getTrendColor()}`}>
            {trend.charAt(0).toUpperCase() + trend.slice(1)}
          </span>
        </div>
      </div>

      {/* Historical Data */}
      <div className="space-y-2">
        <div className="text-xs text-muted-foreground mb-2">7-Day History</div>
        <div className="space-y-1">
          {[
            { day: 1, rate: 0.58, trend: 'increasing' },
            { day: 2, rate: 0.62, trend: 'increasing' },
            { day: 3, rate: 0.65, trend: 'increasing' },
            { day: 4, rate: 0.63, trend: 'decreasing' },
            { day: 5, rate: 0.68, trend: 'increasing' },
            { day: 6, rate: 0.71, trend: 'increasing' },
            { day: 7, rate: 0.74, trend: 'increasing' },
          ].map((day) => (
            <div key={day.day} className="flex items-center justify-between p-2 bg-background/50 rounded-lg border border-border/50">
              <span className="text-xs text-muted-foreground">Day {day.day}</span>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${day.trend === 'increasing' ? 'bg-green-500' : day.trend === 'decreasing' ? 'bg-red-500' : 'bg-muted'}`} />
                <span className={`text-xs font-mono ${day.trend === 'increasing' ? 'text-green-500' : day.trend === 'decreasing' ? 'text-red-500' : 'text-muted-foreground'}`}>
                  {day.rate.toFixed(1)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-between mt-4">
        <div className="text-xs text-muted-foreground">
          {complianceRate >= targetRate ? 'On track for target' : 'Adjust strategy'}
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" className="text-xs">
            <RefreshCw className="h-3 w-3 mr-1" />
            Refresh
          </Button>
          <Button size="sm" className="text-xs bg-primary text-primary-foreground hover:bg-primary/90">
            <Zap className="h-3 w-3 mr-1" />
            Optimize
          </Button>
        </div>
      </div>
    </Card>
  );
}
