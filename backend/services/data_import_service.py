from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_
import pandas as pd
import logging
import asyncio
import random
import time
from datetime import datetime, timedelta
import uuid
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from pro_football_reference_web_scraper import player_game_log
from backend.database.models import Player, BaseStat, TeamStat, GameStats

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Simple circuit breaker to prevent excessive requests during rate limiting."""
    def __init__(self, failure_threshold: int = 3, reset_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout  # seconds
        self.failure_count = 0
        self.open_since = None
        
    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.open_circuit()
            
    def open_circuit(self):
        """Open the circuit, preventing further requests."""
        self.open_since = datetime.now()
        logger.warning(f"Circuit breaker opened. Pausing requests for {self.reset_timeout} seconds.")
        
    def reset(self):
        """Reset the circuit breaker."""
        self.failure_count = 0
        self.open_since = None
        
    def is_open(self) -> bool:
        """Check if the circuit is currently open."""
        if self.open_since is None:
            return False
            
        # Check if we've waited long enough to try again
        elapsed = (datetime.now() - self.open_since).total_seconds()
        if elapsed >= self.reset_timeout:
            logger.info("Circuit breaker reset after timeout.")
            self.reset()
            return False
            
        return True

class DataImportService:
    def __init__(self, db: Session):
        self.db = db
        self.positions = ['QB', 'RB', 'WR', 'TE']
        self.min_delay = 0.8  # 800ms minimum delay between requests
        self.max_delay = 1.2  # 1.2s maximum delay
        self.request_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=120)
        
        # Raw stat mappings - only counting/volume stats
        self.stat_mappings = {
            'QB': {
                'completions': 'cmp',
                'pass_attempts': 'att',
                'pass_yards': 'pass_yds',
                'pass_td': 'pass_td',
                'interceptions': 'int',
                'rush_attempts': 'rush_att',
                'rush_yards': 'rush_yds',
                'rush_td': 'rush_td',
                'sacks': 'sacked'  # If available
            },
            'RB': {
                'rush_attempts': 'rush_att',
                'rush_yards': 'rush_yds',
                'rush_td': 'rush_td',
                'targets': 'tgt',
                'receptions': 'rec',
                'rec_yards': 'rec_yds',
                'rec_td': 'rec_td'
            },
            'WR': {
                'targets': 'tgt',
                'receptions': 'rec',
                'rec_yards': 'rec_yds',
                'rec_td': 'rec_td',
                'rush_attempts': 'rush_att',
                'rush_yards': 'rush_yds',
                'rush_td': 'rush_td'
            },
            'TE': {
                'targets': 'tgt',
                'receptions': 'rec',
                'rec_yards': 'rec_yds',
                'rec_td': 'rec_td'
            }
        }
    
    async def import_season_data(self, season: int = 2024) -> Tuple[int, List[str]]:
        """
        Import season data for all positions.
        Returns (success_count, error_messages)
        """
        total_success = 0
        all_errors = []
        
        for position in self.positions:
            logger.info(f"Importing {position} data for {season}")
            success, errors = await self.import_position_group(position, season)
            total_success += success
            all_errors.extend(errors)
            
        return total_success, all_errors

    async def import_position_group(
        self, 
        position: str, 
        season: int,
        batch_size: int = 5,  # Process 5 players at a time
        batch_delay: float = 3.0  # 3s delay between batches
    ) -> Tuple[int, List[str]]:
        """
        Import all players for a specific position with batch processing.
        Returns (success_count, error_messages)
        """
        if position not in self.positions:
            return 0, [f"Invalid position: {position}"]
            
        success_count = 0
        error_messages = []

        try:
            # Get the comprehensive list of players
            players = await self.build_position_player_list(position, season)
            logger.info(f"Starting import for {len(players)} {position} players in batches of {batch_size}")
            
            # Process in batches
            for batch_start in range(0, len(players), batch_size):
                # Check if circuit breaker is open
                if self.circuit_breaker.is_open():
                    msg = "Circuit breaker triggered due to rate limiting. Pausing imports."
                    logger.warning(msg)
                    error_messages.append(msg)
                    break
                
                batch_end = min(batch_start + batch_size, len(players))
                batch = players[batch_start:batch_end]
                logger.info(f"Processing batch {batch_start//batch_size + 1}/{(len(players)-1)//batch_size + 1} ({batch_start+1}-{batch_end}/{len(players)})")
                
                batch_tasks = []
                for player in batch:
                    player_name = player['name']
                    player_team = player['team']
                    
                    # Check if player already has data (don't create task if data exists)
                    exists = await self._player_data_exists(player_name, position, season)
                    if exists:
                        logger.info(f"Skipping {player_name} - already imported")
                        success_count += 1
                        continue
                        
                    # Create task for player import
                    task = self._process_player(
                        name=player_name,
                        position=position,
                        team=player_team,
                        season=season
                    )
                    batch_tasks.append(task)
                
                # Execute batch tasks concurrently
                if batch_tasks:
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Process results
                    for idx, result in enumerate(batch_results):
                        if isinstance(result, Exception):
                            msg = f"Error importing player: {str(result)}"
                            logger.error(msg)
                            error_messages.append(msg)
                        else:
                            success_count += 1
                
                # Delay between batches (if not the last batch)
                if batch_end < len(players):
                    logger.info(f"Batch complete. Waiting {batch_delay}s before next batch.")
                    await asyncio.sleep(batch_delay)
                    
            return success_count, error_messages
                
        except Exception as e:
            logger.error(f"Error importing {position} group: {str(e)}")
            return success_count, [*error_messages, str(e)]
            
    async def _process_player(
        self,
        name: str,
        position: str,
        team: str,
        season: int
    ) -> bool:
        """Process a single player within a batch."""
        logger.info(f"Processing {name} ({team})")
        try:
            await self._import_player_data(
                name=name,
                position=position,
                team=team,
                season=season
            )
            return True
        except Exception as e:
            logger.error(f"Error processing {name}: {str(e)}")
            raise

    async def build_position_player_list(self, position: str, season: int) -> List[Dict]:
        """
        Build a comprehensive list of players for a given position.
        Uses PFR leaderboard pages to get all active players.
        """
        # Get all players from PFR leaderboards
        all_players = await self.get_all_players_by_position(position, season)
        
        # Add rookies from rookies.json (these might not be on leaderboards yet)
        rookies = await self._get_rookie_data()
        existing_names = {p["name"].lower() for p in all_players}
        
        # Add any rookies not already in the list
        for rookie in rookies:
            if rookie["position"] == position and rookie["name"].lower() not in existing_names:
                all_players.append({
                    "name": rookie["name"],
                    "team": rookie["team"],
                    "position": position
                })
        
        logger.info(f"Final player list for {position}: {len(all_players)} players")
        return all_players
            
    async def get_all_players_by_position(self, position: str, season: int) -> List[Dict]:
        """
        Scrape the PFR position leaderboard pages to get all players.
        This gets us a comprehensive list without having to maintain static lists.
        """
        # Map positions to their respective leaderboard pages
        position_pages = {
            'QB': f'https://www.pro-football-reference.com/years/{season}/passing.htm',
            'RB': f'https://www.pro-football-reference.com/years/{season}/rushing.htm',
            'WR': f'https://www.pro-football-reference.com/years/{season}/receiving.htm',
            'TE': f'https://www.pro-football-reference.com/years/{season}/receiving.htm'
        }
        
        if position not in position_pages:
            logger.error(f"Invalid position: {position}")
            return []
        
        url = position_pages[position]
        logger.info(f"Scraping {position} players from {url}")
        
        try:
            # Make the request with rate limiting and backoff
            async with self.request_semaphore:
                response = await self._request_with_backoff(url)
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the stats table
            table_id = 'passing' if position == 'QB' else 'rushing' if position == 'RB' else 'receiving'
            table = soup.find('table', id=table_id)
                    
            if not table:
                logger.error(f"Could not find stats table for {position}")
                return []
            
            # Extract player data
            players = []
            rows = table.find('tbody').find_all('tr')
            
            for row in rows:
                # Skip header and separator rows
                if 'class' in row.attrs and ('thead' in row.attrs['class'] or 'divider' in row.attrs['class']):
                    continue
                    
                player_cell = row.find('td', {'data-stat': 'player'})
                if not player_cell:
                    continue
                    
                team_cell = row.find('td', {'data-stat': 'team'})
                
                player_name = player_cell.get_text(strip=True)
                team = team_cell.get_text(strip=True) if team_cell else "UNK"
                
                # For WR/TE pages, we need to filter by position
                if position in ['WR', 'TE']:
                    pos_cell = row.find('td', {'data-stat': 'pos'})
                    if pos_cell and pos_cell.get_text(strip=True) != position:
                        continue
                
                players.append({
                    'name': player_name,
                    'team': team,
                    'position': position
                })
            
            logger.info(f"Found {len(players)} {position} players")
            return players
            
        except Exception as e:
            logger.error(f"Error scraping {position} players: {str(e)}")
            return []

    async def _player_data_exists(self, name: str, position: str, season: int) -> bool:
        """Check if player data already exists in the database."""
        player = self.db.query(Player).filter(
            and_(Player.name == name, Player.position == position)
        ).first()
        
        if not player:
            return False
            
        # Check if we have game stats for this season
        game_stats = self.db.query(GameStats).filter(
            and_(GameStats.player_id == player.player_id, GameStats.season == season)
        ).first()
        
        return game_stats is not None

    async def _import_player_data(
        self,
        name: str,
        position: str,
        team: str,
        season: int
    ) -> None:
        """Import both game logs and season totals for a player."""
        try:
            # First check if player exists
            player = self.db.query(Player).filter(
                and_(Player.name == name, Player.position == position)
            ).first()
            
            if not player:
                player = Player(
                    player_id=str(uuid.uuid4()),
                    name=name,
                    team=team,
                    position=position
                )
                self.db.add(player)
                self.db.flush()
            
            # Get game logs from PFR with concurrency control
            async with self.request_semaphore:
                # The game_log scraper is synchronous, so we use asyncio.to_thread
                # to avoid blocking the event loop
                game_log_df = await asyncio.to_thread(
                    player_game_log.get_player_game_log,
                    player=name,
                    position=position,
                    season=season
                )
                # Apply rate limiting after the request
                await self._sleep_random()
            
            if game_log_df is None or game_log_df.empty:
                logger.warning(f"No game log data found for {name}")
                return
                
            # Import each game
            for _, game in game_log_df.iterrows():
                game_dict = game.to_dict()
                game_stats = GameStats.from_game_log(player.player_id, game_dict)
                self.db.add(game_stats)
            
            # Calculate and store season totals
            await self._store_season_totals(player.player_id, game_log_df, season)
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error importing data for {name}: {str(e)}")
            raise

    async def _store_season_totals(
        self,
        player_id: str,
        game_log_df: pd.DataFrame,
        season: int
    ) -> None:
        """Calculate and store season total stats from game logs."""
        try:
            # Get the player's position
            player = self.db.query(Player).get(player_id)
            if not player:
                raise ValueError(f"Player {player_id} not found")
                
            # Get relevant stat columns based on position
            stat_cols = list(self.stat_mappings[player.position].values())
            
            # Filter the DataFrame to include only columns that actually exist
            existing_cols = [col for col in stat_cols if col in game_log_df.columns]
            
            # Calculate totals for each stat
            totals = game_log_df[existing_cols].sum()
            
            # Store base stats
            for our_name, pfr_name in self.stat_mappings[player.position].items():
                if pfr_name in totals.index:
                    stat = BaseStat(
                        stat_id=str(uuid.uuid4()),
                        player_id=player_id,
                        season=season,
                        stat_type=our_name,
                        value=float(totals[pfr_name])
                    )
                    self.db.add(stat)
            
            # Store number of games played
            games_played = len(game_log_df)
            games_stat = BaseStat(
                stat_id=str(uuid.uuid4()),
                player_id=player_id,
                season=season,
                stat_type="games",
                value=float(games_played)
            )
            self.db.add(games_stat)
                    
        except Exception as e:
            logger.error(f"Error storing season totals: {str(e)}")
            raise

    async def _get_rookie_data(self) -> List[Dict]:
        """Get rookie data from local JSON file."""
        try:
            data_dir = Path(__file__).parent.parent.parent / "data"
            rookie_file = data_dir / "rookies.json"
            
            if not rookie_file.exists():
                logger.error(f"Rookie data file not found: {rookie_file}")
                return []
            
            with open(rookie_file, 'r') as f:
                rookie_data = json.load(f)
            
            return rookie_data.get('rookies', [])
            
        except Exception as e:
            logger.error(f"Error reading rookie data: {str(e)}")
            return []

    async def _sleep_random(self) -> None:
        """Sleep for a random duration to implement rate limiting."""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
        
    async def _request_with_backoff(self, url: str, max_retries: int = 3) -> requests.Response:
        """Make HTTP request with exponential backoff for rate limiting."""
        # Check if circuit breaker is open
        if self.circuit_breaker.is_open():
            raise Exception("Circuit breaker is open. Too many failed requests recently.")
            
        for attempt in range(max_retries):
            try:
                response = requests.get(url)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                if hasattr(e, 'response') and e.response.status_code == 429 and attempt < max_retries - 1:
                    # Record rate limit event in circuit breaker
                    self.circuit_breaker.record_failure()
                    
                    wait_time = (2 ** attempt) * self.min_delay
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry. Attempt {attempt+1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                else:
                    if hasattr(e, 'response') and e.response.status_code == 429:
                        # If we've exhausted retries and still getting rate limited, 
                        # record as failure and potentially open circuit breaker
                        self.circuit_breaker.record_failure()
                    raise
        
    async def _request_with_backoff(self, url: str, max_retries: int = 3) -> requests.Response:
        """Make HTTP request with exponential backoff for rate limiting."""
        for attempt in range(max_retries):
            try:
                response = requests.get(url)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * self.min_delay
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                else:
                    raise