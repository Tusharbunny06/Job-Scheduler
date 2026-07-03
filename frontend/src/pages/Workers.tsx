import { useQuery } from '@tanstack/react-query';
import { getWorkers } from '../api/metrics';
import { Server, Wifi, WifiOff, RefreshCw, Loader2, ServerCrash } from 'lucide-react';

function formatHeartbeat(ts: string | null): string {
  if (!ts) return 'Never';
  const d = new Date(ts);
  const diffMs = Date.now() - d.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  if (diffSecs < 60) return `${diffSecs}s ago`;
  const diffMins = Math.floor(diffSecs / 60);
  if (diffMins < 60) return `${diffMins}m ago`;
  return `${Math.floor(diffMins / 60)}h ago`;
}

export default function Workers() {
  const { data: workers, isLoading, isError, refetch } = useQuery({
    queryKey: ['workers'],
    queryFn: getWorkers,
    refetchInterval: 10_000, // Live poll every 10 seconds
  });

  const activeCount = workers?.filter(w => !w.is_stale && w.status === 'active').length ?? 0;
  const staleCount = workers?.filter(w => w.is_stale).length ?? 0;
  const offlineCount = workers?.filter(w => w.status === 'offline').length ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-slate-800">Workers</h2>
          <p className="text-sm text-slate-500 mt-1">
            Real-time view of registered worker nodes. Polls every 10 seconds.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg shadow-sm hover:bg-slate-50 transition text-sm"
        >
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {/* Summary Cards */}
      {!isLoading && !isError && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 flex items-center gap-3 shadow-sm">
            <div className="p-2 bg-emerald-100 rounded-lg"><Wifi className="text-emerald-600" size={20} /></div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{activeCount}</p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Active</p>
            </div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 flex items-center gap-3 shadow-sm">
            <div className="p-2 bg-amber-100 rounded-lg"><Wifi className="text-amber-500" size={20} /></div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{staleCount}</p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Stale (&gt;2 min)</p>
            </div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 flex items-center gap-3 shadow-sm">
            <div className="p-2 bg-slate-100 rounded-lg"><WifiOff className="text-slate-400" size={20} /></div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{offlineCount}</p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Offline</p>
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-16 flex flex-col items-center justify-center gap-4">
          <Loader2 className="animate-spin text-blue-500" size={36} />
          <p className="text-slate-500 text-sm font-medium">Loading workers…</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="bg-white rounded-xl shadow-sm border border-red-100 p-16 flex flex-col items-center justify-center gap-4">
          <ServerCrash className="text-red-400" size={40} />
          <p className="text-slate-700 font-medium">Failed to load workers</p>
          <button onClick={() => refetch()} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">
            Try Again
          </button>
        </div>
      )}

      {/* Workers Table */}
      {!isLoading && !isError && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Worker ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Hostname</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Last Heartbeat</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Health</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {workers && workers.length > 0 ? (
                workers.map(worker => (
                  <tr key={worker.id} className="hover:bg-slate-50 transition">
                    <td className="px-6 py-4 text-sm font-mono text-slate-400">{worker.id.substring(0, 12)}…</td>
                    <td className="px-6 py-4 text-sm font-medium text-slate-800 flex items-center gap-2">
                      <Server size={15} className="text-slate-400" />
                      {worker.hostname}
                    </td>
                    <td className="px-6 py-4">
                      {worker.status === 'active' ? (
                        <span className="px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full bg-emerald-100 text-emerald-800">Active</span>
                      ) : worker.status === 'offline' ? (
                        <span className="px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full bg-slate-100 text-slate-600">Offline</span>
                      ) : (
                        <span className="px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full bg-amber-100 text-amber-700">{worker.status}</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-500">{formatHeartbeat(worker.last_heartbeat)}</td>
                    <td className="px-6 py-4">
                      {worker.is_stale ? (
                        <div className="flex items-center gap-1.5 text-amber-600 text-xs font-medium">
                          <div className="w-2 h-2 rounded-full bg-amber-400" />
                          Stale
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-emerald-600 text-xs font-medium">
                          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                          Healthy
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center gap-3 text-slate-400">
                      <Server size={36} className="text-slate-300" />
                      <p className="font-medium text-slate-500">No workers registered</p>
                      <p className="text-sm">Start a worker process to see it here.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
