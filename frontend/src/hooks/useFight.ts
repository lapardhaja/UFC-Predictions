import { useQuery } from "@tanstack/react-query";
import { fetchFight } from "@/api/client";

export function useFight(fightId: string | undefined) {
  return useQuery({
    queryKey: ["fight", fightId],
    queryFn: () => fetchFight(fightId!),
    enabled: Boolean(fightId),
  });
}
