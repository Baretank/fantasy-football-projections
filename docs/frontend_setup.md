# Frontend Setup and Development Guide

This document provides comprehensive guidance for setting up and developing the frontend of the Fantasy Football Projections application.

## Environment Setup

### Requirements
- Node.js 18+ (LTS version recommended)
- npm 9+ or yarn 1.22+

### Installation

1. Clone the repository (if not already done):
   ```bash
   git clone https://github.com/your-repo/fantasy-football-projections.git
   cd fantasy-football-projections
   ```

2. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

## Development

### Start Development Server

To start the development server with hot-reload:

```bash
cd frontend
npm run dev
```

The application will be available at `http://localhost:5173` by default.

### Configuration

#### API Connection

The frontend connects to the backend API through a proxy configured in `vite.config.ts`:

```typescript
// frontend/vite.config.ts
export default defineConfig({
  // ...other config
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // Important: Use explicit IPv4 address
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
```

**Important**: Always use `127.0.0.1` explicitly (not `localhost` or `0.0.0.0`) to avoid IPv6/IPv4 mismatch issues.

### API Service

The application uses a centralized API service for all backend communication:

```typescript
// frontend/src/services/api.ts
import { API_BASE_URL } from '../config';

/**
 * Helper function for API requests
 */
async function fetchApi(
  endpoint: string, 
  method: string = 'GET', 
  body: any = null
): Promise<any> {
  // Ensure endpoint starts with a slash
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${normalizedEndpoint}`;
  
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
    // Important for CORS requests
    credentials: 'include',
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    
    // Log the URL being fetched for debugging
    console.debug(`Fetching from: ${url}`);
    
    // Check if the response is successful
    if (!response.ok) {
      console.error(`API error: ${response.status} ${response.statusText}`);
      const errorData = await response.text();
      console.error(`Error details: ${errorData}`);
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    // Check if response has content
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    } else {
      return await response.text();
    }
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}
```

## Project Structure

The frontend follows a modular architecture:

```
frontend/
├── public/               # Static assets
├── src/
│   ├── assets/           # Images, fonts, etc.
│   ├── components/       # Reusable UI components
│   │   ├── common/       # Shared components (buttons, inputs, etc.)
│   │   ├── layout/       # Layout components (header, sidebar, etc.)
│   │   ├── players/      # Player-related components
│   │   ├── projections/  # Projection visualization components
│   │   ├── scenarios/    # Scenario management components
│   │   └── draft/        # Draft day tool components
│   ├── hooks/            # Custom React hooks
│   ├── pages/            # Page components
│   ├── services/         # API and data services
│   ├── store/            # State management
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utility functions
│   ├── App.tsx           # Main application component
│   ├── main.tsx          # Application entry point
│   └── vite-env.d.ts     # Vite environment types
├── .eslintrc.js          # ESLint configuration
├── .prettierrc           # Prettier configuration
├── index.html            # HTML entry point
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
└── vite.config.ts        # Vite configuration
```

## Styling

The application uses Tailwind CSS for styling:

```bash
# Install Tailwind CSS if not already installed
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Configure Tailwind in `tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          // ... other shades
          900: '#0c4a6e',
        },
        // ... other color definitions
      },
    },
  },
  plugins: [],
}
```

## TypeScript Types

The application uses comprehensive TypeScript types for API data:

```typescript
// src/types/index.ts

export interface Player {
  player_id: string;
  name: string;
  team: string;
  position: 'QB' | 'RB' | 'WR' | 'TE';
  status?: string;
  height?: number;
  weight?: number;
  created_at: string;
  updated_at: string;
}

export interface Projection {
  projection_id: string;
  player_id: string;
  scenario_id?: string;
  season: number;
  games: number;
  half_ppr: number;
  
  // QB stats
  pass_attempts?: number;
  completions?: number;
  pass_yards?: number;
  pass_td?: number;
  interceptions?: number;
  
  // RB/WR/TE stats
  rush_attempts?: number;
  rush_yards?: number;
  rush_td?: number;
  targets?: number;
  receptions?: number;
  rec_yards?: number;
  rec_td?: number;
  
  // Calculated stats
  completion_percentage?: number;
  yards_per_attempt?: number;
  td_percentage?: number;
  yards_per_rush?: number;
  catch_rate?: number;
  yards_per_reception?: number;
}

export interface Scenario {
  scenario_id: string;
  name: string;
  description?: string;
  is_baseline: boolean;
  season: number;
  parameters: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// More interfaces...
```

## Building for Production

To build the application for production:

```bash
cd frontend
npm run build
```

The build output will be in the `dist` directory.

## Testing

### Unit Tests

Run unit tests with Jest:

```bash
npm test
```

### Component Tests

Run component tests with React Testing Library:

```bash
npm run test:component
```

### E2E Tests

Run end-to-end tests with Cypress:

```bash
npm run cypress:open
```

## Troubleshooting

### Common Frontend Issues

1. **API Connection Issues**:
   - Check browser console for network errors
   - Verify backend is running on correct port (8000)
   - Ensure vite.config.ts is using explicit IPv4 address (127.0.0.1)
   - Add `credentials: 'include'` to fetch options

2. **Component Rendering Issues**:
   - Check for null/undefined values in data
   - Use optional chaining (`?.`) when accessing nested properties
   - Implement loading states for asynchronous data

3. **TypeScript Errors**:
   - Update type definitions when API changes
   - Use type assertions cautiously where necessary
   - Keep type definitions in sync with backend models

## Network Debugging Tools

For debugging network connectivity issues, use the included test page:

```html
<!-- frontend/test-cors.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CORS Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        button { padding: 10px; margin: 5px; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>API Connectivity Test</h1>
    
    <div>
        <h2>1. Test Direct API Access</h2>
        <button id="testDirectAPI">Test Direct API</button>
        <pre id="resultDirect">Results will appear here...</pre>
    </div>
    
    <div>
        <h2>2. Test Proxy API Access</h2>
        <button id="testProxyAPI">Test Proxy API</button>
        <pre id="resultProxy">Results will appear here...</pre>
    </div>
    
    <script>
        document.getElementById('testDirectAPI').addEventListener('click', async () => {
            const resultEl = document.getElementById('resultDirect');
            resultEl.innerHTML = 'Testing direct API call...';
            
            try {
                // Try direct access to backend
                const url = 'http://127.0.0.1:8000/api/scenarios';
                console.log(`Making direct fetch request to: ${url}`);
                
                const response = await fetch(url, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    resultEl.innerHTML = `Error: ${response.status} ${response.statusText}`;
                    return;
                }
                
                const data = await response.json();
                resultEl.innerHTML = `Success! Found ${data.length} scenarios:\n${JSON.stringify(data, null, 2)}`;
            } catch (error) {
                resultEl.innerHTML = `Error: ${error.message}`;
                console.error('Direct API test error:', error);
            }
        });
        
        document.getElementById('testProxyAPI').addEventListener('click', async () => {
            const resultEl = document.getElementById('resultProxy');
            resultEl.innerHTML = 'Testing proxy API call...';
            
            try {
                // Try access through Vite proxy
                const url = '/api/scenarios';
                console.log(`Making proxy fetch request to: ${url}`);
                
                const response = await fetch(url, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    resultEl.innerHTML = `Error: ${response.status} ${response.statusText}`;
                    return;
                }
                
                const data = await response.json();
                resultEl.innerHTML = `Success! Found ${data.length} scenarios:\n${JSON.stringify(data, null, 2)}`;
            } catch (error) {
                resultEl.innerHTML = `Error: ${error.message}`;
                console.error('Proxy API test error:', error);
            }
        });
    </script>
</body>
</html>
```

## Resources

- [React Documentation](https://reactjs.org/docs/getting-started.html)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [Vite Documentation](https://vitejs.dev/guide/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)