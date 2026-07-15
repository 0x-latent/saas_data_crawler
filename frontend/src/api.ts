import axios from 'axios';

export const api = axios.create({
  baseURL: '/api'
});

export type DataAsset = {
  id: number;
  platform: string;
  asset_type: string;
  file_name: string;
  file_path: string;
  file_size: number;
  import_status: string;
  imported_at?: string;
};

export type CrawlerTask = {
  id: number;
  platform: string;
  task_type: string;
  status: string;
  progress_current: number;
  progress_total: number;
  log_tail: string;
  error_message?: string;
  created_at: string;
};

export type Account = {
  id: number;
  platform: string;
  display_name: string;
  login_type: string;
  status: string;
  username_masked?: string;
  phone_masked?: string;
};

export type LoginSession = {
  id: number;
  account_id: number;
  platform: string;
  status: string;
  mode: string;
  prompt_message?: string;
  error_message?: string;
  expires_at?: string;
};

export type Creator = {
  id: number;
  platform: string;
  platform_creator_id: string;
  nick_name?: string;
  follower_count?: number;
  province?: string;
  city?: string;
  gender?: string;
  imported_at: string;
  source_file?: string;
  metrics_json?: Record<string, unknown>;
  attributes_json?: Record<string, unknown>;
};
