export interface Project {
  id: string;
  name: string;
  base_url: string;
  login_url: string | null;
  allowed_domains: string[];
  seed_urls: string[];
  crawl_status: string;
  crawl_pages_count: number;
  crawl_elements_count: number;
  has_credentials: boolean;
  created_at: string;
  updated_at: string;
}

export interface CrawlStatus {
  status: string;
  job_id: string | null;
  pages_count: number;
  elements_count: number;
  message?: string;
}

export interface Page {
  id: string;
  project_id: string;
  url: string;
  title: string | null;
  screenshot_path: string | null;
  discovered_at: string;
  elements: Element[];
}

export interface Element {
  id: string;
  page_id: string;
  element_type: string;
  text_content: string | null;
  aria_label: string | null;
  selector_primary: string;
  selector_fallbacks: string[];
}

export interface Flow {
  id: string;
  project_id: string;
  name: string;
  risk_level: string;
  confidence_score: number;
  requires_auth: boolean;
  destructive: boolean;
  steps: FlowStep[];
  created_at: string;
}

export interface FlowStep {
  id: string;
  step_order: number;
  action_type: string;
  target_element_id: string | null;
  expected_result: Record<string, unknown>;
}

export interface FlowGraph {
  nodes: { id: string; label: string; url: string }[];
  edges: { id: string; source: string; target: string; label?: string }[];
  flows: Flow[];
}

export interface GeneratedTest {
  id: string;
  project_id: string;
  flow_id: string | null;
  name: string;
  file_path: string;
  version: number;
  status: string;
  created_at: string;
  flow_name: string | null;
}

export interface TestRun {
  id: string;
  project_id: string;
  run_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  triggered_by: string;
  pass_count: number;
  fail_count: number;
  total_count: number;
}

export interface TestRunResult {
  id: string;
  test_run_id: string;
  generated_test_id: string;
  test_name: string | null;
  status: string;
  duration_ms: number | null;
  failure_category: string | null;
  error_message: string | null;
  screenshot_path: string | null;
  trace_path: string | null;
  video_path: string | null;
  ai_summary: string | null;
}

export interface HealingSuggestion {
  id: string;
  generated_test_id: string;
  failed_selector: string;
  suggested_selector: string;
  confidence_score: number;
  rationale: string | null;
  approved: boolean | null;
  created_at: string;
}
