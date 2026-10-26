import type { Analysis, LoadName, Loads, NodalLoad, Vector6 } from "./types.ts";

export function combineLoadBasis(analysis: Analysis, loads: Loads): NodalLoad[] {
  const combined = new Map<number, Vector6>();
  Object.entries(loads).forEach(([name, magnitude]) => {
    (analysis.loadBasis[name as LoadName] || []).forEach(([nodeIndex, vector]) => {
      const current = combined.get(nodeIndex) || [0, 0, 0, 0, 0, 0];
      combined.set(
        nodeIndex,
        current.map((value, index) => value + magnitude * vector[index]) as Vector6,
      );
    });
  });
  return [...combined.entries()].sort((left, right) => left[0] - right[0]);
}
