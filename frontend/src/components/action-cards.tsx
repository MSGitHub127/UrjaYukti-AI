'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Zap, AlertTriangle, CheckCircle2, ChevronRight, Clock, TrendingUp, Building2, ArrowRight } from 'lucide-react';

export interface ActionCard {
  id: string;
  type: 'SCHEDULE_SHIFT' | 'INFRASTRUCTURE' | 'CROSS_ZONE' | 'ALERT_RESPONSE';
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  impact: string;
  estimatedBenefit?: string;
  deadline?: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'REJECTED';
  actions: {
    primary: string;
    secondary?: string;
  };
}

interface ActionCardsProps {
  actions: ActionCard[];
  onExecute?: (actionId: string) => void;
  onApprove?: (actionId: string) => void;
  onDismiss?: (actionId: string) => void;
}

export function ActionCards({ actions, onExecute, onApprove, onDismiss }: ActionCardsProps) {
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'CRITICAL': return 'bg-rose-500/20 text-rose-400 border-rose-500/50';
      case 'HIGH': return 'bg-amber-500/20 text-amber-400 border-amber-500/50';
      case 'MEDIUM': return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/50';
      case 'LOW': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
      default: return 'bg-muted/20 text-muted-foreground border-border/50';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'SCHEDULE_SHIFT': return <Zap className="h-4 w-4" />;
      case 'INFRASTRUCTURE': return <Building2 className="h-4 w-4" />;
      case 'CROSS_ZONE': return <ArrowRight className="h-4 w-4" />;
      case 'ALERT_RESPONSE': return <AlertTriangle className="h-4 w-4" />;
      default: return <CheckCircle2 className="h-4 w-4" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING': return <Badge variant="outline" className="text-xs">Pending</Badge>;
      case 'IN_PROGRESS': return <Badge className="bg-cyan-500/20 text-cyan-400 text-xs">In Progress</Badge>;
      case 'COMPLETED': return <Badge className="bg-emerald-500/20 text-emerald-400 text-xs">Completed</Badge>;
      case 'REJECTED': return <Badge variant="outline" className="text-xs text-muted-foreground">Rejected</Badge>;
      default: return <Badge variant="outline" className="text-xs">{status}</Badge>;
    }
  };

  const pendingActions = actions.filter(a => a.status === 'PENDING');
  const completedActions = actions.filter(a => a.status === 'COMPLETED');

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground">AI Recommendations</h3>
          {pendingActions.length > 0 && (
            <Badge variant="outline" className="text-xs">
              {pendingActions.length} pending
            </Badge>
          )}
        </div>
        <Button variant="ghost" size="sm" className="text-xs">
          View All
          <ChevronRight className="h-3 w-3 ml-1" />
        </Button>
      </div>

      {pendingActions.length > 0 ? (
        <div className="space-y-3">
          {pendingActions.map((action) => (
            <Card
              key={action.id}
              className={`p-4 glass-card transition-all hover:border-primary/50 ${
                expandedCard === action.id ? 'border-primary/50' : ''
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`flex-shrink-0 w-10 h-10 rounded-lg ${getPriorityColor(action.priority)} flex items-center justify-center`}>
                  {getTypeIcon(action.type)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <h4 className="text-sm font-medium text-foreground mb-1">{action.title}</h4>
                      <p className="text-xs text-muted-foreground line-clamp-2">{action.description}</p>
                    </div>
                    {getStatusBadge(action.status)}
                  </div>

                  <div className="flex items-center gap-4 mb-3">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <TrendingUp className="h-3 w-3" />
                      <span>{action.impact}</span>
                    </div>
                    {action.estimatedBenefit && (
                      <div className="flex items-center gap-1 text-xs text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" />
                        <span>{action.estimatedBenefit}</span>
                      </div>
                    )}
                    {action.deadline && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{action.deadline}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="text-xs h-8"
                      onClick={() => onExecute?.(action.id)}
                    >
                      {action.actions.primary}
                    </Button>
                    {action.actions.secondary && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-xs h-8"
                        onClick={() => onApprove?.(action.id)}
                      >
                        {action.actions.secondary}
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-xs h-8 ml-auto"
                      onClick={() => onDismiss?.(action.id)}
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-6 glass-card">
          <div className="text-center">
            <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">All actions completed</p>
          </div>
        </Card>
      )}

      {completedActions.length > 0 && (
        <div className="pt-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-muted-foreground w-full"
            onClick={() => setExpandedCard(expandedCard === 'completed' ? null : 'completed')}
          >
            {completedActions.length} completed action{completedActions.length > 1 ? 's' : ''}
            <ChevronRight className={`h-3 w-3 ml-1 transition-transform ${
              expandedCard === 'completed' ? 'rotate-90' : ''
            }`} />
          </Button>
        </div>
      )}
    </div>
  );
}
