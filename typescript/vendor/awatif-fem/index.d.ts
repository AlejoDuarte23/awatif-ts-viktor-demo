export type Node = [number, number, number];
export type Vector6 = [number, number, number, number, number, number];
export type Support6 = [boolean, boolean, boolean, boolean, boolean, boolean];
export interface NodeInputs {
  supports?: Map<number, Support6>;
  loads?: Map<number, Vector6>;
}
export interface ElementInputs {
  elasticities?: Map<number, number>;
  elasticitiesOrthogonal?: Map<number, number>;
  shearModuli?: Map<number, number>;
  areas?: Map<number, number>;
  momentsOfInertiaZ?: Map<number, number>;
  momentsOfInertiaY?: Map<number, number>;
  torsionalConstants?: Map<number, number>;
  thicknesses?: Map<number, number>;
  poissonsRatios?: Map<number, number>;
}
export interface DeformOutputs {
  deformations?: Map<number, Vector6>;
  reactions?: Map<number, Vector6>;
}
export interface AnalyzeOutputs {
  normals?: Map<number, [number, number]>;
  shearsY?: Map<number, [number, number]>;
  shearsZ?: Map<number, [number, number]>;
  torsions?: Map<number, [number, number]>;
  bendingsY?: Map<number, [number, number]>;
  bendingsZ?: Map<number, [number, number]>;
  membraneXX?: Map<number, Node>;
  membraneYY?: Map<number, Node>;
  membraneXY?: Map<number, Node>;
  bendingXX?: Map<number, Node>;
  bendingYY?: Map<number, Node>;
  bendingXY?: Map<number, Node>;
}
export function deform(nodes: Node[], elements: number[][], nodeInputs: NodeInputs,
  elementInputs: ElementInputs): DeformOutputs | undefined;
export function analyze(nodes: Node[], elements: number[][], elementInputs: ElementInputs,
  deformOutputs: DeformOutputs): AnalyzeOutputs;
