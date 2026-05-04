import { useQuery } from "@tanstack/react-query";
import { fetchEvent, fetchUpcomingEvents } from "@/api/client";

export function useEvents() {
  return useQuery({ queryKey: ["events", "upcoming"], queryFn: fetchUpcomingEvents });
}

export function useEvent(eventId: string | undefined) {
  return useQuery({
    queryKey: ["event", eventId],
    queryFn: () => fetchEvent(eventId!),
    enabled: Boolean(eventId),
  });
}
