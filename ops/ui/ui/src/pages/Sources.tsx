import React, { useEffect, useState } from "react";

interface Source {
  id: string;
  tenant_id: string;
  type: string;
  display_name: string;
  collector: string;
  site?: string;
  tags?: string;
  status: string;
  last_seen?: string;
  notes?: string;
}

interface SourceMetrics {
  eps_1m: number;
  records_24h: number;
  error_pct_15m: number;
  avg_risk_15m: number;
  last_seen?: string;
}

interface SourceListResponse {
  sources: Source[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface SourcesProps {
  api: {
    get: (path: string) => Promise<any>;
    post: (path: string, body: any) => Promise<any>;
  };
}

const cx = (...list: (string | boolean | undefined)[]) => list.filter(Boolean).join(" ");

const StatusBadge = ({ status }: { status: string }) => {
  const colors = {
    healthy: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40",
    degraded: "bg-yellow-500/15 text-yellow-300 ring-yellow-500/40", 
    stale: "bg-zinc-500/15 text-zinc-300 ring-zinc-500/40"
  };
  
  return (
    <span className={cx(
      "inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1",
      colors[status as keyof typeof colors] || colors.stale
    )}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

const SourceDrawer = ({ source, metrics, isOpen, onClose }: {
  source?: Source;
  metrics?: SourceMetrics;
  isOpen: boolean;
  onClose: () => void;
}) => {
  if (!source || !isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-96 bg-[#14151B] shadow-xl">
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
            <h2 className="text-lg font-semibold text-white">Source Details</h2>
            <button onClick={onClose} className="text-zinc-400 hover:text-white">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Metadata */}
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-3">Metadata</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-400">ID:</span>
                  <span className="text-white font-mono">{source.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Type:</span>
                  <span className="text-white">{source.type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Tenant:</span>
                  <span className="text-white">{source.tenant_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Site:</span>
                  <span className="text-white">{source.site || "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Collector:</span>
                  <span className="text-white">{source.collector}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Tags:</span>
                  <span className="text-white">{source.tags || "—"}</span>
                </div>
              </div>
            </div>

            {/* Metrics */}
            {metrics && (
              <div>
                <h3 className="text-sm font-medium text-zinc-400 mb-3">Current Metrics</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-zinc-400">EPS (1m):</span>
                    <span className="text-white">{metrics.eps_1m.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Records (24h):</span>
                    <span className="text-white">{metrics.records_24h}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Error % (15m):</span>
                    <span className="text-white">{metrics.error_pct_15m.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Avg Risk (15m):</span>
                    <span className="text-white">{metrics.avg_risk_15m.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400">Last Seen:</span>
                    <span className="text-white">
                      {metrics.last_seen ? new Date(metrics.last_seen).toLocaleString() : "—"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Sparklines placeholder */}
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-3">Trends (15m)</h3>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs text-zinc-400 mb-1">
                    <span>EPS</span>
                    <span>{metrics?.eps_1m.toFixed(2) || "0.00"}</span>
                  </div>
                  <div className="h-8 bg-zinc-800/50 rounded flex items-center justify-center text-xs text-zinc-500">
                    Sparkline placeholder
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-zinc-400 mb-1">
                    <span>Error %</span>
                    <span>{metrics?.error_pct_15m.toFixed(1) || "0.0"}%</span>
                  </div>
                  <div className="h-8 bg-zinc-800/50 rounded flex items-center justify-center text-xs text-zinc-500">
                    Sparkline placeholder
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-zinc-400 mb-1">
                    <span>Avg Risk</span>
                    <span>{metrics?.avg_risk_15m.toFixed(2) || "0.00"}</span>
                  </div>
                  <div className="h-8 bg-zinc-800/50 rounded flex items-center justify-center text-xs text-zinc-500">
                    Sparkline placeholder
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function Sources({ api }: SourcesProps) {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [selectedMetrics, setSelectedMetrics] = useState<SourceMetrics | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  
  // Filters
  const [filters, setFilters] = useState({
    tenant: "",
    type: "",
    status: "",
    page: 1,
    size: 50
  });

  // Polling state
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  const loadSources = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (filters.tenant) params.append("tenant", filters.tenant);
      if (filters.type) params.append("type", filters.type);
      if (filters.status) params.append("status", filters.status);
      params.append("page", filters.page.toString());
      params.append("size", filters.size.toString());
      
      const response: SourceListResponse = await api.get(`/v1/sources?${params}`);
      setSources(response.sources);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sources");
    } finally {
      setLoading(false);
    }
  };

  const loadSourceMetrics = async (sourceId: string) => {
    try {
      const metrics: SourceMetrics = await api.get(`/v1/sources/${sourceId}/metrics?window=900`);
      return metrics;
    } catch (err) {
      console.error("Failed to load metrics for", sourceId, err);
      return null;
    }
  };

  const openSourceDrawer = async (source: Source) => {
    setSelectedSource(source);
    setDrawerOpen(true);
    
    // Load metrics for the selected source
    const metrics = await loadSourceMetrics(source.id);
    setSelectedMetrics(metrics);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setSelectedSource(null);
    setSelectedMetrics(null);
  };

  // Initial load
  useEffect(() => {
    loadSources();
  }, [filters]);

  // Set up polling for live updates
  useEffect(() => {
    const interval = setInterval(async () => {
      // Only update metrics for visible sources, not full table reload
      if (sources.length > 0) {
        const updatedSources = await Promise.all(
          sources.map(async (source) => {
            const metrics = await loadSourceMetrics(source.id);
            if (metrics) {
              // Update status based on metrics
              let newStatus = "stale";
              const now = new Date();
              const lastSeen = metrics.last_seen ? new Date(metrics.last_seen) : null;
              
              if (lastSeen) {
                const secondsSinceLastSeen = (now.getTime() - lastSeen.getTime()) / 1000;
                if (secondsSinceLastSeen < 120 && metrics.error_pct_15m < 5) {
                  newStatus = "healthy";
                } else if (secondsSinceLastSeen < 300 || metrics.error_pct_15m >= 5) {
                  newStatus = "degraded";
                }
              }
              
              return { ...source, status: newStatus };
            }
            return source;
          })
        );
        setSources(updatedSources);
      }
    }, 10000); // 10 seconds

    setPollingInterval(interval);
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [sources.length]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Sources</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={loadSources}
            className="rounded-xl bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 px-4 py-2 border border-emerald-400/20"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-zinc-400 mb-1">Tenant</label>
          <select
            value={filters.tenant}
            onChange={(e) => setFilters(prev => ({ ...prev, tenant: e.target.value, page: 1 }))}
            className="w-full rounded-xl bg-[#14151B] px-3 py-2 text-sm text-zinc-200 outline-none ring-1 ring-white/5 focus:ring-indigo-400/40"
          >
            <option value="">All Tenants</option>
            <option value="default">default</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-zinc-400 mb-1">Type</label>
          <select
            value={filters.type}
            onChange={(e) => setFilters(prev => ({ ...prev, type: e.target.value, page: 1 }))}
            className="w-full rounded-xl bg-[#14151B] px-3 py-2 text-sm text-zinc-200 outline-none ring-1 ring-white/5 focus:ring-indigo-400/40"
          >
            <option value="">All Types</option>
            <option value="cisco_asa">Cisco ASA</option>
            <option value="cisco_ftd">Cisco FTD</option>
            <option value="palo_alto">Palo Alto</option>
            <option value="aws_vpc">AWS VPC</option>
            <option value="test_device">Test Device</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-zinc-400 mb-1">Status</label>
          <select
            value={filters.status}
            onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value, page: 1 }))}
            className="w-full rounded-xl bg-[#14151B] px-3 py-2 text-sm text-zinc-200 outline-none ring-1 ring-white/5 focus:ring-indigo-400/40"
          >
            <option value="">All Status</option>
            <option value="healthy">Healthy</option>
            <option value="degraded">Degraded</option>
            <option value="stale">Stale</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-zinc-400 mb-1">Page Size</label>
          <select
            value={filters.size}
            onChange={(e) => setFilters(prev => ({ ...prev, size: Number(e.target.value), page: 1 }))}
            className="w-full rounded-xl bg-[#14151B] px-3 py-2 text-sm text-zinc-200 outline-none ring-1 ring-white/5 focus:ring-indigo-400/40"
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl bg-red-500/15 text-red-300 px-4 py-3 border border-red-400/20">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-[#14151B] rounded-xl border border-white/5 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#0F1116] border-b border-white/5">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Source</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Tenant</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Collector</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">EPS (1m)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Records (24h)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Last Seen</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Error %</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">Avg Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={10} className="px-6 py-4 text-center text-zinc-400">
                    Loading sources...
                  </td>
                </tr>
              ) : sources.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-6 py-8 text-center text-zinc-400">
                    No sources found
                  </td>
                </tr>
              ) : (
                sources.map((source) => (
                  <tr
                    key={source.id}
                    onClick={() => openSourceDrawer(source)}
                    className="hover:bg-white/5 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={source.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white font-medium">
                      {source.display_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                      {source.type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                      {source.tenant_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                      {source.collector}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                      {/* This will be updated by polling */}
                      —
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                      {/* This will be updated by polling */}
                      —
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                      {source.last_seen ? new Date(source.last_seen).toLocaleString() : "—"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                      {/* This will be updated by polling */}
                      —
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-300">
                      {/* This will be updated by polling */}
                      —
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {sources.length > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-zinc-400">
            Showing {sources.length} sources
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilters(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
              disabled={filters.page <= 1}
              className="px-3 py-1 rounded text-sm bg-[#14151B] text-zinc-300 hover:bg-[#0F1116] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-zinc-400">Page {filters.page}</span>
            <button
              onClick={() => setFilters(prev => ({ ...prev, page: prev.page + 1 }))}
              disabled={sources.length < filters.size}
              className="px-3 py-1 rounded text-sm bg-[#14151B] text-zinc-300 hover:bg-[#0F1116] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Source Details Drawer */}
      <SourceDrawer
        source={selectedSource}
        metrics={selectedMetrics}
        isOpen={drawerOpen}
        onClose={closeDrawer}
      />
    </div>
  );
}
