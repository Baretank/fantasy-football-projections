from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import pandas as pd
import logging
import uuid
from datetime import datetime

from backend.database.models import Player, TeamStat, Projection

logger = logging.getLogger(__name__)

class TeamStatService:
    """Service for managing team-level statistics and adjustments."""
    
    def __init__(self, db: Session):
        self.db = db
        self.position_groups = {
            'QB': ['QB'],
            'RB': ['RB'],
            'WR': ['WR'],
            'TE': ['TE'],
            'Receiving': ['WR', 'TE', 'RB']
        }
    
    async def get_team_stats(
        self, 
        team: Optional[str] = None,
        season: Optional[int] = None
    ) -> List[TeamStat]:
        """Retrieve team stats with optional filters."""
        query = self.db.query(TeamStat)
        
        if team:
            query = query.filter(TeamStat.team == team)
            
        if season:
            query = query.filter(TeamStat.season == season)
            
        return query.all()
    
    async def update_team_stats(
        self, 
        team: str,
        season: int,
        stats: Dict[str, float]
    ) -> Optional[TeamStat]:
        """Update team statistics."""
        try:
            # Get existing team stats
            team_stat = self.db.query(TeamStat).filter(
                and_(TeamStat.team == team, TeamStat.season == season)
            ).first()
            
            if not team_stat:
                # Create new team stat if it doesn't exist
                team_stat = TeamStat(
                    team_stat_id=str(uuid.uuid4()),
                    team=team,
                    season=season
                )
                
            # Update fields
            for field, value in stats.items():
                if hasattr(team_stat, field):
                    setattr(team_stat, field, value)
            
            # Set updated timestamp
            team_stat.updated_at = datetime.utcnow()
            
            # Save changes
            if not team_stat.team_stat_id:
                self.db.add(team_stat)
            
            self.db.commit()
            return team_stat
            
        except Exception as e:
            logger.error(f"Error updating team stats: {str(e)}")
            self.db.rollback()
            return None
    
    async def apply_team_adjustments(
        self, 
        team: str,
        season: int,
        adjustments: Dict[str, float],
        player_shares: Optional[Dict[str, Dict[str, float]]] = None
    ) -> List[Projection]:
        """
        Apply team-level adjustments to all affected player projections.
        
        Args:
            team: The team to adjust
            season: The season year
            adjustments: Dict of adjustment factors for team-level metrics
            player_shares: Optional dict of player-specific distribution changes
                           Format: {player_id: {metric: new_share}}
        
        Returns:
            List of updated projections
        """
        try:
            # Get all team players
            players = self.db.query(Player).filter(Player.team == team).all()
            if not players:
                logger.warning(f"No players found for team {team}")
                return []
                
            # Get team stats
            team_stats = self.db.query(TeamStat).filter(
                and_(TeamStat.team == team, TeamStat.season == season)
            ).first()
            
            if not team_stats:
                logger.error(f"Team stats not found for {team} in {season}")
                return []
                
            # Apply adjustments to team totals first
            adjusted_team_stats = await self._adjust_team_totals(team_stats, adjustments)
            
            # Get all player projections
            player_ids = [p.player_id for p in players]
            projections = self.db.query(Projection).filter(
                and_(
                    Projection.player_id.in_(player_ids),
                    Projection.season == season
                )
            ).all()
            
            # Calculate current usage shares for each position group
            current_usage = await self._calculate_current_usage(projections, players)
            
            # Apply player-specific share adjustments if provided
            if player_shares:
                current_usage = await self._apply_player_share_changes(
                    current_usage, player_shares
                )
                
            # Update projections based on adjusted team totals and usage shares
            updated_projections = []
            
            for proj in projections:
                player = next((p for p in players if p.player_id == proj.player_id), None)
                if not player:
                    continue
                    
                # Apply position-specific adjustments
                updated_proj = await self._adjust_player_projection(
                    proj, player, adjusted_team_stats, current_usage
                )
                
                updated_projections.append(updated_proj)
                
            # Save all changes
            self.db.commit()
            return updated_projections
            
        except Exception as e:
            logger.error(f"Error applying team adjustments: {str(e)}")
            self.db.rollback()
            return []
    
    async def get_team_usage_breakdown(
        self, 
        team: str,
        season: int
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Get a breakdown of team usage by position group and player.
        
        Returns:
            Dict with format: {
                'passing': {
                    'team_total': 600,
                    'players': {
                        'player_id1': {'name': 'Player1', 'value': 550, 'share': 0.92},
                        'player_id2': {'name': 'Player2', 'value': 50, 'share': 0.08}
                    }
                },
                'rushing': {...},
                'targets': {...}
            }
        """
        try:
            # Get team stats
            team_stats = self.db.query(TeamStat).filter(
                and_(TeamStat.team == team, TeamStat.season == season)
            ).first()
            
            if not team_stats:
                logger.error(f"Team stats not found for {team} in {season}")
                return {}
                
            # Get all players for the team
            players = self.db.query(Player).filter(Player.team == team).all()
            player_ids = [p.player_id for p in players]
            
            # Get all projections
            projections = self.db.query(Projection).filter(
                and_(
                    Projection.player_id.in_(player_ids),
                    Projection.season == season
                )
            ).all()
            
            # Initialize results
            result = {
                'passing': {
                    'team_total': team_stats.pass_attempts,
                    'players': {}
                },
                'rushing': {
                    'team_total': team_stats.rush_attempts,
                    'players': {}
                },
                'targets': {
                    'team_total': team_stats.targets,
                    'players': {}
                }
            }
            
            # Calculate totals from projections
            proj_pass_attempts = 0
            proj_rush_attempts = 0
            proj_targets = 0
            
            # First pass: sum up totals
            for proj in projections:
                player = next((p for p in players if p.player_id == proj.player_id), None)
                if not player:
                    continue
                
                # Passing attempts (QB only)
                if player.position == 'QB' and proj.pass_attempts:
                    proj_pass_attempts += proj.pass_attempts
                
                # Rush attempts (all positions)
                if proj.carries:
                    proj_rush_attempts += proj.carries
                
                # Targets (receiving positions)
                if proj.targets:
                    proj_targets += proj.targets
            
            # Second pass: calculate shares
            for proj in projections:
                player = next((p for p in players if p.player_id == proj.player_id), None)
                if not player:
                    continue
                
                # Passing
                if player.position == 'QB' and proj.pass_attempts:
                    share = proj.pass_attempts / max(1, proj_pass_attempts)
                    result['passing']['players'][player.player_id] = {
                        'name': player.name,
                        'value': proj.pass_attempts,
                        'share': share
                    }
                
                # Rushing
                if proj.carries:
                    share = proj.carries / max(1, proj_rush_attempts)
                    result['rushing']['players'][player.player_id] = {
                        'name': player.name,
                        'value': proj.carries,
                        'share': share
                    }
                
                # Targets
                if proj.targets:
                    share = proj.targets / max(1, proj_targets)
                    result['targets']['players'][player.player_id] = {
                        'name': player.name,
                        'value': proj.targets,
                        'share': share
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting team usage breakdown: {str(e)}")
            return {}
    
    async def _adjust_team_totals(
        self, 
        team_stats: TeamStat, 
        adjustments: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Apply adjustment factors to team totals.
        """
        result = {}
        
        # Pass volume adjustments
        if 'pass_volume' in adjustments:
            factor = adjustments['pass_volume']
            result['pass_attempts'] = team_stats.pass_attempts * factor
            result['pass_yards'] = team_stats.pass_yards * factor
            result['pass_td'] = team_stats.pass_td * factor
            
        # Rush volume adjustments
        if 'rush_volume' in adjustments:
            factor = adjustments['rush_volume']
            result['rush_attempts'] = team_stats.rush_attempts * factor
            result['rush_yards'] = team_stats.rush_yards * factor
            result['rush_td'] = team_stats.rush_td * factor
            
        # Scoring rate adjustments
        if 'scoring_rate' in adjustments:
            factor = adjustments['scoring_rate']
            if 'pass_td' not in result:
                result['pass_td'] = team_stats.pass_td * factor
            else:
                result['pass_td'] *= factor
                
            if 'rush_td' not in result:
                result['rush_td'] = team_stats.rush_td * factor
            else:
                result['rush_td'] *= factor
                
            result['rec_td'] = team_stats.rec_td * factor
            
        # Efficiency adjustments
        if 'pass_efficiency' in adjustments:
            factor = adjustments['pass_efficiency']
            if 'pass_yards' not in result:
                result['pass_yards'] = team_stats.pass_yards * factor
            else:
                # Adjust while preserving volume change
                pass_vol_factor = result['pass_yards'] / team_stats.pass_yards
                result['pass_yards'] = team_stats.pass_yards * pass_vol_factor * factor
                
        if 'rush_efficiency' in adjustments:
            factor = adjustments['rush_efficiency']
            if 'rush_yards' not in result:
                result['rush_yards'] = team_stats.rush_yards * factor
            else:
                # Adjust while preserving volume change
                rush_vol_factor = result['rush_yards'] / team_stats.rush_yards
                result['rush_yards'] = team_stats.rush_yards * rush_vol_factor * factor
                
        # Target distribution (depends on pass_attempts)
        if 'pass_volume' in adjustments:
            factor = adjustments['pass_volume']
            result['targets'] = team_stats.targets * factor
            result['receptions'] = team_stats.receptions * factor
            result['rec_yards'] = team_stats.rec_yards * factor
            if 'rec_td' not in result:
                result['rec_td'] = team_stats.rec_td * factor
        
        # Add unchanged fields
        for field in ['plays', 'pass_percentage', 'pass_td_rate', 'rush_yards_per_carry', 'rank']:
            if hasattr(team_stats, field) and field not in result:
                result[field] = getattr(team_stats, field)
                
        return result
    
    async def _calculate_current_usage(
        self, 
        projections: List[Projection], 
        players: List[Player]
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Calculate current usage shares for each position group.
        """
        # Initialize usage tracker
        usage = {
            'QB': {'pass_attempts': {}, 'rush_attempts': {}},
            'RB': {'rush_attempts': {}, 'targets': {}},
            'WR': {'targets': {}, 'rush_attempts': {}},
            'TE': {'targets': {}}
        }
        
        # Calculate totals first
        totals = {
            'pass_attempts': 0,
            'rush_attempts': 0,
            'targets': 0
        }
        
        for proj in projections:
            player = next((p for p in players if p.player_id == proj.player_id), None)
            if not player:
                continue
                
            # QBs: passing and rushing
            if player.position == 'QB':
                if proj.pass_attempts:
                    totals['pass_attempts'] += proj.pass_attempts
                if proj.carries:
                    totals['rush_attempts'] += proj.carries
                    
            # RBs: rushing and receiving
            elif player.position == 'RB':
                if proj.carries:
                    totals['rush_attempts'] += proj.carries
                if proj.targets:
                    totals['targets'] += proj.targets
                    
            # WRs: receiving and some rushing
            elif player.position == 'WR':
                if proj.targets:
                    totals['targets'] += proj.targets
                if proj.carries:
                    totals['rush_attempts'] += proj.carries
                    
            # TEs: receiving
            elif player.position == 'TE':
                if proj.targets:
                    totals['targets'] += proj.targets
        
        # Calculate individual shares
        for proj in projections:
            player = next((p for p in players if p.player_id == proj.player_id), None)
            if not player:
                continue
                
            # QBs
            if player.position == 'QB':
                if proj.pass_attempts and totals['pass_attempts'] > 0:
                    usage['QB']['pass_attempts'][player.player_id] = {
                        'name': player.name,
                        'value': proj.pass_attempts,
                        'share': proj.pass_attempts / totals['pass_attempts']
                    }
                if proj.carries and totals['rush_attempts'] > 0:
                    usage['QB']['rush_attempts'][player.player_id] = {
                        'name': player.name,
                        'value': proj.carries,
                        'share': proj.carries / totals['rush_attempts']
                    }
                    
            # RBs
            elif player.position == 'RB':
                if proj.carries and totals['rush_attempts'] > 0:
                    usage['RB']['rush_attempts'][player.player_id] = {
                        'name': player.name,
                        'value': proj.carries,
                        'share': proj.carries / totals['rush_attempts']
                    }
                if proj.targets and totals['targets'] > 0:
                    usage['RB']['targets'][player.player_id] = {
                        'name': player.name,
                        'value': proj.targets,
                        'share': proj.targets / totals['targets']
                    }
                    
            # WRs
            elif player.position == 'WR':
                if proj.targets and totals['targets'] > 0:
                    usage['WR']['targets'][player.player_id] = {
                        'name': player.name,
                        'value': proj.targets,
                        'share': proj.targets / totals['targets']
                    }
                if proj.carries and totals['rush_attempts'] > 0:
                    usage['WR']['rush_attempts'][player.player_id] = {
                        'name': player.name,
                        'value': proj.carries,
                        'share': proj.carries / totals['rush_attempts']
                    }
                    
            # TEs
            elif player.position == 'TE':
                if proj.targets and totals['targets'] > 0:
                    usage['TE']['targets'][player.player_id] = {
                        'name': player.name,
                        'value': proj.targets,
                        'share': proj.targets / totals['targets']
                    }
        
        return usage
    
    async def _apply_player_share_changes(
        self,
        current_usage: Dict[str, Dict[str, Dict[str, float]]],
        player_shares: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Apply player-specific share changes and rebalance other players.
        """
        # Create a deep copy to avoid modifying the original
        updated_usage = {
            position: {
                metric: {
                    player_id: {**data}
                    for player_id, data in player_data.items()
                }
                for metric, player_data in position_data.items()
            }
            for position, position_data in current_usage.items()
        }
        
        # Process each player share change
        for player_id, metrics in player_shares.items():
            # Find the player's position
            player_position = None
            for position, metrics_data in updated_usage.items():
                for metric, players_data in metrics_data.items():
                    if player_id in players_data:
                        player_position = position
                        break
                if player_position:
                    break
                    
            if not player_position:
                continue  # Skip if player not found
                
            # Apply share changes for each metric
            for metric, new_share in metrics.items():
                if metric not in updated_usage[player_position]:
                    continue
                    
                players_data = updated_usage[player_position][metric]
                if player_id not in players_data:
                    continue
                    
                # Calculate the difference
                old_share = players_data[player_id]['share']
                diff = new_share - old_share
                
                if abs(diff) < 0.001:
                    continue  # Skip if no significant change
                    
                # Apply the new share
                players_data[player_id]['share'] = new_share
                
                # Rebalance other players proportionally
                other_players = [p_id for p_id in players_data if p_id != player_id]
                if not other_players:
                    continue
                    
                # Calculate total share of other players
                other_total = sum(players_data[p_id]['share'] for p_id in other_players)
                
                if other_total <= 0:
                    continue
                    
                # Apply adjustment factor to other players
                adj_factor = (1.0 - new_share) / other_total
                
                for p_id in other_players:
                    players_data[p_id]['share'] *= adj_factor
        
        return updated_usage
    
    async def _adjust_player_projection(
        self,
        projection: Projection,
        player: Player,
        team_stats: Dict[str, float],
        usage: Dict[str, Dict[str, Dict[str, float]]]
    ) -> Projection:
        """
        Adjust an individual player projection based on team totals and usage shares.
        """
        position = player.position
        player_id = player.player_id
        
        # QB adjustments
        if position == 'QB':
            if player_id in usage['QB'].get('pass_attempts', {}):
                # Calculate new passing stats
                share = usage['QB']['pass_attempts'][player_id]['share']
                new_attempts = team_stats.get('pass_attempts', 0) * share
                
                if projection.pass_attempts and projection.pass_attempts > 0:
                    # Adjust passing stats
                    factor = new_attempts / projection.pass_attempts
                    projection.pass_attempts = new_attempts
                    projection.completions *= factor
                    projection.pass_yards = team_stats.get('pass_yards', 0) * share
                    projection.pass_td = team_stats.get('pass_td', 0) * share
                    
                    # Preserve efficiency metrics
                    if projection.pass_attempts > 0:
                        projection.comp_pct = projection.completions / projection.pass_attempts
                        projection.yards_per_att = projection.pass_yards / projection.pass_attempts
                
            if player_id in usage['QB'].get('rush_attempts', {}):
                # Calculate new rush stats
                share = usage['QB']['rush_attempts'][player_id]['share']
                new_carries = team_stats.get('rush_attempts', 0) * share
                
                if projection.carries and projection.carries > 0:
                    factor = new_carries / projection.carries
                    projection.carries = new_carries
                    projection.rush_yards = team_stats.get('rush_yards', 0) * share
                    projection.rush_td = team_stats.get('rush_td', 0) * share
        
        # RB adjustments
        elif position == 'RB':
            if player_id in usage['RB'].get('rush_attempts', {}):
                # Calculate new rush stats
                share = usage['RB']['rush_attempts'][player_id]['share']
                new_carries = team_stats.get('rush_attempts', 0) * share
                
                if projection.carries and projection.carries > 0:
                    factor = new_carries / projection.carries
                    projection.carries = new_carries
                    projection.rush_yards = team_stats.get('rush_yards', 0) * share
                    projection.rush_td = team_stats.get('rush_td', 0) * share
            
            if player_id in usage['RB'].get('targets', {}):
                # Calculate new receiving stats
                share = usage['RB']['targets'][player_id]['share']
                new_targets = team_stats.get('targets', 0) * share
                
                if projection.targets and projection.targets > 0:
                    factor = new_targets / projection.targets
                    projection.targets = new_targets
                    projection.receptions *= factor
                    projection.rec_yards = team_stats.get('rec_yards', 0) * share
                    projection.rec_td = team_stats.get('rec_td', 0) * share
        
        # WR adjustments
        elif position == 'WR':
            if player_id in usage['WR'].get('targets', {}):
                # Calculate new receiving stats
                share = usage['WR']['targets'][player_id]['share']
                new_targets = team_stats.get('targets', 0) * share
                
                if projection.targets and projection.targets > 0:
                    factor = new_targets / projection.targets
                    projection.targets = new_targets
                    projection.receptions *= factor
                    projection.rec_yards = team_stats.get('rec_yards', 0) * share
                    projection.rec_td = team_stats.get('rec_td', 0) * share
            
            if player_id in usage['WR'].get('rush_attempts', {}):
                # Calculate new rush stats (for WRs with rush attempts)
                share = usage['WR']['rush_attempts'][player_id]['share']
                new_carries = team_stats.get('rush_attempts', 0) * share
                
                if projection.carries and projection.carries > 0:
                    factor = new_carries / projection.carries
                    projection.carries = new_carries
                    projection.rush_yards *= factor
                    projection.rush_td *= factor
        
        # TE adjustments
        elif position == 'TE':
            if player_id in usage['TE'].get('targets', {}):
                # Calculate new receiving stats
                share = usage['TE']['targets'][player_id]['share']
                new_targets = team_stats.get('targets', 0) * share
                
                if projection.targets and projection.targets > 0:
                    factor = new_targets / projection.targets
                    projection.targets = new_targets
                    projection.receptions *= factor
                    projection.rec_yards = team_stats.get('rec_yards', 0) * share
                    projection.rec_td = team_stats.get('rec_td', 0) * share
        
        # Recalculate fantasy points
        projection.half_ppr = projection.calculate_fantasy_points()
        projection.updated_at = datetime.utcnow()
        
        return projection