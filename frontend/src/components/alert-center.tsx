import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertTriangle, CheckCircle2, Clock, AlertCircle, XCircle, Bell, Activity } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';
import { colors } from '@/lib/utils';

interface AlertCenterProps {
  zoneId: string;
}

interface Alert {
  id: string;
  zoneId: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  type: 'ANOMALY' | 'OVERLOAD' | 'INFRASTRUCTURE';
  message: string;
  timestamp: string;
  acknowledged: boolean;
  resolvedAt?: string;
  metadata?: Record<string, any>;
}

export function AlertCenter({ zoneId }: AlertCenterProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');

  // Generate synthetic alerts
  useEffect(() => {
    const generateAlerts = () => {
      const syntheticAlerts: Alert[] = [
        {
          id: 'A001',
          zoneId: 'Z01',
          severity: 'CRITICAL',
          type: 'OVERLOAD',
          message: 'Zone 7 transformer at 92% capacity. Immediate intervention required.',
          timestamp: new Date().toISOString(),
          acknowledged: false,
          metadata: { currentLoadKw: 46000, capacityKw: 50000 },
        },
        {
          id: 'A002',
          zoneId: 'Z01',
          severity: 'HIGH',
          type: 'ANOMALY',
          message: 'Demand deviation +2.3σ from forecast. Model retraining recommended.',
          timestamp: new Date().toISOString(),
          acknowledged: false,
          metadata: { forecastDeviation: 2.3, model: 'TFT' },
        },
        {
          id: 'A003',
          zoneId: 'Z02',
          severity: 'MEDIUM',
          type: 'ANOMALY',
          message: 'Compliance probability dropped below 50%. Review incentive strategy.',
          timestamp: new Date().toISOString(),
          acknowledged: false,
          metadata: { complianceRate: 0.48, previousRate: 0.72 },
        },
        {
          id: 'A004',
          zoneId: 'Z03',
          severity: 'LOW',
          type: 'INFRASTRUCTURE',
          message: 'Grid headroom dropping below 15%. Consider infrastructure upgrade.',
          timestamp: new Date().toISOString(),
          acknowledged: false,
          metadata: { headroomPercent: 0.12, previous: 0.25 },
        },
        {
          id: 'A005',
          zoneId: 'Z05',
          severity: 'HIGH',
          type: 'OVERLOAD',
          message: 'Zone 5 transformer at 58% capacity. Load shifting recommended.',
          timestamp: new Date().toISOString(),
          acknowledged: false,
          metadata: { currentLoadKw: 26100, capacityKw: 45000 },
        },
      ];

      setAlerts(syntheticAlerts);
    };

    generateAlerts();
  }, [zoneId]);

  const filteredAlerts = alerts.filter(alert => {
    if (filter === 'all') return true;
    return alert.severity === filter.toUpperCase();
  });

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return colors.danger;
      case 'HIGH': return colors.warning;
      case 'MEDIUM': return colors.info;
      case 'LOW': return colors.success;
      default: return colors.muted;
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return <AlertTriangle className="h-4 w-4" />;
      case 'HIGH': return <AlertTriangle className="h-4 w-4" />;
      case 'MEDIUM': return <AlertCircle className="h-4 w-4" />;
      case 'LOW': return <CheckCircle2 className="h-4 w-4" />;
      default: return <AlertCircle className="h-4 w-4" />;
    }
  };

  const acknowledgeAlert = (alertId: string) => {
    setAlerts(prev => prev.map(a =>
      a.id === alertId ? { ...a, acknowledged: true } : a
    ));
  };

  const resolveAlert = (alertId: string) => {
    setAlerts(prev => prev.map(a =>
      a.id === alertId ? { ...a, resolvedAt: new Date().toISOString() } : a
    ));
  };

  const getSeverityCount = () => {
    return {
      critical: alerts.filter(a => a.severity === 'CRITICAL').length,
      high: alerts.filter(a => a.severity === 'HIGH').length,
      medium: alerts.filter(a => a.severity === 'MEDIUM').length,
      low: alerts.filter(a => a.severity === 'LOW').length,
    };
  };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">Alert Center</h3>
        <Badge variant="outline" className="text-xs">{zoneId}</Badge>
      </div>

      {/* Severity Filters */}
      <div className="flex items-center gap-2 mb-4">
        {['all', 'critical', 'high', 'medium', 'low'].map((severity) => (
          <button
            key={severity}
            onClick={() => setFilter(severity as any)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              filter === severity ? 'bg-primary/20 text-primary border border-primary/50' : 'hover:bg-muted/10 text-muted-foreground'
            }`}
          >
            {severity.charAt(0).toUpperCase() + severity.slice(1)}
          </button>
        ))}
      </div>

      {/* Alert List */}
      <div className="space-y-2">
        {filteredAlerts.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            No alerts for this zone
          </div>
        ) : (
          <ScrollArea className="h-[400px] pr-2">
            {filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-3 rounded-lg border border-border/50 bg-background/50 hover:border-border/50 transition-colors ${
                  alert.acknowledged ? 'opacity-50' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    alert.acknowledged ? 'bg-muted' : getSeverityColor(alert.severity)
                  }`}>
                    {getSeverityIcon(alert.severity)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-foreground">{alert.message}</span>
                      <Badge className="text-xs" style={{ backgroundColor: getSeverityColor(alert.severity) + '33', color: getSeverityColor(alert.severity) }}>
                        {alert.severity}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDateTime(alert.timestamp)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    {alert.acknowledged ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => resolveAlert(alert.id)}
                        className="text-xs"
                      >
                        Resolve
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => acknowledgeAlert(alert.id)}
                        className="text-xs"
                      >
                        Acknowledge
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </ScrollArea>
        )}
      </div>

      {/* Summary */}
      <div className="flex items-center justify-between mt-4">
        <div className="text-xs text-muted-foreground">
          {filteredAlerts.length} alerts
        </div>
        <div className="flex items-center gap-4">
          {Object.entries(getSeverityCount()).map(([severity, count]) => (
            <div key={severity} className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${getSeverityColor(severity)}`} />
              <span className="text-xs text-muted-foreground">{severity}: {count}</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
