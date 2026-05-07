import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Clock, ArrowUpRight, ArrowDownRight, Zap, TrendingUp } from 'lucide-react';
import { formatKw, formatPercent, formatCurrency } from '@/lib/utils';
import { colors } from '@/lib/utils';

interface VPPPanelProps {
  zoneId: string;
}

interface ScheduleResult {
  sessionId: string;
  zoneId: string;
  originalStartHour: number;
  scheduledStartHour: number;
  shiftHours: number;
  energyKwh: number;
  powerKw: number;
  complianceProbability: number;
  incentiveAmount: number;
}

export function VPPPanel({ zoneId }: VPPPanelProps) {
  const [scheduleResults, setScheduleResults] = useState<ScheduleResult[]>([]);
  const [useCompliance, setUseCompliance] = useState(true);
  const [complianceProbability, setComplianceProbability] = useState(0.65);
  const [incentiveRate, setIncentiveRate] = useState(2.0);

  // Generate synthetic schedule results
  useEffect(() => {
    const generateSchedule = () => {
      const results: ScheduleResult[] = [
        { sessionId: 'S001', zoneId, originalStartHour: 18, scheduledStartHour: 20, shiftHours: 2, energyKwh: 25, powerKw: 7.2, complianceProbability: 0.6, incentiveAmount: 50 },
        { sessionId: 'S002', zoneId, originalStartHour: 19, scheduledStartHour: 21, shiftHours: 2, energyKwh: 30, powerKw: 7.2, complianceProbability: 0.5, incentiveAmount: 60 },
        { sessionId: 'S003', zoneId, originalStartHour: 20, scheduledStartHour: 22, shiftHours: 2, energyKwh: 35, powerKw: 7.2, complianceProbability: 0.7, incentiveAmount: 70 },
        { sessionId: 'S004', zoneId, originalStartHour: 21, scheduledStartHour: 23, shiftHours: 2, energyKwh: 28, powerKw: 7.2, complianceProbability: 0.8, incentiveAmount: 40 },
        { sessionId: 'S005', zoneId, originalStartHour: 18, scheduledStartHour: 20, shiftHours: 2, energyKwh: 22, powerKw: 7.2, complianceProbability: 0.4, incentiveAmount: 30 },
      ];

      setScheduleResults(results);
    };

    generateSchedule();
  }, [zoneId]);

  const totalShiftedEnergy = scheduleResults.reduce((sum, r) => sum + r.energyKwh, 0);
  const totalIncentive = scheduleResults.reduce((sum, r) => sum + r.incentiveAmount, 0);
  const avgShiftHours = scheduleResults.length > 0 ? scheduleResults.reduce((sum, r) => sum + r.shiftHours, 0) / scheduleResults.length : 0;

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">VPP Optimizer</h3>
        <Badge variant="outline" className="text-xs">{zoneId}</Badge>
      </div>

      <div className="space-y-4">
        {/* Optimization Controls */}
        <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-border/50">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Use Compliance Model</span>
            <Switch
              checked={useCompliance}
              onCheckedChange={setUseCompliance}
              className="scale-90"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Compliance Probability</span>
            <span className="text-xs font-mono text-foreground">{(100 * complianceProbability).toFixed(0)}%</span>
          </div>
        </div>

        <div className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-border/50">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Incentive Rate</span>
            <span className="text-xs font-mono text-foreground">₹{incentiveRate}/kWh</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Target Peak Reduction</span>
            <span className="text-xs font-mono text-foreground">≥15%</span>
          </div>
        </div>

        {/* Schedule Results */}
        <div className="space-y-2">
          {scheduleResults.map((result) => (
            <div
              key={result.sessionId}
              className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-border/50 hover:border-border/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0">
                  <div className={`w-8 h-8 rounded-full ${
                    result.shiftHours > 0 ? 'bg-teal' : 'bg-muted'
                  } flex items-center justify-center`}>
                    {result.shiftHours > 0 ? (
                      <ArrowUpRight className="h-4 w-4 text-teal" />
                    ) : (
                      <ArrowDownRight className="h-4 w-4 text-muted" />
                    )}
                  </div>
                </div>
                <div className="flex-1">
                  <div className="text-xs text-muted-foreground mb-1">Session {result.sessionId}</div>
                  <div className="text-sm font-medium text-foreground">
                    {result.originalStartHour}:00 → {result.scheduledStartHour}:00
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {result.shiftHours > 0 ? `Shifted ${result.shiftHours}h` : 'No shift'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-muted-foreground mb-1">{result.energyKwh} kWh</div>
                  <div className="text-xs font-mono text-teal">
                    {result.complianceProbability > 0.7 ? 'High compliance' : 'Low compliance'}
                  </div>
                  {result.incentiveAmount > 0 && (
                    <div className="text-xs font-mono text-teal">
                      +₹{result.incentiveAmount}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-4 gap-4 mt-4">
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Total Shifted Energy</div>
          <div className="text-xl font-bold text-foreground">{formatKw(totalShiftedEnergy)}</div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Total Incentive</div>
          <div className="text-xl font-bold text-foreground">{formatCurrency(totalIncentive)}</div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Avg Shift Hours</div>
          <div className="text-xl font-bold text-foreground">{avgShiftHours.toFixed(1)}h</div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Peak Reduction</div>
          <div className="text-xl font-bold text-foreground">18%</div>
        </Card>
      </div>

      <div className="flex items-center justify-between mt-4">
        <div className="text-xs text-muted-foreground">
          {scheduleResults.length} sessions optimized
        </div>
        <Button size="sm">
          <Zap className="h-4 w-4 mr-1" />
          Optimize
        </Button>
      </div>
    </Card>
  );
}
