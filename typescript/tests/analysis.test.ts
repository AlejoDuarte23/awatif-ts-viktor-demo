import assert from "node:assert/strict";
import { test } from "node:test";
import { combineLoadBasis } from "../src/loads.ts";
import { calculateContour, vonMisesAt } from "../src/results.ts";
import { solveAnalysis } from "../src/solver.ts";
import type { Analysis, Loads, Point3, Vector6 } from "../src/types.ts";

const zeroLoads: Loads = {
  axial_compression: 0,
  shear_x: 0,
  shear_y: 0,
  moment_x: 0,
  moment_y: 0,
  torsion_z: 0,
};

function shell(): Analysis {
  return {
    nodes: [
      [0, 0, 0],
      [100, 0, 0],
      [0, 100, 0],
    ],
    elements: [[0, 1, 2]],
    supports: [
      [0, [true, true, true, true, true, true]],
      [1, [true, true, true, true, true, true]],
    ],
    loads: [[2, [0, -1000, -1000, 0, 0, 0]]],
    loadBasis: {
      axial_compression: [],
      shear_x: [],
      shear_y: [],
      moment_x: [],
      moment_y: [],
      torsion_z: [],
    },
    elasticity: 200_000,
    poissonRatio: 0.3,
    yieldStrength: 280,
    elementThicknesses: [10],
  };
}

test("the TypeScript solver gives finite results for a vertical shell", () => {
  const horizontal = shell();
  const rotate = ([x, y, z]: number[]): Point3 => [x, -z, y];
  const vertical: Analysis = {
    ...horizontal,
    nodes: horizontal.nodes.map(rotate),
    loads: horizontal.loads.map(([node, values]) => [
      node,
      [...rotate(values), ...rotate(values.slice(3))] as Vector6,
    ]),
  };
  const flat = solveAnalysis(horizontal);
  const upright = solveAnalysis(vertical);
  const reference = rotate(flat.deformation.deformations.get(2)!);
  const actual = upright.deformation.deformations.get(2)!;
  reference.forEach((value, index) => {
    assert.ok(Number.isFinite(actual[index]));
    assert.ok(Math.abs(value - actual[index]) < 1e-8);
  });
  const contour = calculateContour(vertical, upright.results);
  assert.ok(Number.isFinite(contour.maximumAbsolute));
  assert.ok(contour.maximumAbsolute > 0);
  const reaction = [...upright.deformation.reactions.values()].reduce(
    (sum, value) => sum + value[2],
    0,
  );
  assert.ok(Math.abs(reaction - 1000) < 1e-6);
});

test("the six load bases add nodal forces and moments", () => {
  const analysis = shell();
  analysis.loadBasis.shear_x = [[2, [1, 0, 0, 0, 0, 0]]];
  analysis.loadBasis.moment_y = [
    [2, [0, 0, 2, 0, 3, 0]],
    [0, [0, 0, -2, 0, 0, 0]],
  ];
  assert.deepEqual(combineLoadBasis(analysis, { ...zeroLoads, shear_x: 4, moment_y: -2 }), [
    [0, [0, 0, 4, 0, 0, 0]],
    [2, [4, 0, -4, 0, -6, 0]],
  ]);
});

test("the stress contour includes membrane and both bending surfaces", () => {
  const analysis = shell();
  const contour = calculateContour(analysis, {
    membraneXX: new Map([[0, [1000, 1000, 1000]]]),
    bendingXX: new Map([[0, [1000, 1000, 1000]]]),
  });
  assert.equal(contour.maximumAbsolute, 160);
  assert.equal(contour.max, 280);
  assert.equal(vonMisesAt(0, 0, 10), Math.sqrt(300));
});
