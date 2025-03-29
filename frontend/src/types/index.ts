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
  carries?: number;
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
  rushing: ['carries', 'rush_yards', 'rush_td', 'fumbles'],
  efficiency: ['comp_pct', 'yards_per_att', 'net_yards_per_att', 'pass_td_rate', 'int_rate', 'sack_rate']
};

export const RB_STATS = {
  rushing: ['carries', 'rush_yards', 'rush_td', 'fumbles'],
  receiving: ['targets', 'receptions', 'rec_yards', 'rec_td'],
  efficiency: ['yards_per_carry', 'net_yards_per_carry', 'rush_td_rate', 'catch_pct', 'yards_per_target']
};

export const WR_TE_STATS = {
  receiving: ['targets', 'receptions', 'rec_yards', 'rec_td'],
  rushing: ['carries', 'rush_yards', 'rush_td'],
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
  half_ppr: { 
    label: 'Half PPR', 
    formatter: (value) => value.toFixed(1) 
  },
  pass_attempts: { 
    label: 'Pass Att', 
    formatter: (value) => value.toFixed(0) 
  },
  completions: { 
    label: 'Completions', 
    formatter: (value) => value.toFixed(0) 
  },
  pass_yards: { 
    label: 'Pass Yards', 
    formatter: (value) => value.toFixed(0) 
  },
  pass_td: { 
    label: 'Pass TD', 
    formatter: (value) => value.toFixed(1) 
  },
  interceptions: { 
    label: 'INT', 
    formatter: (value) => value.toFixed(1) 
  },
  carries: { 
    label: 'Carries', 
    formatter: (value) => value.toFixed(0) 
  },
  rush_yards: { 
    label: 'Rush Yards', 
    formatter: (value) => value.toFixed(0) 
  },
  rush_td: { 
    label: 'Rush TD', 
    formatter: (value) => value.toFixed(1) 
  },
  targets: { 
    label: 'Targets', 
    formatter: (value) => value.toFixed(0) 
  },
  receptions: { 
    label: 'Receptions', 
    formatter: (value) => value.toFixed(0) 
  },
  rec_yards: { 
    label: 'Rec Yards', 
    formatter: (value) => value.toFixed(0) 
  },
  rec_td: { 
    label: 'Rec TD', 
    formatter: (value) => value.toFixed(1) 
  },
  comp_pct: { 
    label: 'Comp %', 
    formatter: (value) => (value * 100).toFixed(1) + '%',
    color: (value) => value > 0.65 ? 'text-green-500' : value < 0.58 ? 'text-red-500' : 'text-amber-500'
  },
  yards_per_att: { 
    label: 'YPA', 
    formatter: (value) => value.toFixed(1),
    color: (value) => value > 7.5 ? 'text-green-500' : value < 6.5 ? 'text-red-500' : 'text-amber-500'
  },
  pass_td_rate: { 
    label: 'TD %', 
    formatter: (value) => (value * 100).toFixed(1) + '%',
    color: (value) => value > 0.05 ? 'text-green-500' : value < 0.03 ? 'text-red-500' : 'text-amber-500'
  },
  int_rate: { 
    label: 'INT %', 
    formatter: (value) => (value * 100).toFixed(1) + '%',
    color: (value) => value < 0.02 ? 'text-green-500' : value > 0.035 ? 'text-red-500' : 'text-amber-500'
  },
  yards_per_carry: { 
    label: 'YPC', 
    formatter: (value) => value.toFixed(1),
    color: (value) => value > 4.5 ? 'text-green-500' : value < 3.5 ? 'text-red-500' : 'text-amber-500'
  },
  catch_pct: { 
    label: 'Catch %', 
    formatter: (value) => (value * 100).toFixed(1) + '%',
    color: (value) => value > 0.7 ? 'text-green-500' : value < 0.6 ? 'text-red-500' : 'text-amber-500'
  },
  yards_per_target: { 
    label: 'YPT', 
    formatter: (value) => value.toFixed(1),
    color: (value) => value > 8.5 ? 'text-green-500' : value < 7.0 ? 'text-red-500' : 'text-amber-500'
  },
  target_share: { 
    label: 'Tgt Share', 
    formatter: (value) => (value * 100).toFixed(1) + '%' 
  },
  fumbles: { 
    label: 'Fumbles', 
    formatter: (value) => value.toFixed(1) 
  },
  sacks: { 
    label: 'Sacks', 
    formatter: (value) => value.toFixed(1) 
  }
};