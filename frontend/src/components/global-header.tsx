import { useState, useEffect } from 'react';
import { formatDateTime, formatKw, formatPercent } from '@/lib/utils';
import { colors, getZoneColor, getStatusBadgeStyle } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Activity, AlertTriangle, CheckCircle2, Zap, TrendingUp, Clock, Globe, Server, Database, AlertCircle } from 'lucide-react';

interface GlobalHeaderProps {
  environment: 'live' | 'mock';
  onEnvironmentChange: (env: 'live' | 'mock') => void;
}

export function GlobalHeader({ environment, onEnvironmentChange }: GlobalHeaderProps) {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [gridStatus, setGridStatus] = useState<'operational' | 'degraded' | 'maintenance'>('operational');

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex items-center justify-between px-6 py-3 border-b border-border/50 bg-background/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <span className="text-sm font-medium text-foreground">UrjaYukti AI</span>
        </div>
        <div className="h-px w-px bg-border" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Environment:</span>
          <Switch
            checked={environment === 'live'}
            onCheckedChange={(checked) => onEnvironmentChange(checked ? 'live' : 'mock')}
            className="scale-90"
          />
          <Badge variant={environment === 'live' ? 'default' : 'secondary'} className="text-xs">
            {environment === 'live' ? 'LIVE' : 'MOCK'}
          </Badge>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${gridStatus === 'operational' ? 'bg-primary animate-pulse' : 'bg-muted'}`} />
          <span className="text-sm font-medium text-foreground">Grid Status:</span>
        </div>
        <Badge variant={gridStatus === 'operational' ? 'default' : 'secondary'} className="text-xs">
          {gridStatus.toUpperCase()}
        </Badge>
        <div className="text-xs text-muted-foreground">
          {currentTime.toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
