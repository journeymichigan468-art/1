# Production-Safe Master Agent System

This project now provides a secure backend proxy for AI execution while keeping the existing frontend UI unchanged.

## Architecture

- Static frontend served from `public/`
- Express backend API in `server/`
- Server-side AI execution through Gemini API (`AI_API_KEY` in env)
- JWT-style authentication (signed server-side)
- Rate limiting + role-based quota enforcement
- Server-side execution logging

## Project Structure

```
server/
  index.js
  routes/agent.js
  services/aiService.js
  middleware/
    auth.js
    rateLimiter.js
    usageQuota.js
  utils/encryption.js
public/
  index.html
  styles.css
server.js
```

## Environment Variables

Copy `.env.example` and set values in your deployment environment:

- `AI_API_KEY`: Gemini API key (server-side only)
- `JWT_SECRET`: secret used to sign and verify JWT tokens
- `PORT`: server port (optional, defaults to `5000`)

## API Endpoints

- `POST /api/auth/token`
  - Body: `{ "userId": "u_123", "role": "free|pro|admin" }`
  - Returns a signed token for testing/integration.
- `POST /api/execute`
  - Headers: `Authorization: Bearer <token>`
  - Body: `{ "subtask": "...", "systemPrompt": "..." }`
  - Executes AI call through backend proxy.

## Run

```bash
npm start
```

Then open `http://localhost:5000`.
