# Fantasy Football Data Import: Final MVP Implementation Plan

## 1. Database Updates

### Add GameStats Model (backend/database/models.py)
```python
class GameStats(Base):
    __tablename__ = "game_stats"
    
    game_stat_id = Column(String, primary_key=True)
    player_id = Column(String, ForeignKey("players.player_id"))
    season = Column(Integer)
    week = Column(Integer)
    stats = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    player = relationship("Player", back_populates="game_stats")

# Add to Player model:
game_stats = relationship("GameStats", back_populates="player")
```

## 2. Import Service

### DataImportService (backend/services/data_import_service.py)
```python
class DataImportService:
    def __init__(self, db: Session):
        self.db = db
        self.min_delay = 0.8  # 800ms minimum
        self.max_delay = 1.2  # 1.2s maximum
        
    async def import_position_group(self, position: str, season: int) -> Tuple[int, List[str]]:
        """Import all players for a specific position"""
        players = self._get_players_by_position(position, season)
        success_count = 0
        failed_players = []
        
        for idx, player in enumerate(players, 1):
            print(f"Importing {position} {idx}/{len(players)}: {player['name']}")
            
            if await self._player_exists(player['name'], season):
                print(f"Skipping {player['name']}, already imported")
                success_count += 1
                continue
                
            try:
                game_log = player_game_log.get_player_game_log(
                    player=player['name'],
                    position=position,
                    season=season
                )
                
                await self._store_game_logs(player['name'], position, game_log)
                await self._aggregate_to_season_stats(player['name'], season)
                
                success_count += 1
                
                # Rate limiting
                delay = random.uniform(self.min_delay, self.max_delay)
                await asyncio.sleep(delay)
                
            except Exception as e:
                print(f"Failed to import {player['name']}: {str(e)}")
                failed_players.append(player['name'])
                
        return success_count, failed_players
```

## 3. Upload Script

### scripts/upload_season.py
```python
async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, default=2023)
    parser.add_argument('--position', choices=['QB', 'RB', 'WR', 'TE'])
    args = parser.parse_args()
    
    db = SessionLocal()
    service = DataImportService(db)
    
    try:
        positions = [args.position] if args.position else ['QB', 'RB', 'WR', 'TE']
        
        for position in positions:
            start_time = time.time()
            print(f"\nStarting {position} imports...")
            
            success_count, failed = await service.import_position_group(
                position, args.season
            )
            
            duration = time.time() - start_time
            print(f"\n{position} Import Complete:")
            print(f"Duration: {duration:.1f} seconds")
            print(f"Successfully imported: {success_count} players")
            
            if failed:
                print(f"\nFailed {position} imports:")
                for player in failed:
                    print(f"- {player}")
                with open(f'failed_{position.lower()}_imports.txt', 'w') as f:
                    f.write('\n'.join(failed))
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. Basic Test Suite

### test_data_import.py
```python
class TestDataImport:
    @pytest.mark.asyncio
    async def test_position_import(self, import_service):
        """Test importing a small set of QBs"""
        success_count, failed = await import_service.import_position_group(
            "QB", 2023
        )
        
        assert success_count > 0, "No players imported"
        assert len(failed) == 0, f"Players failed to import: {failed}"
        
        # Verify game logs exist
        qb_stats = import_service.db.query(GameStats).join(Player).filter(
            Player.position == "QB"
        ).all()
        
        assert len(qb_stats) > 0, "No game stats found"
```

## 5. Expected Timings

Position-based import times (approximate):
- QBs (50 players): ~1 minute
- RBs (100 players): ~2 minutes
- WRs (150 players): ~3 minutes
- TEs (100 players): ~2 minutes

Total runtime: ~8-10 minutes for full import

## 6. Implementation Steps

1. Database Setup (Day 1)
   - Add GameStats model
   - Run migrations
   - Verify schema

2. Core Implementation (Day 1-2)
   - Implement DataImportService
   - Create upload script
   - Basic test with 2-3 players

3. Initial Testing (Day 2)
   - Test QB import
   - Verify data accuracy
   - Check rate limiting

4. Full Import (Day 2-3)
   - Run complete import
   - Verify totals
   - Document any issues

## 7. Success Criteria

1. Complete import under 30 minutes
2. Game logs stored for each player
3. Season totals accurate
4. Failed imports logged for retry
5. No rate limiting issues with PFR

This plan provides:
- Position-based organization
- Reasonable rate limiting
- Progress visibility
- Simple error recovery
- Minimal but sufficient testing

Would you like me to begin implementing any specific part?