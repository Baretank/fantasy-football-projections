import pytest
import uuid
from sqlalchemy.orm import Session
from backend.services.override_service import OverrideService
from backend.database.models import StatOverride, Projection, Player

class TestOverrideService:
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create OverrideService instance for testing."""
        return OverrideService(test_db)

    @pytest.fixture(scope="function")
    def sample_projection(self, test_db, sample_players):
        """Create a sample projection for testing overrides."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        
        projection = Projection(
            projection_id=str(uuid.uuid4()),
            player_id=mahomes_id,
            season=2024,
            games=17,
            half_ppr=350.5,
            
            # Passing stats
            pass_attempts=600,
            completions=400,
            pass_yards=4800,
            pass_td=38,
            interceptions=10,
            comp_pct=0.667,
            yards_per_att=8.0,
            pass_td_rate=0.063,
            int_rate=0.017,
            
            # Rushing stats
            carries=60,
            rush_yards=350,
            rush_td=3,
            yards_per_carry=5.83,
            rush_td_rate=0.05,
            
            # Usage metrics
            snap_share=0.99,
            
            # Other required values for recalculation
            sacks=25,
            sack_yards=175,
            net_pass_yards=4625,
            net_yards_per_att=7.71,
            has_overrides=False
        )
        
        test_db.add(projection)
        test_db.commit()
        
        return projection

    @pytest.mark.asyncio
    async def test_create_override(self, service, sample_projection):
        """Test creating a manual override."""
        # Test creating an override for pass attempts
        override = await service.create_override(
            player_id=sample_projection.player_id,
            projection_id=sample_projection.projection_id,
            stat_name="pass_attempts",
            manual_value=650,
            notes="Testing increased volume"
        )
        
        assert override is not None
        assert override.stat_name == "pass_attempts"
        assert override.calculated_value == 600
        assert override.manual_value == 650
        
        # Verify projection was updated with new value
        updated_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_projection.projection_id
        ).first()
        
        assert updated_proj.pass_attempts == 650
        assert updated_proj.has_overrides is True
        
        # Check that dependent stats were recalculated
        assert updated_proj.comp_pct < sample_projection.comp_pct  # Should decrease with more attempts
        assert updated_proj.yards_per_att < sample_projection.yards_per_att  # Should decrease with more attempts
        assert updated_proj.pass_td_rate < sample_projection.pass_td_rate  # Should decrease with more attempts

    @pytest.mark.asyncio
    async def test_dependent_stat_recalculation_qb(self, service, sample_projection):
        """Test recalculation of QB dependent stats."""
        # Override completions
        override = await service.create_override(
            player_id=sample_projection.player_id,
            projection_id=sample_projection.projection_id,
            stat_name="completions",
            manual_value=420,  # Increased from 400
            notes="Testing increased accuracy"
        )
        
        assert override is not None
        
        # Verify recalculation of comp_pct
        updated_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_projection.projection_id
        ).first()
        
        expected_comp_pct = 420 / 600  # 0.7
        assert round(updated_proj.comp_pct, 3) == round(expected_comp_pct, 3)
        
        # Reset for next test
        await service.delete_override(override.override_id)
        
        # Now test pass_td override
        override = await service.create_override(
            player_id=sample_projection.player_id,
            projection_id=sample_projection.projection_id,
            stat_name="pass_td",
            manual_value=45,  # Increased from 38
            notes="Testing increased scoring"
        )
        
        updated_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_projection.projection_id
        ).first()
        
        expected_td_rate = 45 / 600  # 0.075
        assert round(updated_proj.pass_td_rate, 3) == round(expected_td_rate, 3)
        assert updated_proj.half_ppr > sample_projection.half_ppr  # Fantasy points should increase

    @pytest.fixture(scope="function")
    def sample_rb_projection(self, test_db, sample_players):
        """Create a sample RB projection for testing overrides."""
        mccaffrey_id = sample_players["ids"]["Christian McCaffrey"]
        
        projection = Projection(
            projection_id=str(uuid.uuid4()),
            player_id=mccaffrey_id,
            season=2024,
            games=16,
            half_ppr=320.5,
            
            # Rushing stats
            carries=280,
            rush_yards=1400,
            rush_td=14,
            yards_per_carry=5.0,
            rush_td_rate=0.05,
            
            # Receiving stats
            targets=110,
            receptions=88,
            rec_yards=750,
            rec_td=5,
            catch_pct=0.8,
            yards_per_target=6.82,
            rec_td_rate=0.045,
            
            # Other stats
            fumbles=2,
            has_overrides=False
        )
        
        test_db.add(projection)
        test_db.commit()
        
        return projection

    @pytest.mark.asyncio
    async def test_dependent_stat_recalculation_rb(self, service, sample_rb_projection):
        """Test recalculation of RB dependent stats."""
        # Override carries
        override = await service.create_override(
            player_id=sample_rb_projection.player_id,
            projection_id=sample_rb_projection.projection_id,
            stat_name="carries",
            manual_value=320,  # Increased from 280
            notes="Testing increased volume"
        )
        
        assert override is not None
        
        # Verify recalculation of yards_per_carry
        updated_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_rb_projection.projection_id
        ).first()
        
        expected_ypc = 1400 / 320  # 4.375
        assert round(updated_proj.yards_per_carry, 3) == round(expected_ypc, 3)
        
        # Reset for next test
        await service.delete_override(override.override_id)
        
        # Now test receiving override for RB
        override = await service.create_override(
            player_id=sample_rb_projection.player_id,
            projection_id=sample_rb_projection.projection_id,
            stat_name="receptions",
            manual_value=95,  # Increased from 88
            notes="Testing increased reception count"
        )
        
        updated_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_rb_projection.projection_id
        ).first()
        
        expected_catch_pct = 95 / 110  # 0.864
        assert round(updated_proj.catch_pct, 3) == round(expected_catch_pct, 3)

    @pytest.fixture(scope="function")
    def sample_wr_projection(self, test_db, sample_players):
        """Create a sample WR projection for testing overrides."""
        kelce_id = sample_players["ids"]["Travis Kelce"]
        
        projection = Projection(
            projection_id=str(uuid.uuid4()),
            player_id=kelce_id,
            season=2024,
            games=16,
            half_ppr=245.0,
            
            # Receiving stats
            targets=140,
            receptions=98,
            rec_yards=1200,
            rec_td=10,
            catch_pct=0.7,
            yards_per_target=8.57,
            rec_td_rate=0.071,
            
            has_overrides=False
        )
        
        test_db.add(projection)
        test_db.commit()
        
        return projection

    @pytest.mark.asyncio
    async def test_dependent_stat_recalculation_receiver(self, service, sample_wr_projection):
        """Test recalculation of WR/TE dependent stats."""
        # Override targets
        override = await service.create_override(
            player_id=sample_wr_projection.player_id,
            projection_id=sample_wr_projection.projection_id,
            stat_name="targets",
            manual_value=160,  # Increased from 140
            notes="Testing increased target volume"
        )
        
        assert override is not None
        
        # Verify recalculation of catch_pct and yards_per_target
        updated_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_wr_projection.projection_id
        ).first()
        
        expected_catch_pct = 98 / 160  # 0.6125
        expected_ypt = 1200 / 160  # 7.5
        
        assert round(updated_proj.catch_pct, 3) == round(expected_catch_pct, 3)
        assert round(updated_proj.yards_per_target, 3) == round(expected_ypt, 3)
        
        # Now test rec_td override
        await service.delete_override(override.override_id)
        
        override = await service.create_override(
            player_id=sample_wr_projection.player_id,
            projection_id=sample_wr_projection.projection_id,
            stat_name="rec_td",
            manual_value=14,  # Increased from 10
            notes="Testing increased TDs"
        )
        
        updated_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_wr_projection.projection_id
        ).first()
        
        expected_td_rate = 14 / 140  # 0.1
        assert round(updated_proj.rec_td_rate, 3) == round(expected_td_rate, 3)
        assert updated_proj.half_ppr > sample_wr_projection.half_ppr  # Fantasy points should increase

    @pytest.mark.asyncio
    async def test_delete_override(self, service, sample_projection):
        """Test deleting an override and restoring original values."""
        # First create an override
        override = await service.create_override(
            player_id=sample_projection.player_id,
            projection_id=sample_projection.projection_id,
            stat_name="pass_yards",
            manual_value=5200,  # Increased from 4800
            notes="Testing delete functionality"
        )
        
        assert override is not None
        
        # Verify the override was applied
        updated_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_projection.projection_id
        ).first()
        
        assert updated_proj.pass_yards == 5200
        assert updated_proj.has_overrides is True
        
        # Now delete the override
        result = await service.delete_override(override.override_id)
        assert result is True
        
        # Verify the original value was restored
        restored_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_projection.projection_id
        ).first()
        
        assert restored_proj.pass_yards == 4800
        assert restored_proj.has_overrides is False  # No other overrides exist

    @pytest.mark.asyncio
    async def test_batch_override(self, service, sample_projection, sample_rb_projection, sample_wr_projection):
        """Test batch override functionality."""
        player_ids = [
            sample_projection.player_id,  # QB
            sample_rb_projection.player_id,  # RB
            sample_wr_projection.player_id  # TE
        ]
        
        # Test fixed value override (only should affect the QB)
        results = await service.batch_override(
            player_ids=player_ids,
            stat_name="pass_attempts",
            value=630,
            notes="Batch testing fixed value"
        )
        
        assert results is not None
        assert "results" in results
        
        # QBs should succeed, others should fail for QB-specific stat
        assert results["results"][sample_projection.player_id]["success"] is True
        assert results["results"][sample_rb_projection.player_id]["success"] is False
        assert results["results"][sample_wr_projection.player_id]["success"] is False
        
        # Now test percentage adjustment for a common stat like games
        results = await service.batch_override(
            player_ids=player_ids,
            stat_name="games",
            value={"method": "percentage", "amount": -10},  # 10% reduction
            notes="Batch testing percentage adjustment"
        )
        
        # Verify results
        for player_id in player_ids:
            assert results["results"][player_id]["success"] is True
            
        # Check that the games values were reduced by 10%
        qb_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_projection.projection_id
        ).first()
        
        rb_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_rb_projection.projection_id
        ).first()
        
        wr_proj = service.db.query(Projection).filter(
            Projection.projection_id == sample_wr_projection.projection_id
        ).first()
        
        assert qb_proj.games == 15  # 17 * 0.9 = 15.3, rounded down
        assert rb_proj.games == 14  # 16 * 0.9 = 14.4, rounded down
        assert wr_proj.games == 14  # 16 * 0.9 = 14.4, rounded down

    @pytest.mark.asyncio
    async def test_apply_overrides_to_projection(self, service, sample_projection):
        """Test applying multiple overrides to a projection."""
        # Create multiple overrides
        override1 = await service.create_override(
            player_id=sample_projection.player_id,
            projection_id=sample_projection.projection_id,
            stat_name="pass_attempts",
            manual_value=625,
            notes="First override"
        )
        
        override2 = await service.create_override(
            player_id=sample_projection.player_id,
            projection_id=sample_projection.projection_id,
            stat_name="pass_yards",
            manual_value=5100,
            notes="Second override"
        )
        
        # Create a fresh projection object
        fresh_proj = Projection(
            projection_id=sample_projection.projection_id,
            player_id=sample_projection.player_id,
            season=2024,
            games=17,
            half_ppr=350.5,
            pass_attempts=600,
            completions=400,
            pass_yards=4800,
            pass_td=38,
            interceptions=10,
            has_overrides=False
        )
        
        # Apply all overrides to this fresh projection
        updated_proj = await service.apply_overrides_to_projection(fresh_proj)
        
        # Verify both overrides were applied
        assert updated_proj.pass_attempts == 625
        assert updated_proj.pass_yards == 5100
        assert updated_proj.has_overrides is True
        
        # Cleanup
        await service.delete_override(override1.override_id)
        await service.delete_override(override2.override_id)