import sys
from pathlib import Path
import logging

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.database import SessionLocal
from backend.database.models import RookieProjectionTemplate
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_rookie_templates():
    """Initialize default rookie projection templates by position and draft position."""
    db = SessionLocal()
    try:
        # Check if we already have templates
        existing = db.query(RookieProjectionTemplate).count()
        if existing > 0:
            logger.info(f"Found {existing} existing templates. Skipping initialization.")
            return
        
        # Create QB templates
        qb_templates = [
            # Top QB (picks 1-10)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="QB",
                draft_round=1,
                draft_pick_min=1,
                draft_pick_max=10,
                games=16.0,
                snap_share=0.80,
                pass_attempts=520,
                comp_pct=0.62,
                yards_per_att=7.2,
                pass_td_rate=0.04,
                int_rate=0.03,
                rush_att_per_game=4.0,
                rush_yards_per_att=5.0,
                rush_td_per_game=0.2
            ),
            # Round 1 QB (picks 11-32)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="QB",
                draft_round=1,
                draft_pick_min=11,
                draft_pick_max=32,
                games=12.0,
                snap_share=0.60,
                pass_attempts=380,
                comp_pct=0.60,
                yards_per_att=6.8,
                pass_td_rate=0.03,
                int_rate=0.035,
                rush_att_per_game=3.5,
                rush_yards_per_att=4.5,
                rush_td_per_game=0.15
            ),
            # Round 2-3 QB (picks 33-105)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="QB",
                draft_round=2,
                draft_pick_min=33,
                draft_pick_max=105,
                games=6.0,
                snap_share=0.30,
                pass_attempts=180,
                comp_pct=0.58,
                yards_per_att=6.5,
                pass_td_rate=0.025,
                int_rate=0.04,
                rush_att_per_game=2.5,
                rush_yards_per_att=4.0,
                rush_td_per_game=0.1
            ),
            # Day 3 QB (picks 106-262)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="QB",
                draft_round=4,
                draft_pick_min=106,
                draft_pick_max=262,
                games=2.0,
                snap_share=0.10,
                pass_attempts=60,
                comp_pct=0.55,
                yards_per_att=6.0,
                pass_td_rate=0.02,
                int_rate=0.045,
                rush_att_per_game=1.5,
                rush_yards_per_att=3.5,
                rush_td_per_game=0.05
            )
        ]
        
        # Create RB templates
        rb_templates = [
            # Top RB (picks 1-32)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="RB",
                draft_round=1,
                draft_pick_min=1,
                draft_pick_max=32,
                games=15.0,
                snap_share=0.65,
                rush_att_per_game=14.0,
                rush_yards_per_att=4.4,
                rush_td_per_att=0.03,
                targets_per_game=3.5,
                catch_rate=0.75,
                rec_yards_per_catch=8.0,
                rec_td_per_catch=0.04
            ),
            # Round 2 RB (picks 33-64)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="RB",
                draft_round=2,
                draft_pick_min=33,
                draft_pick_max=64,
                games=14.0,
                snap_share=0.55,
                rush_att_per_game=11.0,
                rush_yards_per_att=4.2,
                rush_td_per_att=0.025,
                targets_per_game=3.0,
                catch_rate=0.70,
                rec_yards_per_catch=7.5,
                rec_td_per_catch=0.03
            ),
            # Round 3-4 RB (picks 65-140)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="RB",
                draft_round=3,
                draft_pick_min=65,
                draft_pick_max=140,
                games=13.0,
                snap_share=0.40,
                rush_att_per_game=7.0,
                rush_yards_per_att=4.0,
                rush_td_per_att=0.02,
                targets_per_game=2.0,
                catch_rate=0.65,
                rec_yards_per_catch=7.0,
                rec_td_per_catch=0.02
            ),
            # Late RB (picks 141-262)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="RB",
                draft_round=5,
                draft_pick_min=141,
                draft_pick_max=262,
                games=10.0,
                snap_share=0.25,
                rush_att_per_game=4.0,
                rush_yards_per_att=3.8,
                rush_td_per_att=0.015,
                targets_per_game=1.0,
                catch_rate=0.60,
                rec_yards_per_catch=6.5,
                rec_td_per_catch=0.01
            )
        ]
        
        # Create WR templates
        wr_templates = [
            # Top WR (picks 1-15)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="WR",
                draft_round=1,
                draft_pick_min=1,
                draft_pick_max=15,
                games=16.0,
                snap_share=0.80,
                targets_per_game=7.0,
                catch_rate=0.65,
                rec_yards_per_catch=13.5,
                rec_td_per_catch=0.07,
                rush_att_per_game=0.5,
                rush_yards_per_att=8.0,
                rush_td_per_att=0.03
            ),
            # Round 1 WR (picks 16-32)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="WR",
                draft_round=1,
                draft_pick_min=16,
                draft_pick_max=32,
                games=15.0,
                snap_share=0.70,
                targets_per_game=6.0,
                catch_rate=0.63,
                rec_yards_per_catch=13.0,
                rec_td_per_catch=0.06,
                rush_att_per_game=0.4,
                rush_yards_per_att=7.5,
                rush_td_per_att=0.025
            ),
            # Round 2 WR (picks 33-64)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="WR",
                draft_round=2,
                draft_pick_min=33,
                draft_pick_max=64,
                games=14.0,
                snap_share=0.60,
                targets_per_game=5.0,
                catch_rate=0.62,
                rec_yards_per_catch=12.5,
                rec_td_per_catch=0.05,
                rush_att_per_game=0.3,
                rush_yards_per_att=7.0,
                rush_td_per_att=0.02
            ),
            # Round 3-4 WR (picks 65-140)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="WR",
                draft_round=3,
                draft_pick_min=65,
                draft_pick_max=140,
                games=13.0,
                snap_share=0.40,
                targets_per_game=3.5,
                catch_rate=0.60,
                rec_yards_per_catch=12.0,
                rec_td_per_catch=0.04,
                rush_att_per_game=0.2,
                rush_yards_per_att=6.0,
                rush_td_per_att=0.01
            ),
            # Late WR (picks 141-262)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="WR",
                draft_round=5,
                draft_pick_min=141,
                draft_pick_max=262,
                games=10.0,
                snap_share=0.25,
                targets_per_game=2.0,
                catch_rate=0.58,
                rec_yards_per_catch=11.0,
                rec_td_per_catch=0.03,
                rush_att_per_game=0.1,
                rush_yards_per_att=5.0,
                rush_td_per_att=0.005
            )
        ]
        
        # Create TE templates
        te_templates = [
            # Top TE (picks 1-32)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="TE",
                draft_round=1,
                draft_pick_min=1,
                draft_pick_max=32,
                games=15.0,
                snap_share=0.70,
                targets_per_game=5.0,
                catch_rate=0.68,
                rec_yards_per_catch=11.0,
                rec_td_per_catch=0.08,
                rush_att_per_game=0.0,
                rush_yards_per_att=0.0,
                rush_td_per_att=0.0
            ),
            # Round 2-3 TE (picks 33-105)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="TE",
                draft_round=2,
                draft_pick_min=33,
                draft_pick_max=105,
                games=14.0,
                snap_share=0.60,
                targets_per_game=3.5,
                catch_rate=0.65,
                rec_yards_per_catch=10.5,
                rec_td_per_catch=0.06,
                rush_att_per_game=0.0,
                rush_yards_per_att=0.0,
                rush_td_per_att=0.0
            ),
            # Late TE (picks 106-262)
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="TE",
                draft_round=4,
                draft_pick_min=106,
                draft_pick_max=262,
                games=12.0,
                snap_share=0.40,
                targets_per_game=2.0,
                catch_rate=0.60,
                rec_yards_per_catch=9.5,
                rec_td_per_catch=0.04,
                rush_att_per_game=0.0,
                rush_yards_per_att=0.0,
                rush_td_per_att=0.0
            )
        ]
        
        # Add all templates to database
        for template in qb_templates + rb_templates + wr_templates + te_templates:
            db.add(template)
            
        db.commit()
        logger.info(f"Successfully initialized {len(qb_templates) + len(rb_templates) + len(wr_templates) + len(te_templates)} rookie templates")
        
    except Exception as e:
        logger.error(f"Error initializing rookie templates: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Initializing rookie projection templates")
    initialize_rookie_templates()