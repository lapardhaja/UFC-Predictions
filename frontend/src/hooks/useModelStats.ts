import { useQuery } from "@tanstack/react-query";
import { fetchModelAccuracy, fetchModelFeatures } from "@/api/client";

export function useModelStats() {
  const acc = useQuery({ queryKey: ["model", "accuracy"], queryFn: fetchModelAccuracy });
  const feat = useQuery({ queryKey: ["model", "features"], queryFn: fetchModelFeatures });
  return { acc, feat };
}
