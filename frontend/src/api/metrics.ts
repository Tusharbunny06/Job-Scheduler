import { apiClient } from './client';

export interface DashboardMetrics {
  active_workers: number;
  jobs_queued: number;
  jobs_running: number;
  completed_last_hour: number;
  failure_rate: string;
  failure_rate_value: number;
  avg_execution_seconds: number;
  dlq_count: number;
  total_executions: number;
}

export interface WorkerInfo {
  id: string;
  hostname: string;
  status: string;
  concurrency_limit: number;
  registered_at: string;
  last_heartbeat: string | null;
  is_stale: boolean;
}

export interface ThroughputBucket {
  hour: string;
  completed: number;
}

export const getDashboardMetrics = async (): Promise<DashboardMetrics> => {
  const response = await apiClient.get<DashboardMetrics>('/metrics/dashboard');
  return response.data;
};

export const getWorkers = async (): Promise<WorkerInfo[]> => {
  const response = await apiClient.get<WorkerInfo[]>('/metrics/workers');
  return response.data;
};

export const getThroughput = async (): Promise<ThroughputBucket[]> => {
  const response = await apiClient.get<ThroughputBucket[]>('/metrics/throughput');
  return response.data;
};
