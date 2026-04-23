/** Lead data shape matching the Python Lead dataclass. */
export interface Lead {
  _index?: number;
  root_query: string;
  root_location: string;
  root_seed_name: string | null;
  root_seed_lat: number | null;
  root_seed_lng: number | null;
  spawn_depth: number;
  parent_seed_name: string | null;
  parent_seed_lat: number | null;
  parent_seed_lng: number | null;
  radius_km: number;
  name: string | null;
  rating: string | null;
  reviews: string | null;
  address: string | null;
  phone: string | null;
  website: string | null;
  email: string | null;
  plus_code: string | null;
  maps_url: string | null;
  place_lat: number | null;
  place_lng: number | null;
  distance_km_from_parent: number | null;
  scraped_at_iso: string;
}

export interface ScrapeConfig {
  query: string;
  location: string;
  limit: number;
  radius_km: number;
  max_depth: number;
  root_count: number;
  root_skip: number;
  per_seed_candidates: number;
  per_seed_keep_cap: number;
  zoom: number;
}

export type ScrapeStatus = "idle" | "running" | "complete" | "error" | "stopped";

export const DEFAULT_CONFIG: ScrapeConfig = {
  query: "car wash",
  location: "Delaware",
  limit: 50,
  radius_km: 1.0,
  max_depth: 3,
  root_count: 50,
  root_skip: 0,
  per_seed_candidates: 60,
  per_seed_keep_cap: 10,
  zoom: 15,
};
