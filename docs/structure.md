fantasy-football-projections/
├── README.md
├── .gitignore
├── package.json
├── tsconfig.json
│
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── environment.yml                 # Conda config
│   ├── database/
│   │   ├── __init__.py
│   │   ├── init_db.py
│   │   ├── models.py          # SQLAlchemy models
│   │   └── database.py        # Database connection
│   ├── api/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── players.py
│   │       └── projections.py
│   ├── scripts/
│   │   └── import_data.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── projection_service.py
│   │   ├── data_import_service.py
│   │   └── data_service.py
│   └── tests/
│       ├── __init__.py
│       └── test_projections.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── playerselect.tsx
│   │   │   ├── counter.ts
│   │   │   ├── projectionadjuster.tsx
│   │   │   └── statdisplay.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── utils/
│   │   │   └── calculations.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   │   └── index.html
│   ├── index.html
│   ├── tsconfig.node.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── package.json
│
│
└── data/
    └── sqlite.db              # Local SQLite database

