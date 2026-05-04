import axios from "axios";
import type { EventDetail, EventSummary, FighterDetail, ModelAccuracy, ModelFeatures } from "@/types";

const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const api = axios.create({ baseURL: base });

export async function fetchUpcomingEvents(): Promise<EventSummary[]> {
  const { data } = await api.get<EventSummary[]>("/events/upcoming");
  return data;
}

export async function fetchEvent(eventId: string): Promise<EventDetail> {
  const { data } = await api.get<EventDetail>(`/events/${eventId}`);
  return data;
}

export async function fetchFight(fightId: string) {
  const { data } = await api.get(`/fights/${fightId}`);
  return data as { fight: Record<string, unknown>; prediction: Record<string, unknown> };
}

export async function fetchFighter(fighterId: string): Promise<FighterDetail> {
  const { data } = await api.get<FighterDetail>(`/fighters/${fighterId}`);
  return data;
}

export async function fetchModelAccuracy(): Promise<ModelAccuracy> {
  const { data } = await api.get<ModelAccuracy>("/model/accuracy");
  return data;
}

export async function fetchModelFeatures(): Promise<ModelFeatures> {
  const { data } = await api.get<ModelFeatures>("/model/features");
  return data;
}
