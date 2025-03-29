# Fantasy Football Projections

A modern web application for creating and managing fantasy football player projections with support for statistical modeling, scenario planning, and team-level analysis.

## 🌟 Features

- **Advanced Statistical Modeling**: Enhanced projection system using historical data, team context, and refined efficiency metrics
- **Manual Override System**: Track and apply manual adjustments with automatic recalculation of dependent stats
- **Scenario Planning**: Create, clone, and compare multiple projection scenarios for what-if analysis
- **Team-Level Analysis**: Maintain mathematical consistency across team-level adjustments with fill player generation
- **Enhanced Metrics**: Net yardage calculations, fumble tracking, sack analysis, and detailed efficiency rates
- **Projection Uncertainty**: Statistical variance and confidence intervals for all projections
- **Rookie Projections**: Specialized rookie projection system with historical comps and team context
- **Player Comparison**: Side-by-side comparison tool with visualization and radar charts
- **Dashboard Analytics**: Comprehensive dashboard with projection insights and key metrics
- **Granular Controls**: Fine-tune individual player metrics and see real-time impacts
- **Batch Operations**: Apply changes to multiple players simultaneously
- **Modern Interface**: Intuitive React-based UI with real-time updates
- **Data Import Verification**: Robust validation for imported statistical data
- **Performance Optimization**: Caching and query optimization for fast response times

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Conda (recommended for environment management)
- Git

### Installation

1. Clone the repository:
```bash
git clone git@github.com:yourusername/fantasy-football-projections.git
cd fantasy-football-projections
```

2. Set up the Python backend:
```bash
conda env create -f backend/environment.yml
conda activate fantasy-football
```

3. Initialize the database:
```bash
python backend/database/init_db.py
```

4. Install frontend dependencies:
```bash
cd frontend
npm install
```

5. Optional: Import sample data:
```bash
cd backend/scripts
python upload_season.py --season 2024 --verify
```

### Running the Application

1. Start the backend server:
```bash
cd backend
uvicorn main:app --reload
```

2. Start the frontend development server:
```bash
cd frontend
npm run dev
```

The application will be available at `http://localhost:5173`

## 🏗️ Project Structure

```
fantasy-football-projections/
├── backend/                 # Python FastAPI backend
│   ├── api/                 # API routes and schemas
│   │   └── routes/          # API endpoint definitions
│   ├── database/            # Database models and connection
│   ├── services/            # Business logic and data processing
│   └── tests/               # Backend tests
├── frontend/                # React + TypeScript frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API client and data services
│   │   └── utils/           # Helper functions
│   └── public/              # Static assets
└── data/                    # Local database and data files
```

See `docs/structure.md` for a detailed project structure overview.

## 🔧 Technical Stack

### Backend
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- Pydantic (data validation)
- SQLite (database)
- Numpy/Pandas (data processing)
- Pytest (testing)

### Frontend
- React 18
- TypeScript
- React Router v6 (routing)
- Vite (build tool)
- shadcn/ui (component library)
- Recharts (data visualization)
- TailwindCSS (styling)
- Heroicons (icons)

## 📊 Statistical Model

The enhanced projection system uses a comprehensive statistical model that considers:

- Historical player performance with regression analysis
- Team offensive metrics with mathematical consistency
- Usage patterns and efficiency trends
- Advanced metrics like net yards, sack rates, fumble rates, etc.
- Position-specific modeling (QB, RB, WR, TE)
- Statistical reconciliation with fill players

See `docs/model.md` for detailed documentation of the statistical methodology.

## 🛠️ Development

### Code Style

#### Python
- Use Black for formatting
- Follow PEP 8 guidelines
- Type hints required for all functions
- Async/await pattern for service methods

#### TypeScript
- Use ESLint with TypeScript rules
- Prettier for formatting
- Strict TypeScript checks enabled
- Functional components with hooks

### Testing

#### Backend Tests
```bash
cd backend
python -m pytest tests/
```

For running a specific test:
```bash
python -m pytest tests/path/to/test_file.py::TestClass::test_method -v
```

#### Frontend Tests
```bash
cd frontend
npm test
```

## 📝 Documentation

- Backend API documentation: `http://localhost:8000/docs` and `docs/api_docs.md`
- Developer setup guide: See `docs/developer_setup.md`
- Projection methodology: See `docs/projection_methodology.md`
- User guide for scenario creation: See `docs/user_guide.md`
- Technical implementation details: See `docs/model.md`
- Database schema and models: See `backend/database/models.py`
- Project structure: See `docs/structure.md`
- Data import details: See `docs/Data Import Plan.md`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

Please follow our coding standards and include appropriate tests.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔍 New Features in v0.3.0

- **Projection Uncertainty**: Statistical variance and confidence intervals for all projections
- **Rookie Projection System**: Comprehensive rookie modeling with historical comparisons
- **Side-by-Side Comparison**: Advanced player comparison tool with multiple visualization options
- **Enhanced Dashboard**: Improved analytics dashboard with key performance indicators
- **Modern Navigation**: Comprehensive navigation structure with improved UX
- **Data Validation**: Robust validation and error correction for imported data
- **Performance Optimization**: Caching and query optimization for faster response times
- **Batch API Operations**: Enhanced batch operations for projection management
- **Data Export**: Export capabilities for projections in multiple formats

### Previous Features in v0.2.0

- **Enhanced Data Models**: Added support for net yardage, fumbles, sacks, and detailed efficiency metrics
- **Manual Override System**: New override tracking system with automatic dependent stat recalculation
- **Scenario Management**: Advanced scenario creation, cloning, and comparison capabilities
- **Fill Player System**: Automatic generation of fill players to maintain team-level stat consistency
- **API Enhancements**: New endpoints for managing overrides and scenarios
- **Batch Operations**: Ability to apply changes to multiple players at once

## 🐛 Known Issues and Future Improvements

### Current Limitations
- Single-user system (no authentication)
- Local SQLite database only
- Limited historical data import options
- Limited mobile responsiveness

### Recently Completed Features
- ✅ Enhanced rookie projection system
- ✅ Statistical variance and confidence intervals
- ✅ Data validation for imports
- ✅ Side-by-side player comparison
- ✅ Dashboard analytics view
- ✅ Modern navigation structure
- ✅ Performance optimizations (caching, query improvements)
- ✅ Batch operations and data export

### Planned Features
- Complete regression analysis implementation
- Multi-user support with authentication
- PostgreSQL database support
- Advanced statistical analysis tools
- Mobile responsive design
- Strength of schedule adjustments
- Improved team-level analytics
- API rate limiting
- Real-time collaborative features