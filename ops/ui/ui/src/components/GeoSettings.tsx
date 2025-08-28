import React, { useState, useEffect } from "react";

interface GeoStatus {
  geoip: {
    status: "loaded" | "missing";
    last_refresh?: number;
  };
  asn: {
    status: "loaded" | "missing";
    last_refresh?: number;
  };
  threatintel: {
    status: "loaded" | "missing";
    sources: string[];
  };
}

interface GeoSettingsProps {
  api: {
    get: (path: string) => Promise<any>;
  };
}

const cx = (...list: (string | boolean | undefined)[]) => list.filter(Boolean).join(" ");

const GeoSettings: React.FC<GeoSettingsProps> = ({ api }) => {
  const [geoStatus, setGeoStatus] = useState<GeoStatus | null>(null);
  const [infoPanelOpen, setInfoPanelOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadGeoStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const systemInfo = await api.get("/v1/system");
      setGeoStatus({
        geoip: systemInfo.geoip,
        asn: systemInfo.asn,
        threatintel: systemInfo.threatintel
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Geo status");
    } finally {
      setLoading(false);
    }
  };

  const refreshGeoData = async () => {
    try {
      setLoading(true);
      setError(null);
      // This would call a refresh endpoint in the future
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate refresh
      await loadGeoStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh Geo data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGeoStatus();
  }, []);

  const formatTimestamp = (timestamp?: number) => {
    if (!timestamp) return "Never";
    return new Date(timestamp * 1000).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    return status === "loaded" 
      ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40"
      : "bg-red-500/15 text-red-300 ring-red-500/40";
  };

  if (!geoStatus) {
    return (
      <div className="rounded-xl bg-zinc-900/50 border border-white/10 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Geo Settings</h3>
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-emerald-500"></div>
        </div>
        <p className="text-zinc-400">Loading Geo settings...</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-zinc-900/50 border border-white/10 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Geo Settings</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setInfoPanelOpen(true)}
            className="p-2 text-zinc-400 hover:text-white rounded-lg hover:bg-white/5"
            title="Geo Settings Info"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
          <button
            onClick={refreshGeoData}
            disabled={loading}
            className="rounded-lg bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 px-3 py-2 border border-emerald-400/20 disabled:opacity-50"
          >
            {loading ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-emerald-500"></div>
            ) : (
              "Refresh"
            )}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/15 border border-red-500/30 rounded-lg">
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      {/* GeoIP Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 bg-zinc-800/50 rounded-lg border border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            <div>
              <h4 className="text-white font-medium">GeoIP Database</h4>
              <p className="text-zinc-400 text-sm">
                Last refresh: {formatTimestamp(geoStatus.geoip.last_refresh)}
              </p>
            </div>
          </div>
          <span className={cx(
            "inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1",
            getStatusColor(geoStatus.geoip.status)
          )}>
            {geoStatus.geoip.status}
          </span>
        </div>

        {/* ASN Section */}
        <div className="flex items-center justify-between p-4 bg-zinc-800/50 rounded-lg border border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-blue-500"></div>
            <div>
              <h4 className="text-white font-medium">ASN Database</h4>
              <p className="text-zinc-400 text-sm">
                Last refresh: {formatTimestamp(geoStatus.asn.last_refresh)}
              </p>
            </div>
          </div>
          <span className={cx(
            "inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1",
            getStatusColor(geoStatus.asn.status)
          )}>
            {geoStatus.asn.status}
          </span>
        </div>

        {/* Threat Intelligence Section */}
        <div className="flex items-center justify-between p-4 bg-zinc-800/50 rounded-lg border border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-red-500"></div>
            <div>
              <h4 className="text-white font-medium">Threat Intelligence</h4>
              <p className="text-zinc-400 text-sm">
                {geoStatus.threatintel.sources.length} sources loaded
              </p>
            </div>
          </div>
          <span className={cx(
            "inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1",
            getStatusColor(geoStatus.threatintel.status)
          )}>
            {geoStatus.threatintel.status}
          </span>
        </div>
      </div>

      {/* Download Link */}
      <div className="mt-6 p-4 bg-zinc-800/30 rounded-lg border border-white/5">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-white font-medium">Download GeoLite2 Database</h4>
            <p className="text-zinc-400 text-sm">
              Get the latest GeoIP database from MaxMind
            </p>
          </div>
          <a
            href="https://dev.maxmind.com/geoip/geoip2/geolite2/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-500/15 text-blue-300 hover:bg-blue-500/25 px-4 py-2 border border-blue-400/20"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Download
          </a>
        </div>
      </div>

      {/* Info Panel */}
      {infoPanelOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setInfoPanelOpen(false)} />
          <div className="absolute right-0 top-0 h-full w-96 bg-zinc-900 shadow-xl">
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
                <h2 className="text-lg font-semibold text-white">Geo Settings Info</h2>
                <button 
                  onClick={() => setInfoPanelOpen(false)} 
                  className="text-zinc-400 hover:text-white"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <div>
                  <h3 className="text-sm font-medium text-zinc-400 mb-3">Database Paths</h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-zinc-400">GeoIP:</span>
                      <span className="text-white font-mono ml-2">/app/data/GeoLite2-City.mmdb</span>
                    </div>
                    <div>
                      <span className="text-zinc-400">ASN:</span>
                      <span className="text-white font-mono ml-2">/app/data/asn.csv</span>
                    </div>
                    <div>
                      <span className="text-zinc-400">Threat Intel:</span>
                      <span className="text-white font-mono ml-2">/app/data/ti/</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-medium text-zinc-400 mb-3">Loaded Sources</h3>
                  <div className="space-y-1">
                    {geoStatus.threatintel.sources.length > 0 ? (
                      geoStatus.threatintel.sources.map((source, index) => (
                        <div key={index} className="text-sm text-white font-mono bg-zinc-800/50 p-2 rounded">
                          {source}
                        </div>
                      ))
                    ) : (
                      <p className="text-zinc-400 text-sm">No threat intelligence sources loaded</p>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-medium text-zinc-400 mb-3">Actions</h3>
                  <div className="space-y-2">
                    <button
                      onClick={refreshGeoData}
                      disabled={loading}
                      className="w-full rounded-lg bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 px-4 py-2 border border-emerald-400/20 disabled:opacity-50"
                    >
                      {loading ? "Refreshing..." : "Refresh All Data"}
                    </button>
                    <button
                      onClick={() => setInfoPanelOpen(false)}
                      className="w-full rounded-lg bg-zinc-500/15 text-zinc-300 hover:bg-zinc-500/25 px-4 py-2 border border-zinc-400/20"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GeoSettings;
