# Fantasy Football Projections - Frontend

This is the frontend for the Fantasy Football Projections application. It provides a user interface to interact with the projection system, allowing users to view, adjust, and compare football player projections.

## Features

- **Dashboard**: Overview of projection data with visualizations
- **Player Projections**: Detailed view and adjustment of individual player projections
- **Scenario Manager**: Create and compare different "what-if" scenarios
- **Team Adjustments**: Apply team-level adjustments to all players on a team

## Technologies Used

- **React**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework
- **Radix UI**: Accessible component primitives
- **Recharts**: Charting library for data visualization

## Getting Started

### Prerequisites

- Node.js (v16+)
- npm or yarn

### Installation

1. Install dependencies:
   ```
   npm install
   ```

2. Start the development server:
   ```
   npm run dev
   ```

3. Build for production:
   ```
   npm run build
   ```

## Project Structure

- `/src` - Source code
  - `/components` - React components
    - `/ui` - Reusable UI components
  - `/services` - API services for backend communication
  - `/types` - TypeScript type definitions
  - `/lib` - Utility functions
  - `/utils` - Helper utilities

## API Integration

The frontend communicates with the FastAPI backend through the services defined in `/src/services/api.ts`. The API provides endpoints for:

- Player data
- Projection data
- Scenario management
- Statistical overrides

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Submit a pull request

## License

This project is licensed under the MIT License.