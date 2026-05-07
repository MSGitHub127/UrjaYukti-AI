// Zone types
export interface Zone {
  id: string;
  name: string;
  status: 'SAFE' | 'CAUTION' | 'CRITICAL' | 'OVERLOADED';
  currentLoadKw: number;
  capacityKw: number;
  headroomKw: number;
  headroomPercent: number;
  evLoadKw: number;
  baseLoadKw: number;
  forecastPeakKw: number;
}

// Demand forecast types
export interface DemandForecast {
  time: string;
  zoneId: string;
  prediction: number;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  upperBound?: number;
  lowerBound?: number;
}

export interface DemandForecastResponse {
  zoneId: string;
  forecasts: DemandForecast[];
  metrics: {
    mape: number;
    rmse: number;
    driftDetected: boolean;
  };
}

// VPP scheduling types
export interface ChargingSession {
  sessionId: string;
  userId: string;
  zoneId: string;
  archetypeId: string;
  preferredStartHour: number;
  preferredEndHour: number;
  energyKwh: number;
  powerKw: number;
  flexibilityHours: number;
  complianceProbability: number;
  incentiveEligible: boolean;
}

export interface ScheduleResult {
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

export interface ScheduleMetrics {
  peakLoadKw: number;
  peakLoadIndex: number;
  peakLoadReduction: number;
  avgShiftHours: number;
  totalShiftedSessions: number;
  avgComplianceProbability: number;
  totalIncentiveAmount: number;
  constraintViolations: number;
  pliTargetMet: boolean;
  plrTargetMet: boolean;
}

// Site ranking types
export interface SiteCandidate {
  siteId: string;
  name: string;
  zoneId: string;
  location: [number, number]; // [lat, lon]
  demandScore: number;
  growthScore: number;
  accessibilityScore: number;
  infrastructureScore: number;
  gridCapacityScore: number;
  costScore: number;
  totalScore: number;
  redFlags: string[];
  metadata?: Record<string, any>;
}

export interface SiteRankingResult {
  rank: number;
  siteId: string;
  name: string;
  zoneId: string;
  totalScore: number;
  dimensionScores: Record<string, number>;
  redFlags: string[];
  recommendation: 'HIGH_PRIORITY' | 'RECOMMENDED' | 'CONSIDER' | 'LOW_PRIORITY' | 'NOT_RECOMMENDED';
  paybackYears?: number;
  utilizationRate?: number;
}

// Alert types
export interface Alert {
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

// Transfer types
export interface ZoneTransfer {
  fromZoneId: string;
  toZoneId: string;
  transferKw: number;
  transferEfficiency: number;
  reason: string;
  timestamp: string;
}

// Compliance types
export interface ComplianceMetrics {
  zoneId: string;
  totalShifts: number;
  appliedShifts: number;
  ignoredShifts: number;
  failedShifts: number;
  complianceRate: number;
  incentiveEffectiveness: number;
  outcomeDistribution: Record<string, number>;
}

// ROI types
export interface ROIMetrics {
  capex: number;
  annualRevenue: number;
  annualOpex: number;
  annualProfit: number;
  paybackYears: number;
  utilizationRate: number;
  npv: number;
}

// Agent types
export interface AgentRequest {
  zoneId: string;
  requestType: 'forecast' | 'schedule' | 'site';
  inputData: Record<string, any>;
}

export interface AgentResponse {
  status: 'success' | 'error';
  zoneId: string;
  requestType: string;
  iterations: number;
  finalOutput?: string;
  demandForecast?: Record<string, any>;
  scheduleResult?: Record<string, any>;
  siteRecommendation?: Record<string, any>;
  validationResults?: Record<string, any>;
  error?: string;
}

// Action Cards types
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
