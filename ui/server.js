import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 8080;
const API_TARGET = process.env.HALA_API_BASE || 'http://localhost:8000';
// Note: ws://localhost:8000/ws/chat/v2 is the target, but the proxy middleware handles the base
const WS_TARGET = process.env.HALA_WS_BASE || 'http://localhost:8000';

console.log(`Starting HalaAI UI Server...`);
console.log(`Proxying API requests to: ${API_TARGET}`);

// Proxy API requests to the Hala engine
// The UI calls /api/sessions -> Proxies to ${API_TARGET}/data/sessions
app.use('/api', createProxyMiddleware({
  target: API_TARGET,
  changeOrigin: true,
  pathRewrite: {
    '^/api': '/data', // rewrite path
  },
}));

// Proxy WebSocket requests
app.use('/ws', createProxyMiddleware({
  target: WS_TARGET,
  changeOrigin: true,
  ws: true,
  logLevel: 'debug'
}));

// Proxy Config endpoint to return env vars to client
app.get('/config', (req, res) => {
  res.json({
    // In production/docker, we might want to use the window.location.host logic 
    // or a specific env var. For now, let's assume the browser connects to the same host
    // or a specific WS URL.
    // If the node server is proxying websockets, we can point to it.
    // However, sticking to the direct connection pattern from the old app for now if possible,
    // OR we can proxy WS through this express server.
    // Let's rely on the client knowing the default or env.
    ws_url: process.env.HALA_WS_URL || 'ws://localhost:8000/ws/chat/v2'
  });
});

// Serve static files from the build directory
app.use(express.static(path.join(__dirname, 'dist')));

// Handle client-side routing, return all requests to index.html
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`UI Server running on http://localhost:${PORT}`);
});
