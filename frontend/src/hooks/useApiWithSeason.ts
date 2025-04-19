import { useCallback } from 'react';
import { useSeason } from '@/context/SeasonContext';
import { 
  PlayerService as PlayerServiceOriginal,
  ProjectionService as ProjectionServiceOriginal,
  ScenarioService as ScenarioServiceOriginal,
  OverrideService,
  DraftService
} from '@/services/api';

/**
 * Hook that provides the original API services enhanced with automatic season context injection
 * This ensures all API calls automatically use the current season from the context
 */
export function useApiWithSeason() {
  const { season } = useSeason();
  
  // Enhanced player service that injects the current season
  const PlayerService = {
    ...PlayerServiceOriginal,
    
    // Override methods that need season
    getPlayerStats: useCallback((playerId: string) => {
      return PlayerServiceOriginal.getPlayerStats(playerId, season);
    }, [season])
  };
  
  // Enhanced projection service that injects the current season
  const ProjectionService = {
    ...ProjectionServiceOriginal,
    
    // Override getPlayerProjections to include season by default
    getPlayerProjections: useCallback((playerId: string, scenarioId?: string) => {
      return ProjectionServiceOriginal.getPlayerProjections(playerId, scenarioId, season);
    }, [season]),
    
    // Override createBaseProjection to use current season by default
    createBaseProjection: useCallback((playerId: string, scenarioId?: string) => {
      return ProjectionServiceOriginal.createBaseProjection(playerId, season, scenarioId);
    }, [season]),
    
    // Override applyTeamAdjustments to use current season by default
    applyTeamAdjustments: useCallback((
      team: string, 
      adjustments: Record<string, number>,
      scenarioId?: string,
      playerShares?: Record<string, Record<string, number>>
    ) => {
      return ProjectionServiceOriginal.applyTeamAdjustments(team, season, adjustments, scenarioId, playerShares);
    }, [season]),
    
    // Other season-dependent methods
    getTeamStats: useCallback((team: string) => {
      return ProjectionServiceOriginal.getTeamStats(team, season);
    }, [season]),
    
    getTeamUsage: useCallback((team: string) => {
      return ProjectionServiceOriginal.getTeamUsage(team, season);
    }, [season]),
    
    createRookieProjections: useCallback((scenarioId?: string) => {
      return ProjectionServiceOriginal.createRookieProjections(season, scenarioId);
    }, [season]),
    
    enhanceRookieProjection: useCallback((
      playerId: string,
      compLevel: string = 'medium',
      playingTimePct: number = 0.5
    ) => {
      return ProjectionServiceOriginal.enhanceRookieProjection(playerId, season, compLevel, playingTimePct);
    }, [season]),
    
    createDraftBasedRookieProjection: useCallback((
      playerId: string,
      draftPosition: number,
      scenarioId?: string
    ) => {
      return ProjectionServiceOriginal.createDraftBasedRookieProjection(playerId, draftPosition, season, scenarioId);
    }, [season])
  };

  // Return the enhanced services
  return {
    PlayerService,
    ProjectionService,
    ScenarioService: ScenarioServiceOriginal,
    OverrideService,
    DraftService
  };
}

export default useApiWithSeason;