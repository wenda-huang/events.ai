export type User = {
  id: number;
  email: string;
  name: string;
  phone: string | null;
  lat: number | null;
  lng: number | null;
  tags: string[];
  onboarded: boolean;
  default_radius_mi: number;
};

export type EventItem = {
  id: number;
  title: string;
  description: string;
  location: {
    lat: number;
    lng: number;
    address: string;
    city: string;
  };
  starts_at: string;
  ends_at: string;
  people_min: number;
  people_max: number;
  cost_estimate: string;
  estimated_fields: string[];
  tags: string[];
  source: "user" | "ai";
  source_url: string | null;
  created_by: number | null;
  attendee_count: number;
  invite_count: number;
  my_status: "invited" | "joined" | "declined" | null;
  distance_mi: number | null;
  tag_overlap?: number;
  relevance?: number;
  invite_reason?: string | null;
};

export type Origin = { lat: number; lng: number };
