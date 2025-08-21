import React from "react";
import { PrimaryButton, SecondaryButton } from "./ui/Button";

interface RequestDetails {
  timestamp: string;
  method: string;
  path: string;
  status: number;
  latency_ms: number;
  trace_id: string;
  tenant_id: string;
  client_ip: string;
  enrichment?: {
    src_ip?: string;
    dst_ip?: string;
    country?: string;
    asn?: string;
    risk?: number;
  };
}

interface Props {
  request: RequestDetails | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenInLogs: (traceId: string) => void;
}

export default function RequestDetailsSlideOver({ 
  request, 
  isOpen, 
  onClose, 
  onOpenInLogs 
}: Props) {
  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      // You could add a toast notification here
      console.log(`${label} copied to clipboard`);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const generateCurl = (req: RequestDetails) => {
    return `curl -X ${req.method} "http://localhost${req.path}" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "X-Request-ID: ${req.trace_id}" \\
  -H "Content-Type: application/json"`;
  };

  if (!request) return null;

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40"
          onClick={onClose}
        />
      )}
      
      {/* SlideOver */}
      <div className={`
        fixed inset-y-0 right-0 w-96 bg-neutral-900 border-l border-neutral-700 
        transform transition-transform duration-300 ease-in-out z-50
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
      `}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-neutral-700">
            <h2 className="text-lg font-semibold text-white">Request Details</h2>
            <button
              onClick={onClose}
              className="text-neutral-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-neutral-300 uppercase tracking-wide">
                Request Information
              </h3>
              
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-neutral-400">Method</span>
                  <span className={`text-sm font-medium px-2 py-1 rounded ${
                    request.method === 'GET' ? 'bg-blue-500/20 text-blue-300' :
                    request.method === 'POST' ? 'bg-green-500/20 text-green-300' :
                    request.method === 'PUT' ? 'bg-yellow-500/20 text-yellow-300' :
                    request.method === 'DELETE' ? 'bg-red-500/20 text-red-300' :
                    'bg-neutral-500/20 text-neutral-300'
                  }`}>
                    {request.method}
                  </span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-sm text-neutral-400">Path</span>
                  <span className="text-sm text-white font-mono">{request.path}</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-sm text-neutral-400">Status</span>
                  <span className={`text-sm font-medium px-2 py-1 rounded ${
                    request.status >= 200 && request.status < 300 ? 'bg-green-500/20 text-green-300' :
                    request.status >= 400 && request.status < 500 ? 'bg-yellow-500/20 text-yellow-300' :
                    request.status >= 500 ? 'bg-red-500/20 text-red-300' :
                    'bg-neutral-500/20 text-neutral-300'
                  }`}>
                    {request.status}
                  </span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-sm text-neutral-400">Latency</span>
                  <span className="text-sm text-white">{request.latency_ms}ms</span>
                </div>
              </div>
            </div>

            {/* Trace ID */}
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-neutral-300 uppercase tracking-wide">
                Trace Information
              </h3>
              
              <div className="space-y-3">
                <div>
                  <span className="text-sm text-neutral-400 block mb-2">Trace ID</span>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-sm bg-neutral-800 px-3 py-2 rounded border border-neutral-700 text-emerald-300 font-mono">
                      {request.trace_id}
                    </code>
                    <SecondaryButton
                      onClick={() => copyToClipboard(request.trace_id, 'Trace ID')}
                      className="px-3 py-2"
                    >
                      Copy
                    </SecondaryButton>
                  </div>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-sm text-neutral-400">Tenant ID</span>
                  <span className="text-sm text-white">{request.tenant_id}</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-sm text-neutral-400">Client IP</span>
                  <span className="text-sm text-white font-mono">{request.client_ip}</span>
                </div>
              </div>
            </div>

            {/* Enrichment Data */}
            {request.enrichment && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-neutral-300 uppercase tracking-wide">
                  Enrichment Data
                </h3>
                
                <div className="space-y-3">
                  {request.enrichment.src_ip && (
                    <div className="flex justify-between">
                      <span className="text-sm text-neutral-400">Source IP</span>
                      <span className="text-sm text-white font-mono">{request.enrichment.src_ip}</span>
                    </div>
                  )}
                  
                  {request.enrichment.dst_ip && (
                    <div className="flex justify-between">
                      <span className="text-sm text-neutral-400">Destination IP</span>
                      <span className="text-sm text-white font-mono">{request.enrichment.dst_ip}</span>
                    </div>
                  )}
                  
                  {request.enrichment.country && (
                    <div className="flex justify-between">
                      <span className="text-sm text-neutral-400">Country</span>
                      <span className="text-sm text-white">{request.enrichment.country}</span>
                    </div>
                  )}
                  
                  {request.enrichment.asn && (
                    <div className="flex justify-between">
                      <span className="text-sm text-neutral-400">ASN</span>
                      <span className="text-sm text-white">{request.enrichment.asn}</span>
                    </div>
                  )}
                  
                  {request.enrichment.risk !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-sm text-neutral-400">Risk Score</span>
                      <span className={`text-sm font-medium px-2 py-1 rounded ${
                        request.enrichment.risk < 30 ? 'bg-green-500/20 text-green-300' :
                        request.enrichment.risk < 70 ? 'bg-yellow-500/20 text-yellow-300' :
                        'bg-red-500/20 text-red-300'
                      }`}>
                        {request.enrichment.risk}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="p-6 border-t border-neutral-700 space-y-3">
            <PrimaryButton
              onClick={() => onOpenInLogs(request.trace_id)}
              className="w-full"
            >
              Open in Logs with this trace
            </PrimaryButton>
            
            <SecondaryButton
              onClick={() => copyToClipboard(generateCurl(request), 'cURL command')}
              className="w-full"
            >
              Copy cURL
            </SecondaryButton>
          </div>
        </div>
      </div>
    </>
  );
}
