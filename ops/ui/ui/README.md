# Telemetry API Dashboard - React Version

This is a modern, professional React-based dashboard for the Telemetry API.

## Features

- **Professional Design**: Dark, glossy theme with smooth animations
- **Success Rate Ring**: Beautiful circular progress indicator showing success percentage
- **Slide-Over Details**: Right-side drawer for request details with summary chips
- **Live Logs**: Real-time log streaming with download capability
- **API Playground**: Interactive testing of system endpoints
- **Responsive**: Works on desktop and mobile devices

## Quick Start

### Development Mode

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

3. Open http://localhost

### Production Build

1. Build the application:
```bash
npm run build
```

2. The built files will be in the `dist/` directory

## Key Improvements

### Success Rate Visualization
- **Circular Progress Ring**: Shows success percentage with beautiful gradient
- **Dynamic Colors**: Green for high success, orange for medium, red for low
- **Clean Typography**: Large percentage number with external label

### Request Details
- **Slide-Over Drawer**: Right-side panel instead of modal
- **Summary Chips**: Quick overview of key metrics (Status, Method, Latency, etc.)
- **Country Flags**: Visual indicators for geographic data
- **Copy Button**: Easy JSON copying functionality

### Professional Styling
- **Dark Theme**: Consistent with modern dashboard aesthetics
- **Smooth Animations**: 0.8s cubic-bezier transitions
- **Proper Spacing**: Generous padding and margins
- **Typography**: Inter font with proper font smoothing

## API Integration

The dashboard connects to the Telemetry API endpoints:

- `GET /v1/metrics` - System metrics
- `GET /v1/requests?limit=50` - Recent requests
- `GET /v1/system` - System information
- `GET /v1/logs/stream` - Live log streaming
- `POST /v1/ingest` - Data ingestion
- `POST /v1/lookup` - Threat intelligence lookup

## Configuration

Set the API base URL and key in the top bar:
- **API Base**: Defaults to `http://localhost`
- **API Key**: Defaults to `TEST_KEY`

## Browser Support

- Modern browsers with ES2020 support
- Chrome 88+, Firefox 85+, Safari 14+, Edge 88+
