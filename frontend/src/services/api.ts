import { 
  Player,
  Projection, 
  Scenario,
  StatOverride,
  AdjustmentRequest,
  BatchOverrideRequest,
  DraftStatusUpdate,
  DraftBoard
} from '@/types/index';
import { Logger } from '@/utils/logger';

// Using Vite proxy configuration from vite.config.ts
const API_BASE_URL = '/api';

// Helper function for API requests
async function fetchApi(
  endpoint: string, 
  method: string = 'GET', 
  body: any = null
): Promise<any> {
  // Ensure endpoint starts with a slash
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${normalizedEndpoint}`;
  
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
    // Add credentials for CORS requests
    credentials: 'include',
  };

  if (body && (method === 'POST' || method === 'PUT')) {
    options.body = JSON.stringify(body);
  }

  try {
    Logger.debug(`API Request: ${method} ${url}`);
    if (body) Logger.debug('Request body:', body);
    
    // Add debug info about the URL
    Logger.debug(`Full request URL: ${new URL(url, window.location.origin).href}`);
    
    const response = await fetch(url, options);
    Logger.debug(`Response status: ${response.status}, ok: ${response.ok}`);
    
    if (!response.ok) {
      // Try to parse error response
      try {
        // Log the raw response text for debugging
        const responseText = await response.text();
        Logger.error(`Error response text:`, responseText);
        
        let errorData;
        try {
          errorData = JSON.parse(responseText);
        } catch (parseError) {
          Logger.error(`Could not parse error response as JSON:`, parseError);
          throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        
        Logger.error(`API Error (${response.status}):`, errorData);
        throw new Error(errorData.detail || `API Error: ${response.status} ${response.statusText}`);
      } catch (e) {
        // If error response isn't valid JSON or can't be read
        Logger.error(`API Error (${response.status}): Could not parse response`, e);
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }
    }
    
    const responseText = await response.text();
    Logger.debug(`Raw response:`, responseText.substring(0, 100) + (responseText.length > 100 ? '...' : ''));
    
    // Parse as JSON if there's content, otherwise return empty object
    const data = responseText ? JSON.parse(responseText) : {};
    Logger.debug(`API Response: ${method} ${normalizedEndpoint}`, data);
    return data;
  } catch (error) {
    Logger.error(`API Request Failed: ${method} ${normalizedEndpoint}`, error);
    // Rethrow the error for the caller to handle
    throw error;
  }
}

// Player services
export const PlayerService = {
  async getPlayers(position?: string, team?: string, status?: string, season?: number): Promise<any> {
    let endpoint = '/players';
    const params = new URLSearchParams();
    
    if (position) params.append('position', position);
    if (team) params.append('team', team);
    
    // Only append status if provided - database uses different status codes
    if (status) params.append('status', status);
    
    // Add season for filtering - this is critical for proper season-aware filtering
    // of active players (historical vs current seasons)
    if (season) params.append('season', season.toString());
    
    // Request players with a reasonable limit
    params.append('page', '1');
    params.append('page_size', '2000'); // Set a reasonable limit that should capture all relevant players
    
    // Do NOT use team_filter - there might be a bug in the backend implementation
    // params.append('team_filter', 'true');
    
    const queryString = params.toString();
    if (queryString) endpoint += `?${queryString}`;
    
    Logger.debug(`PlayerService.getPlayers: Fetching from ${endpoint}`);
    try {
      const response = await fetchApi(endpoint);
      Logger.debug(`PlayerService.getPlayers: Response structure:`, 
        response && typeof response === 'object' 
          ? Object.keys(response) 
          : typeof response);
      
      // This API endpoint returns { players: [...], pagination: {...} }
      if (response && typeof response === 'object' && Array.isArray(response.players)) {
        return response.players;
      } 
      
      // If the response is already an array, return it
      if (Array.isArray(response)) {
        return response;
      }
      
      // Return empty array as fallback to maintain consistent return type
      Logger.warn("Response from players endpoint is not in expected format, returning empty array");
      return [];
    } catch (error) {
      Logger.error(`PlayerService.getPlayers error:`, error);
      // Return empty array instead of an object to maintain consistent return type
      return [];
    }
  },
  
  async getRookies(position?: string, team?: string): Promise<Player[]> {
    // Build the query parameters
    const params = new URLSearchParams();
    if (position && position !== 'all_positions') params.append('position', position);
    if (team && team !== 'all_teams') params.append('team', team);
    
    // Simplify the endpoint construction
    const queryString = params.toString();
    const endpoint = `/players/rookies${queryString ? `?${queryString}` : ''}`;
    
    Logger.debug(`Fetching rookies with endpoint: ${endpoint}`);
    try {
      const response = await fetchApi(endpoint);
      Logger.debug(`getRookies: Response structure:`, 
        response && typeof response === 'object' 
          ? Object.keys(response) 
          : typeof response);
      
      // Check if response has an array structure, similar to getPlayers
      if (response && typeof response === 'object' && Array.isArray(response.players)) {
        return response.players;
      } 
      
      // If the response is already an array, return it
      if (Array.isArray(response)) {
        return response;
      }
      
      // Return empty array as fallback to prevent "rookies is not iterable" error
      Logger.warn("Response from rookies endpoint is not in expected format, returning empty array");
      return [];
    } catch (error) {
      Logger.error(`Error fetching rookies from ${endpoint}:`, error);
      // Return empty array instead of throwing, which is consistent with getPlayers
      return [];
    }
  },

  async getPlayer(playerId: string): Promise<Player> {
    return fetchApi(`/players/${playerId}`);
  },

  async getPlayerStats(playerId: string, season?: number): Promise<any> {
    let endpoint = `/players/${playerId}/stats`;
    if (season) endpoint += `?season=${season}`;
    
    return fetchApi(endpoint);
  },
  
  async getPlayersOverview(season?: number): Promise<Player[]> {
    try {
      Logger.info("------- STARTING getPlayersOverview ---------");
      
      // Use the regular getPlayers method with season filtering
      // If season is not provided, use the current context season
      Logger.debug(`Fetching all players for season: ${season || 'default'}`);
      
      // Instead of building the endpoint manually, use the getPlayers method
      // which properly adds the season parameter and uses the correct filters
      const allPlayersResponse = await this.getPlayers(undefined, undefined, undefined, season);
      
      // Inspect the response structure more closely
      if (allPlayersResponse) {
        if (typeof allPlayersResponse === 'object') {
          Logger.debug("Response is an object. Keys:", Object.keys(allPlayersResponse));
          
          if (allPlayersResponse.players) {
            Logger.debug(`Found players array with ${allPlayersResponse.players.length} items`);
            
            if (allPlayersResponse.players.length > 0) {
              Logger.debug("First player:", allPlayersResponse.players[0]);
            }
            
            // Filter for fantasy-relevant positions client-side
            const fantasyPositions = ['QB', 'RB', 'WR', 'TE'];
            const relevantPlayers = allPlayersResponse.players.filter(
              (p: any) => p && p.position && fantasyPositions.includes(p.position)
            );
            
            Logger.info(`Filtered to ${relevantPlayers.length} fantasy-relevant players for season ${season || 'default'}`);
            return relevantPlayers;
          }
        }
        
        if (Array.isArray(allPlayersResponse)) {
          Logger.debug(`Response is directly an array with ${allPlayersResponse.length} items`);
          
          if (allPlayersResponse.length > 0) {
            Logger.debug("First player:", allPlayersResponse[0]);
          }
          
          // Filter for fantasy-relevant positions client-side
          const fantasyPositions = ['QB', 'RB', 'WR', 'TE'];
          const relevantPlayers = allPlayersResponse.filter(
            (p: any) => p && p.position && fantasyPositions.includes(p.position)
          );
          
          Logger.info(`Filtered to ${relevantPlayers.length} fantasy-relevant players for season ${season || 'default'}`);
          return relevantPlayers;
        }
      }
      
      Logger.error("Unexpected response format, returning empty array");
      return [];
    } catch (error) {
      Logger.error(`PlayerService.getPlayersOverview error:`, error);
      return [];
    }
  }
};

// Projection services
export const ProjectionService = {
  async getPlayerProjections(
    playerId: string, 
    scenarioId?: string,
    season?: number
  ): Promise<Projection[]> {
    if (!playerId) {
      Logger.error("getPlayerProjections called with empty playerId");
      return [];
    }
    
    let endpoint = `/projections`;
    const params = new URLSearchParams();
    
    if (playerId) params.append('player_id', playerId);
    if (scenarioId) params.append('scenario_id', scenarioId);
    if (season) params.append('season', season.toString());
    
    const queryString = params.toString();
    if (queryString) endpoint += `?${queryString}`;
    
    Logger.debug(`ProjectionService: Requesting projections for player ${playerId}${scenarioId ? ` in scenario ${scenarioId}` : ''}`);
    const result = await fetchApi(endpoint);
    Logger.debug(`ProjectionService: Received ${Array.isArray(result) ? result.length : 0} projections for player ${playerId}`);
    
    // Return empty array if result is not an array
    if (!Array.isArray(result)) {
      Logger.error(`Unexpected response format for projections, expected array but got:`, typeof result);
      return [];
    }
    
    return result;
  },

  async createBaseProjection(
    playerId: string, 
    season: number,
    scenarioId?: string
  ): Promise<Projection> {
    return fetchApi(
      `/projections/create`, 
      'POST',
      {
        player_id: playerId,
        season: season,
        scenario_id: scenarioId
      }
    );
  },

  async updateProjection(
    projectionId: string, 
    adjustments: Record<string, number>
  ): Promise<Projection> {
    return fetchApi(
      `/projections/${projectionId}/adjust`, 
      'POST', 
      { adjustments }
    );
  },

  async applyTeamAdjustments(
    team: string, 
    season: number, 
    adjustments: Record<string, number>,
    scenarioId?: string,
    playerShares?: Record<string, Record<string, number>>
  ): Promise<any> {
    let endpoint = `/projections/team/${team}/adjust?season=${season}`;
    if (scenarioId) endpoint += `&scenario_id=${scenarioId}`;
    
    return fetchApi(
      endpoint, 
      'PUT', 
      { 
        adjustments,
        player_shares: playerShares
      }
    );
  },
  
  async getProjectionRange(
    projectionId: string,
    confidence: number = 0.80,
    createScenarios: boolean = false
  ): Promise<any> {
    return fetchApi(
      `/projections/${projectionId}/range?confidence=${confidence}&create_scenarios=${createScenarios}`
    );
  },
  
  async getProjectionVariance(
    projectionId: string,
    useHistorical: boolean = true
  ): Promise<any> {
    return fetchApi(
      `/projections/${projectionId}/variance?use_historical=${useHistorical}`
    );
  },
  
  async getTeamStats(
    team: string,
    season: number
  ): Promise<any> {
    return fetchApi(
      `/projections/team/${team}/stats?season=${season}`
    );
  },
  
  async getTeamUsage(
    team: string,
    season: number
  ): Promise<any> {
    return fetchApi(
      `/projections/team/${team}/usage?season=${season}`
    );
  },
  
  async createRookieProjections(
    season: number,
    scenarioId?: string
  ): Promise<any> {
    let endpoint = `/projections/rookies/create?season=${season}`;
    if (scenarioId) endpoint += `&scenario_id=${scenarioId}`;
    
    return fetchApi(endpoint, 'POST');
  },
  
  async enhanceRookieProjection(
    playerId: string,
    season: number,
    compLevel: string = 'medium',
    playingTimePct: number = 0.5
  ): Promise<any> {
    return fetchApi(
      `/projections/rookies/${playerId}/enhance?comp_level=${compLevel}&playing_time_pct=${playingTimePct}&season=${season}`,
      'PUT'
    );
  },
  
  async createDraftBasedRookieProjection(
    playerId: string,
    draftPosition: number,
    season: number,
    scenarioId?: string
  ): Promise<any> {
    let endpoint = `/projections/rookies/draft-based?player_id=${playerId}&draft_position=${draftPosition}&season=${season}`;
    if (scenarioId) endpoint += `&scenario_id=${scenarioId}`;
    
    return fetchApi(endpoint, 'POST');
  }
};

// Scenario services
export const ScenarioService = {
  async getScenarios(): Promise<Scenario[]> {
    try {
      Logger.debug("ScenarioService: Requesting scenarios from /scenarios");
      const result = await fetchApi('/scenarios');
      Logger.debug("ScenarioService: Received response:", result);
      return result;
    } catch (error) {
      Logger.error("ScenarioService.getScenarios error:", error);
      throw error;
    }
  },

  async getScenario(scenarioId: string): Promise<Scenario> {
    try {
      Logger.debug(`ScenarioService: Requesting scenario ${scenarioId}`);
      return fetchApi(`/scenarios/${scenarioId}`);
    } catch (error) {
      Logger.error("ScenarioService.getScenario error:", error);
      throw error;
    }
  },

  async createScenario(
    name: string, 
    description?: string, 
    isBaseline: boolean = false
  ): Promise<Scenario> {
    try {
      Logger.debug(`ScenarioService: Creating scenario "${name}"`);
      return fetchApi(
        '/scenarios', 
        'POST', 
        { name, description, is_baseline: isBaseline }
      );
    } catch (error) {
      Logger.error("ScenarioService.createScenario error:", error);
      throw error;
    }
  },

  async getScenarioProjections(
    scenarioId: string, 
    position?: string, 
    team?: string
  ): Promise<Projection[]> {
    try {
      if (!scenarioId) {
        Logger.error("getScenarioProjections called with empty scenarioId");
        return [];
      }
      
      let endpoint = `/scenarios/${scenarioId}/projections`;
      const params = new URLSearchParams();
      
      if (position) params.append('position', position);
      if (team) params.append('team', team);
      
      const queryString = params.toString();
      if (queryString) endpoint += `?${queryString}`;
      
      Logger.debug(`ScenarioService: Requesting projections for scenario ${scenarioId} with position=${position || 'all'}`);
      const result = await fetchApi(endpoint);
      Logger.debug(`ScenarioService: Received ${Array.isArray(result) ? result.length : 0} projections for scenario ${scenarioId}, position=${position || 'all'}`);
      
      // Return empty array if result is not an array
      if (!Array.isArray(result)) {
        Logger.error(`Unexpected response format for projections, expected array but got:`, typeof result);
        return [];
      }
      
      return result;
    } catch (error) {
      Logger.error("ScenarioService.getScenarioProjections error:", error);
      throw error;
    }
  },

  async cloneScenario(
    scenarioId: string, 
    name: string, 
    description?: string
  ): Promise<Scenario> {
    try {
      Logger.debug(`ScenarioService: Cloning scenario ${scenarioId} as "${name}"`);
      return fetchApi(
        `/scenarios/${scenarioId}/clone?name=${encodeURIComponent(name)}` + 
        (description ? `&description=${encodeURIComponent(description)}` : ''), 
        'POST'
      );
    } catch (error) {
      Logger.error("ScenarioService.cloneScenario error:", error);
      throw error;
    }
  },

  async deleteScenario(scenarioId: string): Promise<void> {
    try {
      Logger.debug(`ScenarioService: Deleting scenario ${scenarioId}`);
      return fetchApi(`/scenarios/${scenarioId}`, 'DELETE');
    } catch (error) {
      Logger.error("ScenarioService.deleteScenario error:", error);
      throw error;
    }
  },

  async compareScenarios(
    scenarioIds: string[], 
    position?: string
  ): Promise<any> {
    try {
      Logger.debug(`ScenarioService: Comparing scenarios`, scenarioIds);
      return fetchApi(
        '/scenarios/compare', 
        'POST', 
        { scenario_ids: scenarioIds, position }
      );
    } catch (error) {
      Logger.error("ScenarioService.compareScenarios error:", error);
      throw error;
    }
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

// Draft services
export const DraftService = {
  async getDraftBoard(
    status?: string, 
    position?: string, 
    team?: string,
    orderBy: string = 'ranking',
    limit: number = 100,
    offset: number = 0
  ): Promise<any> {
    let endpoint = '/draft/draft-board';
    const params = new URLSearchParams();
    
    if (status) params.append('status', status);
    if (position) params.append('position', position);
    if (team) params.append('team', team);
    params.append('order_by', orderBy);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());
    
    const queryString = params.toString();
    if (queryString) endpoint += `?${queryString}`;
    
    return fetchApi(endpoint);
  },

  async updateDraftStatus(
    update: DraftStatusUpdate
  ): Promise<any> {
    return fetchApi(
      '/draft/draft-status', 
      'POST', 
      update
    );
  },

  async batchUpdateDraftStatus(
    updates: DraftStatusUpdate[]
  ): Promise<any> {
    return fetchApi(
      '/draft/batch-draft-status', 
      'POST', 
      { updates }
    );
  },

  async resetDraft(): Promise<any> {
    return fetchApi('/draft/reset-draft', 'POST');
  },

  async undoLastDraftPick(): Promise<any> {
    return fetchApi('/draft/undo-draft', 'POST');
  },

  async getDraftProgress(): Promise<any> {
    return fetchApi('/draft/draft-progress');
  },

  async createDraftBoard(board: DraftBoard): Promise<any> {
    return fetchApi('/draft/draft-boards', 'POST', board);
  },

  async getDraftBoards(activeOnly: boolean = true): Promise<any> {
    return fetchApi(`/draft/draft-boards?active_only=${activeOnly}`);
  },

  async getRookieProjectionTemplate(
    position: string, 
    draftRound?: number
  ): Promise<any> {
    let endpoint = `/draft/rookie-projection-template/${position}`;
    if (draftRound) endpoint += `?draft_round=${draftRound}`;
    
    return fetchApi(endpoint);
  },
  
  async updateRookieDraftStatus(
    playerId: string,
    team: string,
    draftPosition: number,
    round?: number,
    pick?: number,
    autoProject: boolean = true
  ): Promise<any> {
    // This uses the /api/players/rookies/{player_id}/draft endpoint
    // which is defined in the players_router, not the draft_router
    return fetchApi(
      `/players/rookies/${playerId}/draft`,
      'PUT',
      {
        team,
        draft_position: draftPosition,
        round,
        pick,
        auto_project: autoProject
      }
    );
  }
};

// Export all services
export default {
  PlayerService,
  ProjectionService,
  ScenarioService,
  OverrideService,
  DraftService
};