# Fantasy Football Projections

A modern web application for creating and managing fantasy football player projections with support for statistical modeling, scenario planning, and team-level analysis.

## 🌟 Features

- **Statistical Modeling**: Advanced projection system using historical data and team context
- **Scenario Planning**: Create and compare multiple projection scenarios
- **Team-Level Analysis**: Maintain mathematical consistency across team-level adjustments
- **Granular Controls**: Fine-tune individual player metrics and see real-time impacts
- **Data Consistency**: Automated validation and mathematical consistency checks
- **Modern Interface**: Intuitive React-based UI with real-time updates

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Conda (recommended for environment management)

### Installation

1. Clone the repository:
```bash
git clone git@github.com:yourusername/fantasy-football-projections.git
cd fantasy-football-projections
```

2. Set up the Python backend:
```bash
conda env create -f environment.yml
conda activate fantasy-football
```

3. Initialize the database:
```bash
python backend/scripts/init_db.py
```

4. Install frontend dependencies:
```bash
cd frontend
npm install
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
│   ├── api/                # API routes and schemas
│   ├── database/           # Database models and connection
│   ├── services/           # Business logic and data processing
│   └── tests/              # Backend tests
├── frontend/               # React + TypeScript frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API client and data services
│   │   └── utils/          # Helper functions
│   └── public/             # Static assets
└── data/                   # Local database and data files
```

See `structure.md` for a detailed project structure overview.

## 🔧 Technical Stack

### Backend
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- Pydantic (data validation)
- SQLite (database)

### Frontend
- React 18
- TypeScript
- Vite (build tool)
- shadcn/ui (component library)
- Recharts (data visualization)
- TailwindCSS (styling)

## 📊 Statistical Model

The projection system uses a comprehensive statistical model that considers:

- Historical player performance
- Team offensive metrics
- Usage patterns
- Efficiency metrics
- Scoring rates

See `model.md` for detailed documentation of the statistical methodology.

## 🛠️ Development

### Code Style

#### Python
- Use Black for formatting
- Follow PEP 8 guidelines
- Type hints required for all functions

#### TypeScript
- Use ESLint with TypeScript rules
- Prettier for formatting
- Strict TypeScript checks enabled

### Testing

#### Backend Tests
```bash
pytest backend/tests/
```

#### Frontend Tests
```bash
cd frontend
npm test
```

## 📝 Documentation

- Backend API documentation: `http://localhost:8000/docs`
- Technical implementation details: See `implementation.md`
- Database schema and models: See `backend/database/models.py`
- Frontend component documentation: See component files

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

Please follow our coding standards and include appropriate tests.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔍 Implementation Notes

For detailed information about the implementation:
- Statistical methodology: See `model.md`
- Implementation plan: See `implementation.md`
- Project structure: See `structure.md`

## 🐛 Known Issues and Future Improvements

### Current Limitations
- Single-user system (no authentication)
- Local SQLite database only
- Limited historical data import options

### Planned Features
- Multi-user support with authentication
- PostgreSQL database support
- Advanced statistical analysis tools
- Bulk data import/export
- API rate limiting
- Real-time collaborative features
