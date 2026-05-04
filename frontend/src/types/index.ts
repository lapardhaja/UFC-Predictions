export interface FighterBrief {
  fighter_id: string;
  name: string;
}

export interface EventSummary {
  event_id: string;
  event_name: string;
  date: string | null;
  location: string | null;
  is_upcoming: boolean;
  fight_count: number;
}

export interface FightSummary {
  fight_id: string;
  fighter_a: FighterBrief;
  fighter_b: FighterBrief;
  weight_class: string | null;
  is_title_fight: boolean;
}

export interface EventDetail extends EventSummary {
  fights: FightSummary[];
}

export interface FighterDetail {
  fighter_id: string;
  name: string;
  height_cm: number | null;
  reach_cm: number | null;
  weight_lbs: number | null;
  stance: string | null;
  dob: string | null;
  wins: number;
  losses: number;
  draws: number;
  nc: number;
}

export interface ModelAccuracy {
  overall_accuracy: number | null;
  roc_auc: number | null;
  brier_score: number | null;
  history: { period: string; accuracy: number; sample_size: number }[];
}

export interface ModelFeatures {
  items: { feature: string; importance: number }[];
}
