import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { MapPin, TrendingUp, DollarSign, Star, AlertCircle, CheckCircle2 } from 'lucide-react';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { colors } from '@/lib/utils';

interface SiteRankerProps {
  zoneId: string;
}

interface SiteCandidate {
  siteId: string;
  name: string;
  zoneId: string;
  location: [number, number];
  demandScore: number;
  growthScore: number;
  accessibilityScore: number;
  infrastructureScore: number;
  gridCapacityScore: number;
  costScore: number;
  totalScore: number;
  redFlags: string[];
  recommendation: string;
  paybackYears?: number;
  utilizationRate?: number;
}

export function SiteRanker({ zoneId }: SiteRankerProps) {
  const [sites, setSites] = useState<SiteCandidate[]>([]);
  const [weights, setWeights] = useState({
    demand: 30,
    growth: 20,
    accessibility: 15,
    infrastructure: 15,
    gridCapacity: 10,
    cost: 10,
  });

  // Generate synthetic site candidates
  useEffect(() => {
    const generateSites = () => {
      const candidates: SiteCandidate[] = [
        {
          siteId: 'S001',
          name: 'Whitefield Tech Park',
          zoneId: 'Z01',
          location: [12.9698, 77.7499],
          demandScore: 0.85,
          growthScore: 0.75,
          accessibilityScore: 0.90,
          infrastructureScore: 0.95,
          gridCapacityScore: 0.15,
          costScore: 0.20,
          totalScore: 0.82,
          redFlags: ['Low grid headroom'],
          recommendation: 'HIGH_PRIORITY',
          paybackYears: 2.5,
          utilizationRate: 0.85,
        },
        {
          siteId: 'S002',
          name: 'HSR Bus Depot',
          zoneId: 'Z02',
          location: [12.9138, 77.6374],
          demandScore: 0.72,
          growthScore: 0.68,
          accessibilityScore: 0.85,
          infrastructureScore: 0.90,
          gridCapacityScore: 0.30,
          costScore: 0.25,
          totalScore: 0.76,
          redFlags: [],
          recommendation: 'RECOMMENDED',
          paybackYears: 3.2,
          utilizationRate: 0.78,
        },
        {
          siteId: 'S003',
          name: 'Indiranagar Metro Hub',
          zoneId: 'Z03',
          location: [12.9740, 77.6408],
          demandScore: 0.68,
          growthScore: 0.72,
          accessibilityScore: 0.95,
          infrastructureScore: 0.88,
          gridCapacityScore: 0.30,
          costScore: 0.30,
          totalScore: 0.71,
          redFlags: ['High installation cost'],
          recommendation: 'RECOMMENDED',
          paybackYears: 4.1,
          utilizationRate: 0.72,
        },
        {
          siteId: 'S004',
          name: 'Koramangala Mall',
          zoneId: 'Z04',
          location: [12.9350, 77.6200],
          demandScore: 0.55,
          growthScore: 0.60,
          accessibilityScore: 0.92,
          infrastructureScore: 0.85,
          gridCapacityScore: 0.35,
          costScore: 0.40,
          totalScore: 0.62,
          redFlags: ['Low demand'],
          recommendation: 'CONSIDER',
          paybackYears: 5.8,
          utilizationRate: 0.65,
        },
        {
          siteId: 'S005',
          name: 'Electronic City Tech Park',
          zoneId: 'Z05',
          location: [12.8350, 77.6080],
          demandScore: 0.78,
          growthScore: 0.82,
          accessibilityScore: 0.88,
          infrastructureScore: 0.92,
          gridCapacityScore: 0.42,
          costScore: 0.15,
          totalScore: 0.79,
          redFlags: [],
          recommendation: 'HIGH_PRIORITY',
          paybackYears: 2.1,
          utilizationRate: 0.91,
        },
        {
          siteId: 'S006',
          name: 'Marathahalli Industrial',
          zoneId: 'Z06',
          location: [12.9080, 77.5700],
          demandScore: 0.48,
          growthScore: 0.55,
          accessibilityScore: 0.75,
          infrastructureScore: 0.80,
          gridCapacityScore: 0.38,
          costScore: 0.35,
          totalScore: 0.59,
          redFlags: ['Low demand', 'High cost'],
          recommendation: 'CONSIDER',
          paybackYears: 6.8,
          utilizationRate: 0.58,
        },
      ];

      setSites(candidates);
    };

    generateSites();
  }, [zoneId]);

  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation) {
      case 'HIGH_PRIORITY': return colors.success;
      case 'RECOMMENDED': return colors.info;
      case 'CONSIDER': return colors.warning;
      case 'LOW_PRIORITY': return colors.muted;
      case 'NOT_RECOMMENDED': return colors.danger;
      default: return colors.info;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return colors.success;
    if (score >= 0.6) return colors.info;
    if (score >= 0.4) return colors.warning;
    return colors.muted;
  };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">MCDA Site Ranker</h3>
        <Badge variant="outline" className="text-xs">{zoneId}</Badge>
      </div>

      {/* Weight Controls */}
      <div className="space-y-4 mb-6">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-foreground">Scoring Weights</span>
          <Button size="sm" variant="outline" className="text-xs">
            Reset
          </Button>
        </div>

        <div className="space-y-3">
          {Object.entries(weights).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground capitalize">{key}</span>
              <Slider
                value={[value]}
                max={100}
                step={5}
                className="flex-1 mx-3"
                onValueChange={(v) => setWeights({ ...weights, [key]: v[0] })}
              />
              <span className="text-xs font-mono text-foreground">{value}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Site Ranking Table */}
      <div className="rounded-lg border border-border/50 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="text-xs font-medium text-muted-foreground">Rank</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground">Site</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground">Zone</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground">Score</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground">Status</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground">Payback</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground">Utilization</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sites.map((site, index) => (
              <TableRow key={site.siteId} className="hover:bg-muted/5">
                <TableCell className="font-medium">{index + 1}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-primary" />
                    <span className="text-sm font-medium">{site.name}</span>
                  </div>
                </TableCell>
                <TableCell>{site.zoneId}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        style={{ width: `${site.totalScore * 100}%`, backgroundColor: getScoreColor(site.totalScore) }}
                        className="h-full rounded-full"
                      />
                    </div>
                    <span className="text-xs font-mono">{site.totalScore.toFixed(2)}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge className="text-xs" style={{ backgroundColor: getRecommendationColor(site.recommendation) + '33', color: getRecommendationColor(site.recommendation) }}>
                    {site.recommendation.replace('_', ' ')}
                  </Badge>
                </TableCell>
                <TableCell>
                  <span className="text-xs font-mono">{site.paybackYears?.toFixed(1)}y</span>
                </TableCell>
                <TableCell>
                  <span className="text-xs font-mono">{formatPercent(site.utilizationRate || 0)}</span>
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    {site.redFlags.length === 0 ? (
                      <CheckCircle2 className="h-4 w-4 text-success" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-danger" />
                    )}
                    {site.redFlags.length > 0 && (
                      <span className="text-xs text-muted-foreground">({site.redFlags.length} flags)</span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <Button size="sm" variant="outline" className="text-xs">
                    Details
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between mt-4">
        <div className="text-xs text-muted-foreground">
          {sites.length} sites ranked
        </div>
        <Button size="sm">
          <MapPin className="h-4 w-4 mr-1" />
          Export Rankings
        </Button>
      </div>
    </Card>
  );
}
