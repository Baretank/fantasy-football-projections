from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship, mapped_column, Mapped
from datetime import datetime
from typing import Dict, Optional
from .database import Base
import uuid

class GameStats(Base):
    """Game-by-game player statistics"""
    __tablename__ = "game_stats"

    game_stat_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(ForeignKey("players.player_id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
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

    @classmethod
    def from_game_log(cls, player_id: str, game_log_row: Dict) -> 'GameStats':
        """Create GameStats instance from a PFR game log row"""
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
    name: Mapped[str] = mapped_column(String, nullable=False)
    team: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    game_stats = relationship("GameStats", back_populates="player")
    base_stats = relationship("BaseStat", back_populates="player")
    projections = relationship("Projection", back_populates="player")
    stat_overrides = relationship("StatOverride", back_populates="player")

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
    team: Mapped[str] = mapped_column(String, nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
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
    carries: Mapped[float] = mapped_column(Float)
    rush_yards_per_carry: Mapped[float] = mapped_column(Float)
    targets: Mapped[float] = mapped_column(Float)
    receptions: Mapped[float] = mapped_column(Float)
    rec_yards: Mapped[float] = mapped_column(Float)
    rec_td: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
            carries=data['Car'],
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
    player_id: Mapped[str] = mapped_column(ForeignKey("players.player_id"), nullable=False)
    scenario_id: Mapped[Optional[str]] = mapped_column(ForeignKey("scenarios.scenario_id"), nullable=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    games: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Fantasy points
    half_ppr: Mapped[float] = mapped_column(Float, nullable=False)
    
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
    carries: Mapped[Optional[float]] = mapped_column(Float)
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
    car_pct: Mapped[Optional[float]] = mapped_column(Float)       # % of team rush attempts
    yards_per_carry: Mapped[Optional[float]] = mapped_column(Float) # gross YPC
    net_yards_per_carry: Mapped[Optional[float]] = mapped_column(Float) # net YPC
    tar_pct: Mapped[Optional[float]] = mapped_column(Float)       # % of team targets
    catch_pct: Mapped[Optional[float]] = mapped_column(Float)     # catch rate
    yards_per_target: Mapped[Optional[float]] = mapped_column(Float) # YPT
    rec_td_rate: Mapped[Optional[float]] = mapped_column(Float)   # TD% on targets
    
    # Override tracking
    has_overrides: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fill_player: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    player = relationship("Player", back_populates="projections")
    scenario = relationship("Scenario", back_populates="projections")
    stat_overrides = relationship("StatOverride", back_populates="projection")

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
                'carries': data.get('Car'),
                'rush_yards': data.get('RuYD'),
                'rush_td': data.get('RuTD')
            })
        elif data['Pos'] in ['RB', 'WR', 'TE']:
            base.update({
                'carries': data.get('Car'),
                'rush_yards': data.get('RuYD'),
                'rush_td': data.get('RuTD'),
                'targets': data.get('Tar'),
                'receptions': data.get('Rec'),
                'rec_yards': data.get('ReYD'),
                'rec_td': data.get('ReTD')
            })
            
        return cls(**base)

    def calculate_fantasy_points(self) -> float:
        """Calculate half-PPR fantasy points with enhanced accuracy"""
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
            points += (self.receptions * 0.5)  # Half PPR
        if self.rec_yards:
            points += (self.rec_yards / 10.0)  # 0.1 points per receiving yard
        if self.rec_td:
            points += (self.rec_td * 6.0)
            
        return points

class Scenario(Base):
    """Projection scenarios for what-if analysis"""
    __tablename__ = "scenarios"

    scenario_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False) 
    base_scenario_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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