import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { element, errorText } from "./dom.ts";
import { combineLoadBasis } from "./loads.ts";
import { calculateContour } from "./results.ts";
import { solveInBackground } from "./analysis-client.ts";
import type {
  ComponentName,
  Contour,
  Deformation,
  LoadName,
  Loads,
  Payload,
  Point3,
  ShellComponent,
  ShellResults,
} from "./types.ts";

interface ViewerState {
  meshVisible: boolean;
  showDeformed: boolean;
  deformationScale: number;
  currentLoads: Loads;
  solving: boolean;
  shellMeshes: Map<ComponentName, { mesh: THREE.Mesh; edges: THREE.LineSegments }>;
  deformation: Deformation | null;
  shellResults: ShellResults | null;
  contourValues: number[] | null;
  contour: Contour | null;
}

(() => {
  const data = window.__BASE_PLATE_PAYLOAD__;
  if (!data) throw new Error("The WebView model data is missing.");
  const payload: Payload = data;
  const errorPanel = element("#error-panel");
  const errorMessage = element("#error-message");
  const solveIndicator = element("#solve-indicator");
  const solveDetail = element("#solve-detail");

  function showError(error: unknown) {
    solveIndicator.hidden = true;
    errorPanel.hidden = false;
    errorMessage.textContent = errorText(error);
    element("#status-pill").textContent = "FAILED";
    element("#status-pill").style.color = "#b42318";
  }

  const viewport = element("#viewport");
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  viewport.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100000);
  camera.up.set(0, 0, 1);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x71808b, 2.1));
  const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
  keyLight.position.set(550, -420, 780);
  scene.add(keyLight);

  const modelRoot = new THREE.Group();
  const loadRoot = new THREE.Group();
  const shellRoot = new THREE.Group();
  const wireRoot = new THREE.Group();
  scene.add(modelRoot, loadRoot, shellRoot, wireRoot);

  const state: ViewerState = {
    meshVisible: Boolean(payload.input.view.show_mesh),
    showDeformed: false,
    deformationScale: payload.input.view.deformation_scale,
    currentLoads: { ...payload.input.loads },
    solving: false,
    shellMeshes: new Map(),
    deformation: null,
    shellResults: null,
    contourValues: null,
    contour: null,
  };

  const materials = {
    plate: new THREE.MeshStandardMaterial({
      color: 0x9a5d3b,
      roughness: 0.72,
      metalness: 0.12,
      side: THREE.DoubleSide,
    }),
    tube: new THREE.MeshStandardMaterial({
      color: 0x2b8796,
      roughness: 0.63,
      metalness: 0.12,
      side: THREE.DoubleSide,
    }),
    stiffener: new THREE.MeshStandardMaterial({
      color: 0xc99444,
      roughness: 0.66,
      metalness: 0.08,
      side: THREE.DoubleSide,
    }),
    result: new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.7,
      metalness: 0.05,
      side: THREE.DoubleSide,
    }),
    wire: new THREE.LineBasicMaterial({
      color: 0x163b4c,
      transparent: true,
      opacity: 0.58,
      depthTest: true,
      depthWrite: false,
    }),
  };

  [materials.plate, materials.tube, materials.stiffener, materials.result].forEach((material) => {
    material.polygonOffset = true;
    material.polygonOffsetFactor = 1;
    material.polygonOffsetUnits = 1;
  });

  const contourStops: [number, THREE.Color][] = [
    [0.0, new THREE.Color("#172554")],
    [0.2, new THREE.Color("#1665a8")],
    [0.42, new THREE.Color("#24b5b8")],
    [0.64, new THREE.Color("#f2d34f")],
    [0.82, new THREE.Color("#ec6a32")],
    [1.0, new THREE.Color("#8f1838")],
  ];

  function makeTriangleGeometry(
    component: ShellComponent,
    nodesOverride: Point3[] | null = null,
    faceColors: THREE.Color[] | null = null,
  ) {
    const nodes = nodesOverride || component.nodes;
    const positions: number[] = [];
    const colors: number[] = [];

    component.elements.forEach((element, elementIndex) => {
      const color = faceColors?.[elementIndex];
      element.forEach((nodeIndex) => {
        const point = nodes[nodeIndex];
        positions.push(point[0], point[1], point[2]);
        if (color) colors.push(color.r, color.g, color.b);
      });
    });

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    if (colors.length) {
      geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    }
    geometry.computeVertexNormals();
    geometry.computeBoundingSphere();
    return geometry;
  }

  function disposeObject(object: THREE.Mesh | THREE.LineSegments) {
    if (!object) return;
    object.parent?.remove(object);
    object.geometry?.dispose();
  }

  function renderShellAssembly() {
    state.shellMeshes.forEach(({ mesh, edges }) => {
      disposeObject(mesh);
      disposeObject(edges);
    });
    state.shellMeshes.clear();

    let nodes = payload.geometry.nodes;
    if (state.showDeformed && state.deformation) {
      const scale = state.deformationScale;
      nodes = payload.analysis.nodes.map((point, index) => {
        const displacement = state.deformation!.deformations.get(index) || [0, 0, 0];
        return [
          point[0] + displacement[0] * scale,
          point[1] + displacement[1] * scale,
          point[2] + displacement[2] * scale,
        ];
      });
    }

    const components: [ComponentName, ShellComponent][] = [
      ["plate", payload.geometry.plate],
      ["tube", payload.geometry.tube],
      ["stiffeners", payload.geometry.stiffeners],
    ];
    const componentMaterials = {
      plate: materials.plate,
      tube: materials.tube,
      stiffeners: materials.stiffener,
    };
    components.forEach(([name, component]) => {
      const colors = state.contourValues
        ? component.elementIndices.map((elementIndex) =>
            contourColor(
              state.contourValues![elementIndex],
              state.contour!.min,
              state.contour!.max,
            ),
          )
        : null;
      const material = colors ? materials.result : componentMaterials[name];
      const geometry = makeTriangleGeometry(component, nodes, colors);
      const mesh = new THREE.Mesh(geometry, material);
      const edges = new THREE.LineSegments(new THREE.WireframeGeometry(geometry), materials.wire);
      edges.renderOrder = 10;
      shellRoot.add(mesh);
      wireRoot.add(edges);
      state.shellMeshes.set(name, { mesh, edges });
    });
    syncMeshVisibility();
  }

  function contourColor(value: number, minimum: number, maximum: number) {
    const span = maximum - minimum;
    const t = span > 1e-12 ? THREE.MathUtils.clamp((value - minimum) / span, 0, 1) : 0.5;
    for (let index = 1; index < contourStops.length; index++) {
      const [upperT, upperColor] = contourStops[index];
      const [lowerT, lowerColor] = contourStops[index - 1];
      if (t <= upperT) {
        const local = (t - lowerT) / (upperT - lowerT);
        return lowerColor.clone().lerp(upperColor, local);
      }
    }
    return contourStops[contourStops.length - 1][1].clone();
  }

  function addFoundation() {
    const foundation = payload.geometry.foundation;
    const geometry = new THREE.BoxGeometry(foundation.width, foundation.depth, foundation.height);
    const material = new THREE.MeshStandardMaterial({
      color: 0x9aa4aa,
      roughness: 0.95,
      transparent: true,
      opacity: 0.35,
    });
    const block = new THREE.Mesh(geometry, material);
    block.position.z = -foundation.height / 2 - payload.input.geometry.plate_thickness;
    modelRoot.add(block);
  }

  function addBolts() {
    const diameter = Math.max(6, payload.input.geometry.bolt_nominal_diameter);
    const plateThickness = payload.input.geometry.plate_thickness;
    const shaftLength = Math.max(100, payload.input.geometry.plate_radius * 0.62);
    const boltMaterial = new THREE.MeshStandardMaterial({
      color: 0xc56a35,
      roughness: 0.45,
      metalness: 0.42,
    });

    payload.geometry.boltCenters.forEach(([x, y]) => {
      const shaft = new THREE.Mesh(
        new THREE.CylinderGeometry(diameter / 2, diameter / 2, shaftLength, 12),
        boltMaterial,
      );
      shaft.rotation.x = Math.PI / 2;
      shaft.position.set(x, y, plateThickness - shaftLength / 2);
      modelRoot.add(shaft);

      const washer = new THREE.Mesh(
        new THREE.CylinderGeometry(diameter * 0.95, diameter * 0.95, 5, 16),
        boltMaterial,
      );
      washer.rotation.x = Math.PI / 2;
      washer.position.set(x, y, plateThickness + 3);
      modelRoot.add(washer);
    });
  }

  function addLoadPathHalo() {
    const radius = payload.input.geometry.tube_radius;
    const halo = new THREE.Mesh(
      new THREE.TorusGeometry(radius, 2.2, 8, 72),
      new THREE.MeshBasicMaterial({
        color: 0x26a6b5,
        transparent: true,
        opacity: 0.68,
      }),
    );
    halo.position.z = 2;
    modelRoot.add(halo);
  }

  function clearGroup(group: THREE.Group) {
    while (group.children.length) group.remove(group.children[0]);
  }

  function addLoads(loads = state.currentLoads) {
    clearGroup(loadRoot);
    const top = new THREE.Vector3(0, 0, payload.input.geometry.tube_height);
    const characteristic = payload.input.geometry.plate_radius * 0.6;
    const loadApplicationPoint = top.clone().add(new THREE.Vector3(0, 0, characteristic * 0.7));
    const loadArrowColor = 0xc62828;
    const loadShaftRadius = 2.4;
    const loadMaterial = new THREE.MeshBasicMaterial({ color: loadArrowColor });

    function makeForceArrow(direction: THREE.Vector3) {
      const arrow = new THREE.Group();
      const normalizedDirection = direction.clone().normalize();
      const headLength = 28;
      const shaftLength = characteristic - headLength;
      const orientation = new THREE.Quaternion().setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        normalizedDirection,
      );
      const shaft = new THREE.Mesh(
        new THREE.CylinderGeometry(loadShaftRadius, loadShaftRadius, shaftLength, 10),
        loadMaterial,
      );
      shaft.quaternion.copy(orientation);
      shaft.position
        .copy(loadApplicationPoint)
        .addScaledVector(normalizedDirection, shaftLength / 2);
      arrow.add(shaft);

      const arrowhead = new THREE.Mesh(new THREE.ConeGeometry(15, headLength, 12), loadMaterial);
      arrowhead.quaternion.copy(orientation);
      arrowhead.position
        .copy(loadApplicationPoint)
        .addScaledVector(normalizedDirection, shaftLength + headLength / 2);
      arrow.add(arrowhead);
      return arrow;
    }

    const forceArrows: [number, THREE.Vector3][] = [
      [loads.shear_x, new THREE.Vector3(Math.sign(loads.shear_x) || 1, 0, 0)],
      [loads.shear_y, new THREE.Vector3(0, Math.sign(loads.shear_y) || 1, 0)],
      [loads.axial_compression, new THREE.Vector3(0, 0, -1)],
    ];
    forceArrows.forEach(([magnitude, direction]) => {
      if (Math.abs(magnitude) < 1e-12) return;
      loadRoot.add(makeForceArrow(direction));
    });

    const momentRings: [number, string][] = [
      [loads.moment_x, "x"],
      [loads.moment_y, "y"],
      [loads.torsion_z, "z"],
    ];
    momentRings.forEach(([magnitude, axis], index) => {
      if (Math.abs(magnitude) < 1e-12) return;
      const radius = characteristic * (0.55 + index * 0.05);
      const arc = Math.PI * 1.65;
      // The torus normal is transformed onto the selected global moment axis,
      // so its winding follows the usual right-hand-rule sign directly.
      const direction = Math.sign(magnitude) || 1;
      const symbol = new THREE.Group();
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(radius, loadShaftRadius, 8, 54, arc),
        loadMaterial,
      );
      ring.scale.y = direction;
      symbol.add(ring);

      const endAngle = direction * arc;
      const endpoint = new THREE.Vector3(
        radius * Math.cos(endAngle),
        radius * Math.sin(endAngle),
        0,
      );
      const tangent = new THREE.Vector3(
        -direction * Math.sin(endAngle),
        direction * Math.cos(endAngle),
        0,
      ).normalize();
      const arrowLength = Math.max(16, characteristic * 0.16);
      const arrowhead = new THREE.Mesh(
        new THREE.ConeGeometry(arrowLength * 0.42, arrowLength, 12),
        loadMaterial,
      );
      arrowhead.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
      // ConeGeometry points along +Y. Position its base at the end of the
      // curved shaft and extend its tip forward along the tangent.
      arrowhead.position.copy(endpoint).addScaledVector(tangent, arrowLength / 2);
      symbol.add(arrowhead);

      if (axis === "x") symbol.rotation.y = Math.PI / 2;
      if (axis === "y") symbol.rotation.x = Math.PI / 2;
      symbol.position.copy(loadApplicationPoint);
      loadRoot.add(symbol);
    });
  }

  function syncMeshVisibility() {
    wireRoot.visible = state.meshVisible;
    const button = element<HTMLButtonElement>("#toggle-mesh");
    button.setAttribute("aria-pressed", String(state.meshVisible));
    button.textContent = state.meshVisible ? "Hide mesh" : "Show mesh";
  }

  function fitView() {
    const bounds = new THREE.Box3().setFromObject(modelRoot);
    bounds.union(new THREE.Box3().setFromObject(shellRoot));
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    const extent = Math.max(size.x, size.y, size.z, 1);
    camera.position.set(
      center.x + extent * 1.38,
      center.y - extent * 1.48,
      center.z + extent * 1.1,
    );
    camera.near = Math.max(0.1, extent / 2000);
    camera.far = extent * 40;
    camera.updateProjectionMatrix();
    controls.target.copy(center).add(new THREE.Vector3(0, 0, size.z * 0.08));
    controls.update();
  }

  function addLoadChips(loads = state.currentLoads) {
    const chips = element("#load-chips");
    chips.replaceChildren();
    const values: [string, number, string][] = [
      ["N", loads.axial_compression, "kN"],
      ["Vx", loads.shear_x, "kN"],
      ["Vy", loads.shear_y, "kN"],
      ["Mx", loads.moment_x, "kN·m"],
      ["My", loads.moment_y, "kN·m"],
      ["Tz", loads.torsion_z, "kN·m"],
    ];
    values.forEach(([label, value, unit]) => {
      const chip = document.createElement("span");
      chip.textContent = `${label} ${formatNumber(value)} ${unit}`;
      chips.appendChild(chip);
    });
  }

  function formatNumber(value: number, digits = 2) {
    if (!Number.isFinite(value)) return "—";
    const absolute = Math.abs(value);
    if (absolute > 0 && (absolute >= 1e5 || absolute < 1e-3)) {
      return value.toExponential(2);
    }
    return value.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    });
  }

  function readLoadsFromControls(): Loads {
    const fields = {
      axial_compression: "#load-axial-compression",
      shear_x: "#load-shear-x",
      shear_y: "#load-shear-y",
      moment_x: "#load-moment-x",
      moment_y: "#load-moment-y",
      torsion_z: "#load-torsion-z",
    };
    return Object.fromEntries(
      Object.entries(fields).map(([name, selector]) => {
        const value = Number(element<HTMLInputElement>(selector).value);
        if (!Number.isFinite(value)) throw new Error(`Enter a valid value for ${name}.`);
        return [name, value];
      }),
    ) as Loads;
  }

  function populateAnalysisControls() {
    const fields = {
      axial_compression: "#load-axial-compression",
      shear_x: "#load-shear-x",
      shear_y: "#load-shear-y",
      moment_x: "#load-moment-x",
      moment_y: "#load-moment-y",
      torsion_z: "#load-torsion-z",
    };
    Object.entries(fields).forEach(([name, selector]) => {
      element<HTMLInputElement>(selector).value = String(state.currentLoads[name as LoadName]);
    });
    element<HTMLInputElement>("#deformation-scale").value = String(state.deformationScale);
    element("#deformation-scale-value").textContent = `${state.deformationScale}×`;
  }

  function displayResults() {
    if (!state.shellResults) return;
    state.contour = calculateContour(payload.analysis, state.shellResults);
    state.contourValues = state.contour.values;
    renderShellAssembly();

    element("#result-title").textContent = state.contour.title;
    element("#max-result-label").textContent = state.contour.isYieldLimited
      ? "PEAK ELASTIC STRESS"
      : `MAX ${state.contour.title.toUpperCase()}`;
    element("#max-result-unit").textContent = state.contour.unit;
    element("#max-stress").textContent = formatNumber(state.contour.maximumAbsolute);
    const exceedsYield =
      state.contour.isYieldLimited && state.contour.maximumAbsolute > state.contour.yieldStrength;
    element("#legend-max").textContent =
      `${exceedsYield ? "≥" : ""}${formatNumber(state.contour.max)}`;
    element("#legend-min").textContent = formatNumber(state.contour!.min);
    element("#legend-unit").textContent = state.contour.isYieldLimited
      ? `${state.contour.unit} · fy`
      : state.contour.unit;
    element("#legend").hidden = false;
    const statusPill = element("#status-pill");
    statusPill.textContent = exceedsYield ? "ELASTIC > FY" : "SOLVED";
    statusPill.dataset.state = exceedsYield ? "warning" : "ok";
  }

  async function runAwatifAnalysis() {
    if (state.solving) return;
    state.currentLoads = readLoadsFromControls();
    addLoads();
    addLoadChips();
    const analysis = {
      ...payload.analysis,
      loads: combineLoadBasis(payload.analysis, state.currentLoads),
    };
    const calculateButton = element<HTMLButtonElement>("#calculate-analysis");
    state.solving = true;
    calculateButton.disabled = true;
    errorPanel.hidden = true;
    solveIndicator.hidden = false;
    solveDetail.textContent = "Solving shell assembly…";
    const statusPill = element("#status-pill");
    statusPill.textContent = "SOLVING";
    statusPill.dataset.state = "";

    let deformation;
    let results;
    try {
      ({ deformation, results } = await solveInBackground(analysis, () => {
        statusPill.textContent = "COMPATIBILITY SOLVE";
        solveDetail.textContent = "Solving…";
      }));
    } finally {
      state.solving = false;
      calculateButton.disabled = false;
      solveIndicator.hidden = true;
    }

    let maximumDisplacement = 0;
    deformation.deformations.forEach((value) => {
      const magnitude = Math.hypot(value[0], value[1], value[2]);
      if (!Number.isFinite(magnitude)) {
        throw new Error("Awatif produced a non-finite displacement. Check the supports and mesh.");
      }
      maximumDisplacement = Math.max(maximumDisplacement, magnitude);
    });

    let reactionZ = 0;
    deformation.reactions.forEach((value) => {
      reactionZ += value[2] || 0;
    });

    state.deformation = deformation;
    state.shellResults = results;
    state.showDeformed = true;
    element<HTMLButtonElement>("#toggle-deformed").setAttribute("aria-pressed", "true");
    displayResults();
    element("#max-displacement").textContent = formatNumber(maximumDisplacement, 4);
    element("#reaction-z").textContent = formatNumber(reactionZ / 1000);
    element<HTMLButtonElement>("#toggle-deformed").disabled = false;
  }

  function initializeModel() {
    addFoundation();
    addBolts();
    addLoadPathHalo();
    addLoads();
    renderShellAssembly();
    syncMeshVisibility();
    fitView();

    element("#mode-label").textContent =
      payload.mode === "results" ? "Awatif shell assembly results" : "Geometry and loading";
    element("#result-title").textContent =
      payload.mode === "results" ? "Ready to calculate" : "Connection model";
    element("#status-pill").textContent = payload.mode === "results" ? "READY" : "MODEL";

    if (payload.mode === "results") {
      solveIndicator.hidden = true;
      element("#analysis-controls").hidden = false;
      populateAnalysisControls();
      element("#metric-three-label").textContent =
        `${payload.metadata.meshDensity.toUpperCase()} MESH`;
      element("#mesh-size").textContent = payload.metadata.shellElements.toLocaleString();
    } else {
      solveIndicator.hidden = true;
      const geometry = payload.input.geometry;
      element("#max-result-label").textContent = "PLATE DIAMETER";
      element("#max-stress").textContent = formatNumber(2 * geometry.plate_radius);
      element("#max-result-unit").textContent = "mm";
      element("#metric-two-label").textContent = "TUBE DIAMETER";
      element("#max-displacement").textContent = formatNumber(2 * geometry.tube_radius);
      element("#metric-three-label").textContent = "BOLT CIRCLE";
      element("#mesh-size").textContent = formatNumber(
        2 * (geometry.plate_radius - geometry.bolt_center_edge_distance),
      );
      element("#metric-three-unit").textContent = "mm";
      element("#metric-four-label").textContent =
        `${payload.metadata.meshDensity.toUpperCase()} MESH`;
      element("#reaction-z").textContent = payload.metadata.shellElements.toLocaleString();
      element("#metric-four-unit").textContent = "triangles";
    }
    element("#assumption").textContent = payload.metadata.assumption;
    addLoadChips();

    const deformedButton = element<HTMLButtonElement>("#toggle-deformed");
    deformedButton.disabled = !state.deformation;
    deformedButton.setAttribute("aria-pressed", String(state.showDeformed));
  }

  element<HTMLButtonElement>("#fit-view").addEventListener("click", fitView);
  element<HTMLButtonElement>("#toggle-mesh").addEventListener("click", () => {
    state.meshVisible = !state.meshVisible;
    syncMeshVisibility();
  });
  element<HTMLButtonElement>("#toggle-deformed").addEventListener("click", () => {
    if (!state.deformation) return;
    state.showDeformed = !state.showDeformed;
    element("#toggle-deformed").setAttribute("aria-pressed", String(state.showDeformed));
    renderShellAssembly();
  });
  element<HTMLButtonElement>("#calculate-analysis").addEventListener("click", () => {
    runAwatifAnalysis().catch(showError);
  });
  element<HTMLInputElement>("#deformation-scale").addEventListener("input", (event) => {
    state.deformationScale = Number((event.currentTarget as HTMLInputElement).value);
    element("#deformation-scale-value").textContent = `${state.deformationScale}×`;
    if (state.deformation && state.showDeformed) renderShellAssembly();
  });

  const resizeObserver = new ResizeObserver(() => {
    const width = Math.max(1, viewport.clientWidth);
    const height = Math.max(1, viewport.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  });
  resizeObserver.observe(viewport);

  function animate() {
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  try {
    initializeModel();
    animate();
  } catch (error) {
    showError(error);
  }
})();
