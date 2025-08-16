// scripts/ui_smoke.js — UI smoke test using the same API client
// Usage: node scripts/ui_smoke.js

// Mock the browser environment for the API client
global.window = {
  location: { hostname: 'localhost' }
};

global.fetch = require('node-fetch');

// Import the API client (same one UI uses)
const fs = require('fs');
const path = require('path');

// Read and execute the API client code
const apiClientPath = path.join(__dirname, '../ops/stage4/ui/api-client.js');
const apiClientCode = fs.readFileSync(apiClientPath, 'utf8');

// Mock the config
global.window.__CFG__ = {
  API_BASE_URL: 'http://localhost:8080',
  API_PREFIX: '/v1',
  API_KEY: 'TEST_KEY'
};

// Execute the API client code
eval(apiClientCode);

async function smokeTest() {
  console.log('🧪 UI Smoke Test - Using same API client as UI');
  console.log('API Config:', {
    API_BASE_URL: window.apiConfig.API_BASE_URL,
    API_PREFIX: window.apiConfig.API_PREFIX,
    API_KEY: '***' + window.apiConfig.API_KEY.substring(window.apiConfig.API_KEY.length - 4)
  });

  try {
    // Test the three endpoints the UI uses
    console.log('\n==> Testing /api/requests (15m)');
    const req15m = await window.api('/api/requests', { limit: 50, window: '15m' });
    console.log(`✓ requests(15m) count: ${req15m.items ? req15m.items.length : 0}`);
    console.log(`  keys: ${Object.keys(req15m).join(', ')}`);

    console.log('\n==> Testing /api/requests (24h)');
    const req24h = await window.api('/api/requests', { limit: 500, window: '24h' });
    console.log(`✓ requests(24h) count: ${req24h.items ? req24h.items.length : 0}`);
    console.log(`  keys: ${Object.keys(req24h).join(', ')}`);

    console.log('\n==> Testing /metrics');
    const metrics = await window.api('/metrics', { window: '15m' });
    console.log(`✓ metrics keys: ${Object.keys(metrics).join(', ')}`);
    console.log(`  eps: ${metrics.eps || 0}`);
    console.log(`  queue_depth: ${metrics.queue_depth || 0}`);

    console.log('\n✅ ALL TESTS PASSED');
    return true;
  } catch (error) {
    console.error('\n❌ TEST FAILED:', error.message);
    return false;
  }
}

// Run the test
smokeTest().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('Unexpected error:', error);
  process.exit(1);
});
