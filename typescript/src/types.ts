import type { AnalyzeOutputs, Node, Support6, Vector6 } from "awatif-fem";

export type Point3 = Node;
export type { Vector6 };
export type LoadName =
  "axial_compression" | "shear_x" | "shear_y" | "moment_x" | "moment_y" | "torsion_z";
export type Loads = Record<LoadName, number>;
export type NodalLoad = [number, Vector6];
export type ComponentName = "plate" | "tube" | "stiffeners";

export interface ShellComponent {
  nodes: Point3[];
  elements: number[][];
  nodeIndices: number[];
  elementIndices: number[];
}

export interface Analysis {
  nodes: Point3[];
  elements: number[][];
  supports: [number, Support6][];
  loads: NodalLoad[];
  loadBasis: Record<LoadName, NodalLoad[]>;
  elasticity: number;
  poissonRatio: number;
  yieldStrength: number;
  elementThicknesses: number[];
}

export interface GeometryInputs {
  tube_radius: number;
  tube_height: number;
  tube_thickness: number;
  plate_radius: number;
  plate_thickness: number;
  bolt_nominal_diameter: number;
  bolt_center_edge_distance: number;
}

export interface Payload {
  mode: "model" | "results";
  input: {
    geometry: GeometryInputs;
    loads: Loads;
    view: { show_mesh: boolean; deformation_scale: number; result_component: string };
  };
  geometry: Record<ComponentName, ShellComponent> & {
    nodes: Point3[];
    boltCenters: Point3[];
    foundation: { width: number; depth: number; height: number };
  };
  analysis: Analysis;
  metadata: { meshDensity: string; shellElements: number; assumption: string };
}

export interface Deformation {
  deformations: Map<number, Vector6>;
  reactions: Map<number, Vector6>;
}
export type ShellResults = AnalyzeOutputs;
export interface Solution {
  deformation: Deformation;
  results: ShellResults;
}
export interface Contour {
  values: number[];
  min: number;
  max: number;
  computedMin: number;
  computedMax: number;
  maximumAbsolute: number;
  isYieldLimited: boolean;
  yieldStrength: number;
  title: string;
  unit: string;
}

declare global {
  interface Window {
    __BASE_PLATE_PAYLOAD__?: Payload;
  }
  var BasePlateSolver: { solveAnalysis(analysis: Analysis): Solution } | undefined;
}
