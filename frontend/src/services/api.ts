import { 
  Player,
  Projection, 
  Scenario,
  StatOverride,
  AdjustmentRequest,
  BatchOverrideRequest
} from '@/types/index';

const API_BASE_URL = 'http://localhost:8000/api';

// Helper function for API requests
async function fetchApi(
  endpoint: string, 
  method: string = 'GET', 
  body: any = null
): Promise<any> {
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (body && (method === 'POST' || method === 'PUT')) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'An error occurred');
  }
  
  return response.json();
}

// Player services
export const PlayerService = {
  async getPlayers(position?: string, team?: string): Promise<Player[]> {
    let endpoint = '/players';
    const params = new URLSearchParams();
    
    if (position) params.append('position', position);
    if (team) params.append('team', team);
    
    const queryString = params.toString();
    if (queryString) endpoint += `?${queryString}`;
    
    return fetchApi(endpoint);
  },

  async getPlayer(playerId: string): Promise<Player> {
    return fetchApi(`/players/${playerId}`);
  },

  async getPlayerStats(playerId: string, season?: number): Promise<any> {
    let endpoint = `/players/${playerId}/stats`;
    if (season) endpoint += `?season=${season}`;
    
    return fetchApi(endpoint);
  }
};

// Projection services
export const ProjectionService = {
  async getPlayerProjections(
    playerId: string, 
    scenarioId?: string
  ): Promise<Projection[]> {
    let endpoint = `/projections/player/${playerId}`;
    if (scenarioId) endpoint += `?scenario_id=${scenarioId}`;
    
    return fetchApi(endpoint);
  },

  async createBaseProjection(
    playerId: string, 
    season: number
  ): Promise<Projection> {
    return fetchApi(
      `/projections/player/${playerId}/base?season=${season}`, 
      'POST'
    );
  },

  async updateProjection(
    projectionId: string, 
    adjustments: Record<string, number>
  ): Promise<Projection> {
    return fetchApi(
      `/projections/${projectionId}`, 
      'PUT', 
      { adjustments }
    );
  },

  async applyTeamAdjustments(
    team: string, 
    season: number, 
    adjustments: Record<string, number>
  ): Promise<any> {
    return fetchApi(
      `/projections/team/${team}/adjustments?season=${season}`, 
      'PUT', 
      { adjustments }
    );
  }
};

// Scenario services
export const ScenarioService = {
  async getScenarios(): Promise<Scenario[]> {
    return fetchApi('/scenarios');
  },

  async getScenario(scenarioId: string): Promise<Scenario> {
    return fetchApi(`/scenarios/${scenarioId}`);
  },

  async createScenario(
    name: string, 
    description?: string, 
    isBaseline: boolean = false
  ): Promise<Scenario> {
    return fetchApi(
      '/scenarios', 
      'POST', 
      { name, description, is_baseline: isBaseline }
    );
  },

  async getScenarioProjections(
    scenarioId: string, 
    position?: string, 
    team?: string
  ): Promise<Projection[]> {
    let endpoint = `/scenarios/${scenarioId}/projections`;
    const params = new URLSearchParams();
    
    if (position) params.append('position', position);
    if (team) params.append('team', team);
    
    const queryString = params.toString();
    if (queryString) endpoint += `?${queryString}`;
    
    return fetchApi(endpoint);
  },

  async cloneScenario(
    scenarioId: string, 
    name: string, 
    description?: string
  ): Promise<Scenario> {
    return fetchApi(
      `/scenarios/${scenarioId}/clone?name=${encodeURIComponent(name)}` + 
      (description ? `&description=${encodeURIComponent(description)}` : ''), 
      'POST'
    );
  },

  async deleteScenario(scenarioId: string): Promise<void> {
    return fetchApi(`/scenarios/${scenarioId}`, 'DELETE');
  },

  async compareScenarios(
    scenarioIds: string[], 
    position?: string
  ): Promise<any> {
    return fetchApi(
      '/scenarios/compare', 
      'POST', 
      { scenario_ids: scenarioIds, position }
    );
  }
};

// Override services
export const OverrideService = {
  async createOverride(
    playerId: string, 
    projectionId: string, 
    statName: string, 
    manualValue: number, 
    notes?: string
  ): Promise<StatOverride> {
    return fetchApi(
      '/overrides', 
      'POST', 
      {
        player_id: playerId,
        projection_id: projectionId,
        stat_name: statName,
        manual_value: manualValue,
        notes
      }
    );
  },

  async getPlayerOverrides(playerId: string): Promise<StatOverride[]> {
    return fetchApi(`/overrides/player/${playerId}`);
  },

  async getProjectionOverrides(projectionId: string): Promise<StatOverride[]> {
    return fetchApi(`/overrides/projection/${projectionId}`);
  },

  async deleteOverride(overrideId: string): Promise<void> {
    return fetchApi(`/overrides/${overrideId}`, 'DELETE');
  },

  async batchOverride(
    playerIds: string[], 
    statName: string, 
    value: number | { method: string, amount: number }, 
    notes?: string
  ): Promise<any> {
    return fetchApi(
      '/overrides/batch', 
      'POST', 
      {
        player_ids: playerIds,
        stat_name: statName,
        value,
        notes
      }
    );
  }
};

// Export all services
export default {
  PlayerService,
  ProjectionService,
  ScenarioService,
  OverrideService
};