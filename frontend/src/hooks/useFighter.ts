import { useQuery } from "@tanstack/react-query";
import { fetchFighter } from "@/api/client";

export function useFighter(fighterId: string | undefined) {
  return useQuery({
    queryKey: ["fighter", fighterId],
    queryFn: () => fetchFighter(fighterId!),
    enabled: Boolean(fighterId),
  });
}
