# TSX Compiler Service

Fast, secure compilation service for AI-generated React/TSX components.

## Overview

This microservice compiles AI-generated TSX source code into executable JavaScript bundles using esbuild. It validates source code for security issues before compilation and returns both JS and CSS outputs.

## Features

- **Fast Compilation**: Uses esbuild for sub-2s compilation times
- **Security Validation**: Blocks dangerous imports and APIs
- **CSS Extraction**: Automatically extracts and returns CSS
- **Error Handling**: Returns structured errors for AI self-correction
- **Production Ready**: Dockerized with health checks

## API Endpoints

### POST /compile

Compile TSX source code to JavaScript bundle.

**Request:**
```json
{
  "sourceCode": "export default function...",
  "componentName": "LandingPage",
  "siteId": "site_123"
}
```

**Response (Success):**
```json
{
  "success": true,
  "bundleCode": "/* compiled JS */",
  "cssCode": "/* extracted CSS */"
}
```

**Response (Validation Error):**
```json
{
  "success": false,
  "error": "Source code validation failed",
  "validationErrors": [
    "Dangerous import detected: fs",
    "Forbidden API usage detected: eval"
  ]
}
```

**Response (Compilation Error):**
```json
{
  "success": false,
  "error": "Compilation failed: Unexpected token..."
}
```

### GET /health

Check service health.

**Response:**
```json
{
  "status": "ok",
  "compiler": "available",
  "timestamp": "2026-07-16T12:00:00.000Z"
}
```

## Security

The service validates all source code to prevent:

- Dangerous imports: `fs`, `child_process`, `http`, `net`, etc.
- External URL imports: `import x from "https://..."`
- Relative imports outside directory: `import x from "../../..."`
- Forbidden APIs: `eval`, `Function()`, `fetch()`, `XMLHttpRequest`, `WebSocket`
- Inline scripts: `<script>` tags

## Development

### Prerequisites

- Node.js 20+
- npm or yarn

### Setup

```bash
cd apps/compiler
npm install
```

### Run Development Server

```bash
npm run dev
```

Server starts at http://localhost:3001

### Build for Production

```bash
npm run build
npm start
```

### Environment Variables

```bash
PORT=3001              # Server port
HOST=0.0.0.0          # Server host
NODE_ENV=production   # Environment
LOG_LEVEL=info        # Logging level
```

## Docker

### Build Image

```bash
docker build -t lenquant-compiler .
```

### Run Container

```bash
docker run -p 3001:3001 \
  -e NODE_ENV=production \
  -e PORT=3001 \
  lenquant-compiler
```

## Integration

The backend calls this service via the `CompilerClient`:

```python
from app.core.compiler_client import get_compiler_client

compiler = get_compiler_client()
result = await compiler.compile_tsx(
    source_code=tsx_code,
    component_name="GeneratedSite",
    site_id="site_123"
)

if result["success"]:
    bundle_url = await upload_to_storage(result["bundleCode"])
    site.compiledBundleUrl = bundle_url
    site.compilationStatus = "success"
else:
    site.compilationStatus = "failed"
    site.compilationError = result["error"]
```

## Architecture

```
┌─────────────┐
│   Backend   │
│  (Python)   │
└──────┬──────┘
       │ HTTP POST /compile
       │
┌──────▼──────┐
│  Compiler   │
│  (Node.js)  │
│             │
│  ┌────────┐ │
│  │validate│ │  Security checks
│  └───┬────┘ │
│      │      │
│  ┌───▼────┐ │
│  │esbuild │ │  Fast compilation
│  └───┬────┘ │
│      │      │
│  ┌───▼────┐ │
│  │ bundle │ │  JS + CSS output
│  └────────┘ │
└─────────────┘
```

## Testing

### Manual Test

```bash
curl -X POST http://localhost:3001/compile \
  -H "Content-Type: application/json" \
  -d '{
    "sourceCode": "export default function Test() { return <div>Hello</div>; }",
    "componentName": "Test",
    "siteId": "test_123"
  }'
```

### Health Check

```bash
curl http://localhost:3001/health
```

## Performance

- **Compilation Time**: < 2 seconds for typical components
- **Memory Usage**: ~50-100MB per compilation
- **Concurrency**: Handles multiple requests in parallel

## Troubleshooting

### Compilation Timeout

Increase the timeout in `compiler_client.py`:
```python
self.timeout = 60.0  # Default is 30.0
```

### Connection Refused

Check that:
1. Compiler service is running
2. Port 3001 is not blocked
3. `COMPILER_SERVICE_URL` env var is correct

### Validation Errors

Review the `validationErrors` array in the response. Common issues:
- Using `import fs from "fs"` (blocked for security)
- Using `eval()` or `Function()` (blocked for security)
- Missing default export (required)

## License

Internal use only - Part of LenQuant platform.
