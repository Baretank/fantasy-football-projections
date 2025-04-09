# Remote Access Setup Guide with ngrok

This guide outlines how to set up remote access to your locally running Fantasy Football Projections application using ngrok. This allows you to access your frontend application from any device on any network.

## Prerequisites

- ngrok account (paid tier recommended for persistent sessions)
- Fantasy Football Projections application running locally
- Basic command line knowledge

## Step 1: Install ngrok

1. Sign up for an account at [ngrok.com](https://ngrok.com)
2. Download ngrok for your operating system
3. Extract the ngrok executable to a convenient location
4. Authenticate your ngrok installation:

```bash
./ngrok authtoken YOUR_AUTH_TOKEN
```

Replace `YOUR_AUTH_TOKEN` with the token provided in your ngrok dashboard.

## Step 2: Configure Your Application

Ensure your frontend and backend are configured correctly:

1. Verify your Vite configuration includes API proxying:

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // other aliases...
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

2. Ensure your API client is using relative URLs:

```typescript
// frontend/src/services/api.ts
const API_BASE_URL = '/api'; // Use relative URL instead of absolute
```

## Step 3: Start Your Services

1. Start your backend server:

```bash
cd backend
uvicorn main:app --reload
```

2. Start your frontend application:

```bash
cd frontend
npm run dev
```

Verify that both services are running correctly locally.

## Step 4: Create ngrok Tunnel

Create a tunnel to your frontend application:

```bash
ngrok http 5173
```

The command output will display your public ngrok URL, which will look something like:
```
Forwarding https://8a1b2c3d4.ngrok.io -> http://localhost:5173
```

## Step 5: Access Your Application

1. Use the provided ngrok URL in any browser from any network
2. API calls will be proxied through the Vite dev server to your local backend
3. You can now interact with the application as if you were accessing it locally

## Handling Backend API Requests

With the configuration above, API requests are handled as follows:

1. Browser makes request to `https://8a1b2c3d4.ngrok.io/api/players`
2. ngrok routes this to `http://localhost:5173/api/players`
3. The Vite dev server proxies `/api/players` to `http://localhost:8000/api/players`
4. Your FastAPI backend processes the request and returns the response
5. The response follows the reverse path back to the browser

## Paid Tier Benefits

With a paid ngrok plan:

- **Reserved Domains**: Get a consistent URL that doesn't change between sessions
- **Longer Sessions**: No 2-hour session limit
- **Multiple Tunnels**: Run multiple tunnels simultaneously
- **IP Restrictions**: Restrict access to trusted IP addresses
- **Custom Domains**: Use your own domain name

## Troubleshooting

1. **API Calls Failing**: Ensure your backend is running and the proxy configuration is correct
2. **ngrok Disconnections**: With paid tier, this shouldn't happen; otherwise, restart ngrok
3. **CORS Issues**: Check that your backend allows requests from the ngrok domain

## Security Considerations

1. ngrok URLs are publicly accessible by default
2. Consider enabling ngrok's authentication feature for additional security
3. For sensitive data, consider IP restrictions (paid feature)
4. This setup is for development/testing and not recommended for production use

## Next Steps

After confirming that remote access works, consider:

1. Setting up a more permanent solution for production
2. Implementing proper authentication for your application
3. Configuring a database that can be accessed securely from multiple locations