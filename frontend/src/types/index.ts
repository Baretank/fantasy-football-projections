// Basic types
export interface BaseEntity {
  created_at: string;
  updated_at?: string;
}

// Player types
export interface Player extends BaseEntity {
  player_id: string;
  name: string;
  team: string;
  position: string;
  
  // Enhanced player details
  date_of_birth?: string;  // ISO date string format YYYY-MM-DD
  height?: number;         // Height in inches
  weight?: number;
  status?: string;
  depth_chart_position?: string;
  
  // Draft information
  draft_position?: number;
  draft_team?: string;
  draft_round?: number;
  draft_pick?: number;
}

// Projection types
export interface Projection extends BaseEntity {
  projection_id: string;
  player_id: string;
  scenario_id?: string;
  season: number;
  games: number;
  half_ppr: number;
  
  // Basic stats
  pass_attempts?: number;
  completions?: number;
  pass_yards?: number;
  pass_td?: number;
  interceptions?: number;
  rush_attempts?: number;  // Updated from carries to match backend field name
  rush_yards?: number;
  rush_td?: number;
  targets?: number;
  receptions?: number;
  rec_yards?: number;
  rec_td?: number;
  
  // Enhanced stats
  gross_pass_yards?: number;
  sacks?: number;
  sack_yards?: number;
  net_pass_yards?: number;
  fumbles?: number;
  net_rush_yards?: number;
  
  // Efficiency metrics
  pass_td_rate?: number;
  int_rate?: number;
  sack_rate?: number;
  comp_pct?: number;
  yards_per_att?: number;
  net_yards_per_att?: number;
  fumble_rate?: number;
  rush_td_rate?: number;
  yards_per_carry?: number;
  net_yards_per_carry?: number;
  catch_pct?: number;
  yards_per_target?: number;
  rec_td_rate?: number;
  
  // Usage metrics
  snap_share?: number;
  target_share?: number;
  rush_share?: number;
  redzone_share?: number;
  pass_att_pct?: number;
  car_pct?: number;
  tar_pct?: number;
  
  // Override info
  has_overrides: boolean;
  is_fill_player: boolean;
}

// Scenario types
export interface Scenario extends BaseEntity {
  scenario_id: string;
  name: string;
  description?: string;
  is_baseline: boolean;
  base_scenario_id?: string;
}

// Override types
export interface StatOverride extends BaseEntity {
  override_id: string;
  player_id: string;
  projection_id: string;
  stat_name: string;
  calculated_value: number;
  manual_value: number;
  notes?: string;
}

// Request types
export interface AdjustmentRequest {
  adjustments: Record<string, number>;
}

export interface BatchOverrideRequest {
  player_ids: string[];
  stat_name: string;
  value: number | { method: string; amount: number };
  notes?: string;
}

export interface ScenarioComparisonRequest {
  scenario_ids: string[];
  position?: string;
}

export type DraftStatus = 'available' | 'drafted' | 'watched';

export interface DraftStatusUpdate {
  player_id: string;
  draft_status: DraftStatus;
  fantasy_team?: string;
  draft_order?: number;
  create_projection?: boolean;
}

export interface DraftBoard {
  name: string;
  description?: string;
  season?: number; 
  settings?: Record<string, any>;
  number_of_teams?: number;
  roster_spots?: number;
}

// Response types
export interface ScenarioComparisonPlayer {
  player_id: string;
  name: string;
  team: string;
  position: string;
  scenarios: Record<string, Record<string, any>>;
}

export interface ScenarioComparisonResponse {
  scenarios: { id: string; name: string }[];
  players: ScenarioComparisonPlayer[];
}

export interface BatchOverrideResult {
  player_id: string;
  success: boolean;
  message?: string;
  override_id?: string;
  old_value?: number;
  new_value?: number;
}

export interface BatchOverrideResponse {
  results: Record<string, BatchOverrideResult>;
}

export interface StatVariance {
  mean: number;
  stddev: number;
  min: number;
  max: number;
  sample_size: number;
}

export interface ProjectionVarianceResponse {
  projection_id: string;
  player_id: string;
  position: string;
  variance: Record<string, StatVariance>;
}

export interface ProjectionRangeResponse {
  projection_id: string;
  player_id: string;
  position: string;
  confidence: number;
  range: Record<string, {
    low: number;
    high: number;
  }>;
  scenarios_created?: string[];
}

export interface ErrorResponse {
  detail: string;
  code?: string;
}

export interface SuccessResponse {
  status: string;
  message?: string;
  data?: Record<string, any>;
}

// Position-specific stat groups
export const QB_STATS = {
  passing: ['pass_attempts', 'completions', 'pass_yards', 'pass_td', 'interceptions', 'sacks'],
  rushing: ['rush_attempts', 'rush_yards', 'rush_td', 'fumbles'],
  efficiency: ['comp_pct', 'yards_per_att', 'net_yards_per_att', 'pass_td_rate', 'int_rate', 'sack_rate']
};

export const RB_STATS = {
  rushing: ['rush_attempts', 'rush_yards', 'rush_td', 'fumbles'],
  receiving: ['targets', 'receptions', 'rec_yards', 'rec_td'],
  efficiency: ['yards_per_carry', 'net_yards_per_carry', 'rush_td_rate', 'catch_pct', 'yards_per_target']
};

export const WR_TE_STATS = {
  receiving: ['targets', 'receptions', 'rec_yards', 'rec_td'],
  rushing: ['rush_attempts', 'rush_yards', 'rush_td'],
  efficiency: ['catch_pct', 'yards_per_target', 'rec_td_rate', 'target_share']
};

// Scenario comparison stat groups
export const COMPARISON_STATS = {
  QB: ['half_ppr', 'pass_yards', 'pass_td', 'rush_yards', 'rush_td', 'interceptions'],
  RB: ['half_ppr', 'rush_yards', 'rush_td', 'receptions', 'rec_yards', 'rec_td'],
  WR: ['half_ppr', 'targets', 'receptions', 'rec_yards', 'rec_td', 'target_share'],
  TE: ['half_ppr', 'targets', 'receptions', 'rec_yards', 'rec_td', 'target_share']
};

// Stat display formats
export interface StatDisplayFormat {
  label: string;
  formatter: (value: number) => string;
  color?: (value: number) => string;
}

export const STAT_FORMATS: Record<string, StatDisplayFormat> = {
  // Fantasy points
  half_ppr: { 
    label: 'Half PPR', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0'
  },
  
  // Game info
  games: {
    label: 'Games',
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  
  // Passing stats
  pass_attempts: { 
    label: 'Pass Att', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  completions: { 
    label: 'Compl', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  pass_yards: { 
    label: 'Pass Yds', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  pass_td: { 
    label: 'Pass TD', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0'
  },
  interceptions: { 
    label: 'INT', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0'
  },
  sacks: { 
    label: 'Sacks', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0'
  },
  sack_yards: {
    label: 'Sack Yds',
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  gross_pass_yards: {
    label: 'Gross Pass',
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  net_pass_yards: {
    label: 'Net Pass',
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  
  // Rushing stats
  rush_attempts: { 
    label: 'Carries', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  rush_yards: { 
    label: 'Rush Yds', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  rush_td: { 
    label: 'Rush TD', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0'
  },
  fumbles: { 
    label: 'Fumbles', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0',
    color: (value) => value !== null && value !== undefined ? (value < 1 ? 'text-green-500' : value > 3 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  
  // Receiving stats
  targets: { 
    label: 'Targets', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  receptions: { 
    label: 'Rec', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  rec_yards: { 
    label: 'Rec Yds', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(0) : '0'
  },
  rec_td: { 
    label: 'Rec TD', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0'
  },
  
  // Efficiency metrics - Passing
  comp_pct: { 
    label: 'Comp %', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) + '%' : '0.0%',
    color: (value) => value !== null && value !== undefined ? (value > 65 ? 'text-green-500' : value < 58 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  yards_per_att: { 
    label: 'YPA', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0',
    color: (value) => value !== null && value !== undefined ? (value > 7.5 ? 'text-green-500' : value < 6.5 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  net_yards_per_att: {
    label: 'Net YPA',
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0',
    color: (value) => value !== null && value !== undefined ? (value > 7.0 ? 'text-green-500' : value < 6.0 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  pass_td_rate: { 
    label: 'Pass TD %', 
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%',
    color: (value) => value !== null && value !== undefined ? (value > 0.05 ? 'text-green-500' : value < 0.03 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  int_rate: { 
    label: 'INT %', 
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%',
    color: (value) => value !== null && value !== undefined ? (value < 0.02 ? 'text-green-500' : value > 0.035 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  sack_rate: {
    label: 'Sack %',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%',
    color: (value) => value !== null && value !== undefined ? (value < 0.05 ? 'text-green-500' : value > 0.08 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  
  // Efficiency metrics - Rushing
  yards_per_carry: { 
    label: 'YPC', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0',
    color: (value) => value !== null && value !== undefined ? (value > 4.5 ? 'text-green-500' : value < 3.5 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  net_yards_per_carry: {
    label: 'Net YPC',
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0',
    color: (value) => value !== null && value !== undefined ? (value > 4.3 ? 'text-green-500' : value < 3.3 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  rush_td_rate: {
    label: 'Rush TD %',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%',
    color: (value) => value !== null && value !== undefined ? (value > 0.04 ? 'text-green-500' : value < 0.02 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  fumble_rate: {
    label: 'Fumble %',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(2) + '%' : '0.00%',
    color: (value) => value !== null && value !== undefined ? (value < 0.01 ? 'text-green-500' : value > 0.02 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  
  // Efficiency metrics - Receiving
  catch_pct: { 
    label: 'Catch %', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) + '%' : '0.0%',
    color: (value) => value !== null && value !== undefined ? (value > 70 ? 'text-green-500' : value < 60 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  yards_per_target: { 
    label: 'YPT', 
    formatter: (value) => value !== null && value !== undefined ? value.toFixed(1) : '0.0',
    color: (value) => value !== null && value !== undefined ? (value > 8.5 ? 'text-green-500' : value < 7.0 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  rec_td_rate: {
    label: 'Rec TD %',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%',
    color: (value) => value !== null && value !== undefined ? (value > 0.09 ? 'text-green-500' : value < 0.05 ? 'text-red-500' : 'text-amber-500') : 'text-amber-500'
  },
  
  // Usage metrics
  snap_share: {
    label: 'Snap %',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%'
  },
  target_share: { 
    label: 'Tgt Share', 
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%'
  },
  rush_share: {
    label: 'Rush Share',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%'
  },
  redzone_share: {
    label: 'RZ Share',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%'
  },
  pass_att_pct: {
    label: 'Pass Att %',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%'
  },
  car_pct: {
    label: 'Car %',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%'
  },
  tar_pct: {
    label: 'Tar %',
    formatter: (value) => value !== null && value !== undefined ? (value * 100).toFixed(1) + '%' : '0.0%'
  },
  
  // Status flags
  has_overrides: {
    label: 'Overrides',
    formatter: (value) => value ? '✓' : '-'
  },
  is_fill_player: {
    label: 'Fill Player',
    formatter: (value) => value ? '✓' : '-'
  }
};