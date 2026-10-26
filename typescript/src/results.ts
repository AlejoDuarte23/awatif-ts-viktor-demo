import type { Analysis, Contour, Point3, ShellResults } from "./types.ts";

function resultArray(map: Map<number, Point3> | undefined, elementIndex: number): Point3 {
  return map?.get(elementIndex) || [0, 0, 0];
}

export function vonMisesAt(sx: number, sy: number, txy: number): number {
  return Math.sqrt(Math.max(0, sx * sx - sx * sy + sy * sy + 3 * txy * txy));
}

export function calculateContour(analysis: Analysis, results: ShellResults): Contour {
  const values = analysis.elements.map((_, elementIndex) => {
    const thickness = analysis.elementThicknesses[elementIndex];
    const nxx = resultArray(results.membraneXX, elementIndex);
    const nyy = resultArray(results.membraneYY, elementIndex);
    const nxy = resultArray(results.membraneXY, elementIndex);
    const mxx = resultArray(results.bendingXX, elementIndex);
    const myy = resultArray(results.bendingYY, elementIndex);
    const mxy = resultArray(results.bendingXY, elementIndex);

    let maximum = 0;
    for (let node = 0; node < 3; node++) {
      [-1, 1].forEach((surface) => {
        const sx = nxx[node] / thickness + (surface * 6 * mxx[node]) / thickness ** 2;
        const sy = nyy[node] / thickness + (surface * 6 * myy[node]) / thickness ** 2;
        const txy = nxy[node] / thickness + (surface * 6 * mxy[node]) / thickness ** 2;
        maximum = Math.max(maximum, vonMisesAt(sx, sy, txy));
      });
    }
    return maximum;
  });

  const computedMin = Math.min(...values);
  const computedMax = Math.max(...values);
  const yieldStrength = analysis.yieldStrength;
  return {
    values,
    min: 0,
    max: yieldStrength,
    computedMin,
    computedMax,
    maximumAbsolute: Math.max(...values.map(Math.abs)),
    isYieldLimited: true,
    yieldStrength,
    title: "Von Mises stress",
    unit: "MPa",
  };
}
