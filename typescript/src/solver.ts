import { analyze, deform } from "awatif-fem";
import type { ElementInputs } from "awatif-fem";
import type { Analysis, Solution } from "./types.ts";

export function solveAnalysis(analysis: Analysis): Solution {
  const elementInputs: ElementInputs = {
    elasticities: new Map(analysis.elements.map((_, index) => [index, analysis.elasticity])),
    poissonsRatios: new Map(analysis.elements.map((_, index) => [index, analysis.poissonRatio])),
    thicknesses: new Map(analysis.elementThicknesses.map((thickness, index) => [index, thickness])),
  };
  const deformation = deform(
    analysis.nodes,
    analysis.elements,
    {
      supports: new Map(analysis.supports),
      loads: new Map(analysis.loads),
    },
    elementInputs,
  );
  if (!deformation?.deformations || !deformation.reactions) {
    throw new Error("Awatif returned no deformation result.");
  }
  const results = analyze(analysis.nodes, analysis.elements, elementInputs, deformation);
  return {
    deformation: { deformations: deformation.deformations, reactions: deformation.reactions },
    results,
  };
}
