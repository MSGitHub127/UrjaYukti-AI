import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowRight, Activity, TrendingUp, Zap, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { formatKw, formatPercent } from '@/lib/utils';
import { colors } from '@/lib/utils';

interface CrossZoneViewProps {
  zoneId: string;
}

interface ZoneTransfer {
  fromZoneId: string;
  toZoneId: string;
  transferKw: number;
  transferEfficiency: number;
  reason: string;
  timestamp: string;
}

export function CrossZoneView({ zoneId }: CrossZoneViewProps) {
  const [transfers, setTransfers] = useState<ZoneTransfer[]>([]);
  const [totalTransferred, setTotalTransferred] = useState(0);

  // Generate synthetic transfer data
  useEffect(() => {
    const generateTransfers = () => {
      const syntheticTransfers: ZoneTransfer[] = [
        {
          fromZoneId: 'Z01',
          toZoneId: 'Z05',
          transferKw: 8500,
          transferEfficiency: 0.95,
          reason: 'Primary corridor load balancing',
          timestamp: new Date().toISOString(),
        },
        {
          fromZoneId: 'Z01',
          toZoneId: 'Z06',
          transferKw: 5200,
          transferEfficiency: 0.92,
          reason: 'Secondary corridor load balancing',
          timestamp: new Date().toISOString(),
        },
        {
          fromZoneId: 'Z02',
          toZoneId: 'Z03',
          transferKw: 4800,
          transferEfficiency: 0.88,
          reason: 'Adjacent zone load sharing',
          timestamp: new Date().toISOString(),
        },
        {
          fromZoneId: 'Z05',
          toZoneId: 'Z06',
          transferKw: 7300,
          transferEfficiency: 0.93,
          reason: 'Industrial park load sharing',
          timestamp: new Date().toISOString(),
        },
      ];

      setTransfers(syntheticTransfers);
      setTotalTransferred(syntheticTransfers.reduce((sum, t) => sum + t.transferKw, 0));
    };

    generateTransfers();
  }, [zoneId]);

  const getTransferColor = (efficiency: number) => {
    if (efficiency >= 0.95) return colors.success;
    if (efficiency >= 0.85) return colors.info;
    return colors.warning;
  };

  const avgEfficiency = transfers.length > 0
    ? transfers.reduce((sum, t) => sum + t.transferEfficiency, 0) / transfers.length
    : 0;

  const zonesInvolved = new Set<string>();
  transfers.forEach(t => {
    zonesInvolved.add(t.fromZoneId);
    zonesInvolved.add(t.toZoneId);
  });

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">Cross-Zone Coordination</h3>
        <Badge variant="outline" className="text-xs">{zoneId}</Badge>
      </div>

      {/* Transfer Summary */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Total Transferred</div>
          <div className="text-2xl font-bold text-foreground">{formatKw(totalTransferred)}</div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Avg Efficiency</div>
          <div className="text-2xl font-bold text-foreground">{(avgEfficiency * 100).toFixed(1)}%</div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Active Transfers</div>
          <div className="text-2xl font-bold text-foreground">{transfers.length}</div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-muted-foreground mb-1">Zones Involved</div>
          <div className="text-2xl font-bold text-foreground">{zonesInvolved.size}</div>
        </Card>
      </div>

      {/* Transfer List */}
      <div className="space-y-2">
        {transfers.map((transfer, index) => (
          <div
            key={`${transfer.fromZoneId}-${transfer.toZoneId}-${index}`}
            className="flex items-center justify-between p-3 bg-background/50 rounded-lg border border-border/50 hover:border-border/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                transfer.transferEfficiency >= 0.95 ? 'bg-teal' : 'bg-muted'
              }`}>
                {transfer.transferEfficiency >= 0.95 ? (
                  <ArrowUpRight className="h-4 w-4 text-teal" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 text-muted" />
                )}
              </div>
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-foreground mb-1">
                {transfer.fromZoneId} → {transfer.toZoneId}
              </div>
              <div className="text-xs text-muted-foreground">
                {formatKw(transfer.transferKw)} transferred at {transfer.transferEfficiency * 100}% efficiency
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs font-mono text-teal">
                {formatKw(transfer.transferKw)}
              </div>
              <div className="text-xs text-muted-foreground">
                {transfer.reason}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between mt-4">
        <div className="text-xs text-muted-foreground">
          {transfers.length} transfers completed
        </div>
        <Button size="sm">
          <Zap className="h-4 w-4 mr-1" />
          Balance Load
        </Button>
      </div>
    </Card>
  );
}
