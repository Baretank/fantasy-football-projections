from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, JSON, Boolean, Date, Enum, Index
from sqlalchemy.orm import relationship, mapped_column, Mapped
from datetime import datetime, date
from typing import Dict, Optional
from .database import Base
import uuid
import enum

class DraftStatus(str, enum.Enum):
    """Status of a player in a fantasy draft"""
    AVAILABLE = "available"
    DRAFTED = "drafted"
    WATCHED = "watched"

# First ImportLog class removed to fix duplication error

class GameStats(Base):
    """Game-by-game player statistics"""
    __tablename__ = "game_stats"

    game_stat_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(ForeignKey("players.player_id"), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    week: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    opponent: Mapped[str] = mapped_column(String, nullable=False)
    game_location: Mapped[str] = mapped_column(String, nullable=False)  # home/away
    result: Mapped[str] = mapped_column(String, nullable=False)  # W/L
    team_score: Mapped[int] = mapped_column(Integer, nullable=False)
    opponent_score: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Store position-specific stats in JSON
    stats: Mapped[Dict] = mapped_column(JSON, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    player = relationship("Player", back_populates="game_stats")
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_game_stats_player_season', 'player_id', 'season'),
        Index('ix_game_stats_season_week', 'season', 'week'),
    )

    @classmethod
    def from_game_log(cls, player_id: str, game_log_row: Dict) -> 'GameStats':
        """Create GameStats instance from an NFL data game log row"""
        base_data = {
            'player_id': player_id,
            'season': int(game_log_row['date'][:4]),  # Extract year from date
            'week': int(game_log_row['week']),
            'opponent': game_log_row['opp'],
            'game_location': 'away' if game_log_row['game_location'] == '@' else 'home',
            'result': game_log_row['result'],
            'team_score': int(game_log_row['team_pts']),
            'opponent_score': int(game_log_row['opp_pts'])
        }
        
        # Remove base fields to leave only stats
        stats_fields = {k: v for k, v in game_log_row.items() 
                       if k not in ['date', 'week', 'opp', 'game_location', 
                                  'result', 'team_pts', 'opp_pts']}
        
        return cls(
            game_stat_id=str(uuid.uuid4()),
            **base_data,
            stats=stats_fields
        )

class Player(Base):
    """Player information and metadata"""
    __tablename__ = "players"

    player_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    team: Mapped[str] = mapped_column(String, nullable=False, index=True)
    position: Mapped[str] = mapped_column(String, nullable=False, index=True)
    
    # New fields for enhanced player details
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # Format: YYYY-MM-DD
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Height in inches
    weight: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # In pounds
    status: Mapped[str] = mapped_column(String, default="Active", index=True)  # Active, Injured, Rookie
    depth_chart_position: Mapped[str] = mapped_column(String, default="Backup")  # Starter, Backup, Reserve
    is_fill_player: Mapped[bool] = mapped_column(Boolean, default=False)  # Whether this is a fill player (for team stats reconciliation)
    is_rookie: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # Whether this is a rookie player
    
    # Draft information fields
    draft_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Overall draft position
    draft_team: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Team that drafted player
    draft_round: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Draft round
    draft_pick: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Pick within round
    
    # Draft board fields
    draft_status: Mapped[str] = mapped_column(Enum(DraftStatus), default=DraftStatus.AVAILABLE, index=True)  # available, drafted, watched
    fantasy_team: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)  # Fantasy team that drafted the player
    draft_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Order in which player was drafted
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    game_stats = relationship("GameStats", back_populates="player")
    base_stats = relationship("BaseStat", back_populates="player")
    projections = relationship("Projection", back_populates="player")
    stat_overrides = relationship("StatOverride", back_populates="player")
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_players_position_team', 'position', 'team'),
        Index('ix_players_position_status', 'position', 'status'),
        Index('ix_players_team_position', 'team', 'position'),
        Index('ix_players_draft_status_position', 'draft_status', 'position'),
    )

class BaseStat(Base):
    """Historical and baseline statistics"""
    __tablename__ = "base_stats"

    stat_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(ForeignKey("players.player_id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Null for season totals
    stat_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g., 'pass_attempts', 'rush_yards'
    value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    player = relationship("Player", back_populates="base_stats")

class TeamStat(Base):
    """Team-level offensive statistics and metrics"""
    __tablename__ = "team_stats"

    team_stat_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    team: Mapped[str] = mapped_column(String, nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Core offensive metrics
    plays: Mapped[float] = mapped_column(Float, nullable=False)
    pass_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    pass_attempts: Mapped[float] = mapped_column(Float, nullable=False)
    pass_yards: Mapped[float] = mapped_column(Float)
    pass_td: Mapped[float] = mapped_column(Float)
    pass_td_rate: Mapped[float] = mapped_column(Float)
    rush_attempts: Mapped[float] = mapped_column(Float)
    rush_yards: Mapped[float] = mapped_column(Float)
    rush_td: Mapped[float] = mapped_column(Float)
    rush_yards_per_carry: Mapped[float] = mapped_column(Float)
    targets: Mapped[float] = mapped_column(Float)
    receptions: Mapped[float] = mapped_column(Float)
    rec_yards: Mapped[float] = mapped_column(Float)
    rec_td: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_team_stats_team_season', 'team', 'season'),
        Index('ix_team_stats_season_rank', 'season', 'rank'),
        Index('ix_team_stats_team_season_week', 'team', 'season', 'week'),
    )

    @classmethod
    def from_dict(cls, data: Dict) -> 'TeamStat':
        """Create TeamStat from dictionary of values"""
        return cls(
            team=data['Team'],
            plays=data['Plays'],
            pass_percentage=data['Pass %'],
            pass_attempts=data['PaATT'],
            pass_yards=data['PaYD'],
            pass_td=data['PaTD'],
            pass_td_rate=data['TD%'],
            rush_attempts=data['RuATT'],
            rush_yards=data['RuYD'],
            rush_td=data['RuTD'],
            rush_yards_per_carry=data['YPC'],
            targets=data['Tar'],
            receptions=data['Rec'],
            rec_yards=data['ReYD'],
            rec_td=data['ReTD'],
            rank=data['Rank']
        )

class Projection(Base):
    """Individual player projections with statistical modeling"""
    __tablename__ = "projections"

    projection_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(ForeignKey("players.player_id"), nullable=False, index=True)
    scenario_id: Mapped[Optional[str]] = mapped_column(ForeignKey("scenarios.scenario_id"), nullable=True, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    games: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Fantasy points
    half_ppr: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    
    # Passing stats (QB)
    pass_attempts: Mapped[Optional[float]] = mapped_column(Float)
    completions: Mapped[Optional[float]] = mapped_column(Float)
    pass_yards: Mapped[Optional[float]] = mapped_column(Float)
    pass_td: Mapped[Optional[float]] = mapped_column(Float)
    interceptions: Mapped[Optional[float]] = mapped_column(Float)
    
    # Enhanced passing stats
    gross_pass_yards: Mapped[Optional[float]] = mapped_column(Float)
    sacks: Mapped[Optional[float]] = mapped_column(Float)
    sack_yards: Mapped[Optional[float]] = mapped_column(Float)
    net_pass_yards: Mapped[Optional[float]] = mapped_column(Float)
    pass_td_rate: Mapped[Optional[float]] = mapped_column(Float)
    int_rate: Mapped[Optional[float]] = mapped_column(Float)
    sack_rate: Mapped[Optional[float]] = mapped_column(Float)
    
    # Rushing stats (All positions)
    rush_attempts: Mapped[Optional[float]] = mapped_column(Float)
    rush_yards: Mapped[Optional[float]] = mapped_column(Float)
    rush_td: Mapped[Optional[float]] = mapped_column(Float)
    
    # Enhanced rushing stats
    gross_rush_yards: Mapped[Optional[float]] = mapped_column(Float)
    fumbles: Mapped[Optional[float]] = mapped_column(Float)
    fumble_rate: Mapped[Optional[float]] = mapped_column(Float)
    net_rush_yards: Mapped[Optional[float]] = mapped_column(Float)
    rush_td_rate: Mapped[Optional[float]] = mapped_column(Float)
    
    # Receiving stats (RB, WR, TE)
    targets: Mapped[Optional[float]] = mapped_column(Float)
    receptions: Mapped[Optional[float]] = mapped_column(Float)
    rec_yards: Mapped[Optional[float]] = mapped_column(Float)
    rec_td: Mapped[Optional[float]] = mapped_column(Float)
    
    # Usage metrics
    snap_share: Mapped[Optional[float]] = mapped_column(Float)
    target_share: Mapped[Optional[float]] = mapped_column(Float)
    rush_share: Mapped[Optional[float]] = mapped_column(Float)
    redzone_share: Mapped[Optional[float]] = mapped_column(Float)
    
    # Efficiency metrics
    pass_att_pct: Mapped[Optional[float]] = mapped_column(Float)  # % of team pass attempts
    comp_pct: Mapped[Optional[float]] = mapped_column(Float)      # completion percentage
    yards_per_att: Mapped[Optional[float]] = mapped_column(Float) # gross YPA
    net_yards_per_att: Mapped[Optional[float]] = mapped_column(Float) # net YPA
    rush_att_pct: Mapped[Optional[float]] = mapped_column(Float)  # % of team rush attempts
    yards_per_carry: Mapped[Optional[float]] = mapped_column(Float) # gross YPC
    net_yards_per_carry: Mapped[Optional[float]] = mapped_column(Float) # net YPC
    tar_pct: Mapped[Optional[float]] = mapped_column(Float)       # % of team targets
    catch_pct: Mapped[Optional[float]] = mapped_column(Float)     # catch rate
    yards_per_target: Mapped[Optional[float]] = mapped_column(Float) # YPT
    rec_td_rate: Mapped[Optional[float]] = mapped_column(Float)   # TD% on targets
    
    # Override tracking
    has_overrides: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_fill_player: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    player = relationship("Player", back_populates="projections")
    scenario = relationship("Scenario", back_populates="projections")
    stat_overrides = relationship("StatOverride", back_populates="projection")
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_projections_player_season', 'player_id', 'season'),
        Index('ix_projections_scenario_season', 'scenario_id', 'season'),
        Index('ix_projections_season_half_ppr', 'season', 'half_ppr'),
        Index('ix_projections_player_scenario', 'player_id', 'scenario_id'),
    )

    @classmethod
    def from_dict(cls, data: Dict) -> 'Projection':
        """Create Projection from dictionary of values"""
        base = {
            'player_id': data['Player'],
            'season': data['Season'],
            'games': data['Gm'],
            'half_ppr': data['HPPR']
        }
        
        # Add position-specific stats
        if data['Pos'] == 'QB':
            base.update({
                'pass_attempts': data.get('PaATT'),
                'completions': data.get('Comp'),
                'pass_yards': data.get('PaYD'),
                'pass_td': data.get('PaTD'),
                'interceptions': data.get('INT'),
                'rush_attempts': data.get('RuATT') or data.get('rush_attempts'),
                'rush_yards': data.get('RuYD'),
                'rush_td': data.get('RuTD')
            })
        elif data['Pos'] in ['RB', 'WR', 'TE']:
            base.update({
                'rush_attempts': data.get('RuATT') or data.get('rush_attempts'),
                'rush_yards': data.get('RuYD'),
                'rush_td': data.get('RuTD'),
                'targets': data.get('Tar'),
                'receptions': data.get('Rec'),
                'rec_yards': data.get('ReYD'),
                'rec_td': data.get('ReTD')
            })
            
        return cls(**base)

    def calculate_fantasy_points(self, scoring_type: str = 'half') -> float:
        """
        Calculate fantasy points with enhanced accuracy
        
        Args:
            scoring_type: 'standard', 'half', or 'ppr'
        """
        points = 0.0
        
        # Passing points - use net passing yards if available
        pass_yards = self.net_pass_yards if self.net_pass_yards is not None else self.pass_yards
        if pass_yards:
            points += (pass_yards / 25.0)  # 0.04 points per passing yard
        if self.pass_td:
            points += (self.pass_td * 4.0)
        if self.interceptions:
            points -= (self.interceptions * 2.0)
            
        # Rushing points - use net rushing yards if available
        rush_yards = self.net_rush_yards if self.net_rush_yards is not None else self.rush_yards
        if rush_yards:
            points += (rush_yards / 10.0)  # 0.1 points per rushing yard
        if self.rush_td:
            points += (self.rush_td * 6.0)
        
        # Fumble penalty
        if self.fumbles:
            points -= (self.fumbles * 2.0)
            
        # Receiving points
        if self.receptions:
            if scoring_type == 'ppr':
                points += (self.receptions * 1.0)  # Full PPR
            elif scoring_type == 'half':
                points += (self.receptions * 0.5)  # Half PPR
            # No points for receptions in standard scoring
            
        if self.rec_yards:
            points += (self.rec_yards / 10.0)  # 0.1 points per receiving yard
        if self.rec_td:
            points += (self.rec_td * 6.0)
            
        return points
        
    @property
    def standard(self) -> float:
        """Calculate standard fantasy points"""
        return self.calculate_fantasy_points(scoring_type='standard')
        
    @property
    def ppr(self) -> float:
        """Calculate PPR fantasy points"""
        return self.calculate_fantasy_points(scoring_type='ppr')

class Scenario(Base):
    """Projection scenarios for what-if analysis"""
    __tablename__ = "scenarios"

    scenario_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False) 
    base_scenario_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False, default=2024)
    parameters: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projections = relationship("Projection", back_populates="scenario")

class StatOverride(Base):
    """Track manual overrides to projection values"""
    __tablename__ = "stat_overrides"
    
    override_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(ForeignKey("players.player_id"), nullable=False)
    projection_id: Mapped[str] = mapped_column(ForeignKey("projections.projection_id"), nullable=False)
    stat_name: Mapped[str] = mapped_column(String, nullable=False)
    calculated_value: Mapped[float] = mapped_column(Float, nullable=False)
    manual_value: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    player = relationship("Player", back_populates="stat_overrides")
    projection = relationship("Projection", back_populates="stat_overrides")

class RookieProjectionTemplate(Base):
    """Templates for rookie projections based on position and draft position"""
    __tablename__ = "rookie_projection_templates"

    template_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    position: Mapped[str] = mapped_column(String, nullable=False)  # QB, RB, WR, TE
    draft_round: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-7
    draft_pick_min: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-262
    draft_pick_max: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-262
    
    # Playing time
    games: Mapped[float] = mapped_column(Float, default=17.0)
    snap_share: Mapped[float] = mapped_column(Float)  # Percentage of team snaps
    
    # Position-specific metrics
    # QB metrics
    pass_attempts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comp_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    yards_per_att: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pass_td_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    int_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rush_att_per_game: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rush_yards_per_att: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rush_td_per_game: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # RB metrics
    targets_per_game: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    catch_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rec_yards_per_catch: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rec_td_per_catch: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rush_td_per_att: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DraftBoard(Base):
    """Track draft board status for fantasy drafts"""
    __tablename__ = "draft_boards"
    
    draft_board_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    draft_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    number_of_teams: Mapped[int] = mapped_column(Integer, default=12)
    roster_spots: Mapped[int] = mapped_column(Integer, default=15)
    current_pick: Mapped[int] = mapped_column(Integer, default=0)
    settings: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)  # scoring rules, position limits, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ImportLog(Base):
    """Track import operations and errors"""
    __tablename__ = "import_logs"
    
    log_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    operation: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # success, warning, error
    message: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)