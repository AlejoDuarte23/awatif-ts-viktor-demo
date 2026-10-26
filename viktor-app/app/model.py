import math
from dataclasses import asdict, dataclass
from typing import Any

from meshpy import triangle

Vector6 = list[float]
Point3 = list[float]
Triangle = list[int]


MESH_DENSITY_PRESETS: dict[str, dict[str, int]] = {
    "Coarse": {
        "circumference_divisions_per_stiffener": 2,
        "tube_height_divisions": 4,
        "stiffener_divisions": 2,
        "plate_mesh_divisions": 5,
    },
    "Medium": {
        "circumference_divisions_per_stiffener": 3,
        "tube_height_divisions": 4,
        "stiffener_divisions": 2,
        "plate_mesh_divisions": 6,
    },
    "Fine": {
        "circumference_divisions_per_stiffener": 4,
        "tube_height_divisions": 6,
        "stiffener_divisions": 3,
        "plate_mesh_divisions": 8,
    },
}


@dataclass(frozen=True)
class GeometryInputs:
    tube_radius: float = 100.0
    tube_height: float = 300.0
    tube_thickness: float = 8.0
    mesh_density: str = "Medium"
    stiffener_count: int = 7
    stiffener_height: float = 150.0
    stiffener_base: float = 110.0
    stiffener_thickness: float = 10.0
    plate_radius: float = 220.0
    bolt_count: int = 7
    bolt_nominal_diameter: float = 20.0
    bolt_diameter: float = 22.0
    bolt_center_edge_distance: float = 50.0
    plate_thickness: float = 20.0
    elasticity: float = 200_000.0
    poisson_ratio: float = 0.30
    yield_strength: float = 280.0

    def _mesh_setting(self, name: str) -> int:
        return MESH_DENSITY_PRESETS[self.mesh_density][name]

    @property
    def tube_circumference_divisions(self) -> int:
        multiplier = self._mesh_setting("circumference_divisions_per_stiffener")
        minimum_multiplier = math.ceil(8 / self.stiffener_count)
        return self.stiffener_count * max(multiplier, minimum_multiplier)

    @property
    def tube_height_divisions(self) -> int:
        return self._mesh_setting("tube_height_divisions")

    @property
    def stiffener_divisions(self) -> int:
        return self._mesh_setting("stiffener_divisions")

    @property
    def plate_mesh_divisions(self) -> int:
        return self._mesh_setting("plate_mesh_divisions")


@dataclass(frozen=True)
class GeometryDesignInputs:
    input_method: str = "Relative"
    tube_diameter: float = 200.0
    tube_height: float = 300.0
    tube_thickness: float = 8.0
    plate_projection: float = 120.0
    plate_diameter: float = 440.0
    plate_thickness: float = 20.0
    bolt_count: int = 7
    bolt_diameter: float = 20.0
    hole_clearance: float = 2.0
    hole_diameter: float = 22.0
    bolt_center_edge_distance: float = 50.0
    match_anchor_count: bool = True
    stiffener_count: int = 7
    stiffener_height_ratio: float = 50.0
    stiffener_base_ratio: float = 91.67
    stiffener_height: float = 150.0
    stiffener_base: float = 110.0
    stiffener_thickness: float = 10.0
    elasticity: float = 200_000.0
    poisson_ratio: float = 0.30
    yield_strength: float = 280.0
    mesh_density: str = "Medium"


def resolve_geometry_design(design: GeometryDesignInputs) -> GeometryInputs:
    if design.input_method not in {"Relative", "Advanced absolute"}:
        raise ValueError("Input method must be Relative or Advanced absolute.")
    if design.tube_diameter <= 0:
        raise ValueError("Tube outside diameter must be larger than zero.")

    tube_radius = design.tube_diameter / 2
    if design.input_method == "Relative":
        if design.plate_projection <= 0:
            raise ValueError("Plate projection must be larger than zero.")
        if design.hole_clearance < 0:
            raise ValueError("Hole clearance cannot be negative.")
        if not 0 < design.stiffener_height_ratio <= 100:
            raise ValueError("Stiffener height ratio must be between 0 and 100%.")
        if not 0 < design.stiffener_base_ratio <= 100:
            raise ValueError("Stiffener base ratio must be between 0 and 100%.")

        plate_radius = tube_radius + design.plate_projection
        hole_diameter = design.bolt_diameter + design.hole_clearance
        stiffener_height = design.tube_height * design.stiffener_height_ratio / 100
        stiffener_base = design.plate_projection * design.stiffener_base_ratio / 100
        stiffener_count = design.bolt_count if design.match_anchor_count else design.stiffener_count
    else:
        plate_radius = design.plate_diameter / 2
        hole_diameter = design.hole_diameter
        stiffener_height = design.stiffener_height
        stiffener_base = design.stiffener_base
        stiffener_count = design.stiffener_count

    geometry = GeometryInputs(
        tube_radius=tube_radius,
        tube_height=design.tube_height,
        tube_thickness=design.tube_thickness,
        mesh_density=design.mesh_density,
        stiffener_count=int(round(stiffener_count)),
        stiffener_height=stiffener_height,
        stiffener_base=stiffener_base,
        stiffener_thickness=design.stiffener_thickness,
        plate_radius=plate_radius,
        bolt_count=int(round(design.bolt_count)),
        bolt_nominal_diameter=design.bolt_diameter,
        bolt_diameter=hole_diameter,
        bolt_center_edge_distance=design.bolt_center_edge_distance,
        plate_thickness=design.plate_thickness,
        elasticity=design.elasticity,
        poisson_ratio=design.poisson_ratio,
        yield_strength=design.yield_strength,
    )
    validate_inputs(geometry)
    return geometry


def derived_geometry_values(geometry: GeometryInputs) -> dict[str, float]:
    return {
        "plate_diameter": 2 * geometry.plate_radius,
        "hole_diameter": geometry.bolt_diameter,
        "bolt_circle_diameter": 2 * _bolt_circle_radius(geometry),
        "clear_edge_distance": (geometry.bolt_center_edge_distance - geometry.bolt_diameter / 2),
        "stiffener_height": geometry.stiffener_height,
        "stiffener_base": geometry.stiffener_base,
    }


@dataclass(frozen=True)
class LoadInputs:
    axial_compression: float = 20.0
    shear_x: float = 0.0
    shear_y: float = 20.0
    moment_x: float = -10.0
    moment_y: float = 0.0
    torsion_z: float = 0.0


@dataclass(frozen=True)
class ViewInputs:
    show_mesh: bool = False
    deformation_scale: float = 100.0
    result_component: str = "von_mises"


def validate_inputs(geometry: GeometryInputs) -> None:
    if geometry.mesh_density not in MESH_DENSITY_PRESETS:
        raise ValueError("Mesh density must be Coarse, Medium, or Fine.")

    positive = {
        "Tube radius": geometry.tube_radius,
        "Tube height": geometry.tube_height,
        "Tube thickness": geometry.tube_thickness,
        "Stiffener height": geometry.stiffener_height,
        "Stiffener base": geometry.stiffener_base,
        "Stiffener thickness": geometry.stiffener_thickness,
        "Plate radius": geometry.plate_radius,
        "Hole diameter": geometry.bolt_diameter,
        "Nominal bolt diameter": geometry.bolt_nominal_diameter,
        "Bolt center edge distance": geometry.bolt_center_edge_distance,
        "Plate thickness": geometry.plate_thickness,
        "Elasticity": geometry.elasticity,
        "Yield strength": geometry.yield_strength,
    }
    for label, value in positive.items():
        if value <= 0:
            raise ValueError(f"{label} must be larger than zero.")

    if geometry.plate_radius <= geometry.tube_radius:
        raise ValueError("Plate diameter must be larger than the tube outside diameter.")
    if geometry.tube_radius + geometry.stiffener_base > geometry.plate_radius:
        raise ValueError(
            "Stiffener base exceeds the plate projection. Reduce the base ratio "
            "or increase the plate projection."
        )
    if geometry.stiffener_height >= geometry.tube_height:
        raise ValueError("Stiffener height must remain below the tube height.")
    if geometry.bolt_count < 3:
        raise ValueError("Use at least three bolts.")
    if geometry.stiffener_count < 3:
        raise ValueError("Use at least three stiffeners.")
    if not 0 < geometry.poisson_ratio < 0.5:
        raise ValueError("Poisson ratio must be between 0 and 0.5.")

    bolt_radius = _bolt_circle_radius(geometry)
    hole_radius = geometry.bolt_diameter / 2
    if geometry.bolt_center_edge_distance <= hole_radius:
        raise ValueError("Bolt center edge distance must be larger than half the hole diameter.")
    if bolt_radius <= 0:
        raise ValueError("Bolt center edge distance places the bolts outside the plate.")
    if bolt_radius - hole_radius <= geometry.tube_radius + 5:
        raise ValueError(
            "Anchor holes are too close to the tube. Increase plate projection, "
            "reduce center edge distance, or reduce the hole diameter."
        )


def build_payload(
    geometry: GeometryInputs,
    loads: LoadInputs,
    view: ViewInputs,
    *,
    mode: str,
) -> dict[str, Any]:
    validate_inputs(geometry)

    nodes, elements, components, element_thicknesses = _create_connected_shell_mesh(geometry)
    bolt_centers = _bolt_centers(geometry)
    bolt_node_groups = _find_bolt_boundary_nodes(
        nodes,
        bolt_centers,
        geometry.bolt_diameter / 2,
    )
    support_nodes = sorted({node for group in bolt_node_groups for node in group})
    tube_top_nodes = _find_tube_top_nodes(
        nodes,
        components["tube"]["nodeIndices"],
        geometry.tube_height,
    )
    nodal_loads = _distribute_resultants(nodes, tube_top_nodes, loads)
    load_basis = _build_load_basis(nodes, tube_top_nodes)

    return {
        "mode": mode,
        "geometry": {
            "nodes": nodes,
            "plate": components["plate"],
            "tube": components["tube"],
            "stiffeners": components["stiffeners"],
            "boltCenters": [[x, y, 0.0] for x, y in bolt_centers],
            "foundation": {
                "width": geometry.plate_radius * 2.35,
                "depth": geometry.plate_radius * 2.35,
                "height": geometry.plate_radius * 0.95,
            },
        },
        "analysis": {
            "nodes": nodes,
            "elements": elements,
            "supports": [[node, [True, True, True, True, True, True]] for node in support_nodes],
            "loads": [[node, vector] for node, vector in sorted(nodal_loads.items())],
            "loadBasis": load_basis,
            "elasticity": geometry.elasticity,
            "poissonRatio": geometry.poisson_ratio,
            "yieldStrength": geometry.yield_strength,
            "elementThicknesses": element_thicknesses,
            "boltNodeGroups": bolt_node_groups,
            "tubeTopNodes": tube_top_nodes,
        },
        "input": {
            "geometry": asdict(geometry),
            "loads": asdict(loads),
            "view": asdict(view),
        },
        "metadata": {
            "meshDensity": geometry.mesh_density,
            "shellNodes": len(nodes),
            "shellElements": len(elements),
            "componentElements": {
                name: len(component["elements"]) for name, component in components.items()
            },
            "supportNodes": len(support_nodes),
            "tubeTopNodes": len(tube_top_nodes),
            "solver": "Awatif v2.0.0 triangular shell assembly",
            "yieldStrength": geometry.yield_strength,
            "assumption": (
                "Awatif performs a linear-elastic analysis of connected plate, tube, "
                "and stiffener shells. "
                "The shell meshes share weld-line nodes; tube resultants are applied "
                "at the tube top ring and bolt-hole boundaries are fully fixed. "
                f"The {geometry.yield_strength:g} MPa yield strength caps the color "
                "scale only; plastic redistribution is not calculated."
            ),
        },
    }


def _bolt_circle_radius(geometry: GeometryInputs) -> float:
    return geometry.plate_radius - geometry.bolt_center_edge_distance


def _bolt_centers(geometry: GeometryInputs) -> list[tuple[float, float]]:
    radius = _bolt_circle_radius(geometry)
    offset = math.pi / geometry.stiffener_count
    return [
        (
            radius * math.cos(offset + 2 * math.pi * index / geometry.bolt_count),
            radius * math.sin(offset + 2 * math.pi * index / geometry.bolt_count),
        )
        for index in range(geometry.bolt_count)
    ]


def _circle_points(
    center: tuple[float, float],
    radius: float,
    count: int,
    *,
    offset: float = 0.0,
) -> list[tuple[float, float]]:
    return [
        (
            center[0] + radius * math.cos(offset + 2 * math.pi * i / count),
            center[1] + radius * math.sin(offset + 2 * math.pi * i / count),
        )
        for i in range(count)
    ]


def _analysis_angles(geometry: GeometryInputs) -> list[float]:
    angles = {
        2 * math.pi * index / max(8, geometry.tube_circumference_divisions)
        for index in range(max(8, geometry.tube_circumference_divisions))
    }
    angles.update(
        2 * math.pi * index / geometry.stiffener_count for index in range(geometry.stiffener_count)
    )
    return sorted(angles)


def _tube_z_levels(geometry: GeometryInputs) -> list[float]:
    lower_divisions = max(1, geometry.stiffener_divisions)
    upper_divisions = max(1, geometry.tube_height_divisions - lower_divisions)
    levels = [
        geometry.stiffener_height * index / lower_divisions for index in range(lower_divisions + 1)
    ]
    levels.extend(
        geometry.stiffener_height
        + (geometry.tube_height - geometry.stiffener_height) * index / upper_divisions
        for index in range(1, upper_divisions + 1)
    )
    return levels


def _create_plate_mesh(geometry: GeometryInputs) -> tuple[list[Point3], list[Triangle]]:
    outer_count = max(28, geometry.plate_mesh_divisions * 4)
    hole_count = 6
    interface_angles = _analysis_angles(geometry)

    points = _circle_points((0.0, 0.0), geometry.plate_radius, outer_count)
    facets = [(i, (i + 1) % outer_count) for i in range(outer_count)]
    holes = _bolt_centers(geometry)
    hole_radius = geometry.bolt_diameter / 2

    for center in holes:
        polygon = _circle_points(center, hole_radius, hole_count)
        start = len(points)
        points.extend(polygon)
        facets.extend((start + i, start + ((i + 1) % hole_count)) for i in range(hole_count))

    # Force the tube weld ring and every stiffener foot into the triangulation.
    points.extend(
        [
            (geometry.tube_radius * math.cos(angle), geometry.tube_radius * math.sin(angle))
            for angle in interface_angles
        ]
    )
    for index in range(geometry.stiffener_count):
        angle = 2 * math.pi * index / geometry.stiffener_count
        for division in range(1, geometry.stiffener_divisions + 1):
            radius = geometry.tube_radius + (
                geometry.stiffener_base * division / geometry.stiffener_divisions
            )
            points.append((radius * math.cos(angle), radius * math.sin(angle)))

    mesh_info = triangle.MeshInfo()
    mesh_info.set_points(points)
    mesh_info.set_facets(facets)
    mesh_info.set_holes(holes)

    target_area = math.pi * geometry.plate_radius**2 / (2 * geometry.plate_mesh_divisions**2)

    mesh = triangle.build(mesh_info, max_volume=target_area, min_angle=22.0)
    nodes: list[Point3] = [[float(x), float(y), 0.0] for x, y in mesh.points]
    elements: list[Triangle] = []

    for raw in mesh.elements:
        element = [int(raw[0]), int(raw[1]), int(raw[2])]
        a, b, c = (nodes[index] for index in element)
        signed_twice_area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if signed_twice_area < 0:
            element[1], element[2] = element[2], element[1]
        elements.append(element)

    return nodes, elements


def _create_connected_shell_mesh(
    geometry: GeometryInputs,
) -> tuple[list[Point3], list[Triangle], dict[str, dict[str, Any]], list[float]]:
    local_components = {
        "plate": _create_plate_mesh(geometry),
        "tube": _create_tube_mesh(geometry),
        "stiffeners": _create_stiffener_mesh(geometry),
    }
    component_thicknesses = {
        "plate": geometry.plate_thickness,
        "tube": geometry.tube_thickness,
        "stiffeners": geometry.stiffener_thickness,
    }

    nodes: list[Point3] = []
    elements: list[Triangle] = []
    element_thicknesses: list[float] = []
    components: dict[str, dict[str, Any]] = {}
    node_lookup: dict[tuple[float, float, float], int] = {}

    def node_key(node: Point3) -> tuple[float, float, float]:
        return round(node[0], 8), round(node[1], 8), round(node[2], 8)

    for name, (local_nodes, local_elements) in local_components.items():
        local_to_global: list[int] = []
        for local_node in local_nodes:
            key = node_key(local_node)
            global_index = node_lookup.get(key)
            if global_index is None:
                global_index = len(nodes)
                node_lookup[key] = global_index
                nodes.append(local_node)
            local_to_global.append(global_index)

        component_elements: list[Triangle] = []
        component_element_indices: list[int] = []
        for local_element in local_elements:
            element = [local_to_global[index] for index in local_element]
            component_elements.append(element)
            component_element_indices.append(len(elements))
            elements.append(element)
            element_thicknesses.append(component_thicknesses[name])

        components[name] = {
            "elements": component_elements,
            "elementIndices": component_element_indices,
            "nodeIndices": sorted(set(local_to_global)),
        }

    return nodes, elements, components, element_thicknesses


def _find_bolt_boundary_nodes(
    nodes: list[Point3],
    centers: list[tuple[float, float]],
    hole_radius: float,
) -> list[list[int]]:
    groups: list[list[int]] = []
    tolerance = max(1e-5, hole_radius * 1e-5)

    for cx, cy in centers:
        ranked = sorted(
            (
                (abs(math.hypot(node[0] - cx, node[1] - cy) - hole_radius), i)
                for i, node in enumerate(nodes)
            ),
            key=lambda pair: pair[0],
        )
        group = [index for distance, index in ranked if distance <= tolerance]
        if len(group) < 3:
            group = [index for _, index in ranked[:6]]
        groups.append(sorted(set(group)))

    return groups


def _find_tube_top_nodes(
    nodes: list[Point3], tube_node_indices: list[int], height: float
) -> list[int]:
    tolerance = max(1e-5, height * 1e-6)
    top_nodes = [index for index in tube_node_indices if abs(nodes[index][2] - height) <= tolerance]
    if len(top_nodes) < 3:
        raise ValueError("No tube-top nodes were found for the load resultants.")
    return sorted(top_nodes)


def _distribute_resultants(
    nodes: list[Point3],
    interface_nodes: list[int],
    loads: LoadInputs,
) -> dict[int, Vector6]:
    if not interface_nodes:
        raise ValueError("No tube/plate interface nodes were found.")

    # Build the minimum-norm nodal force vector that reproduces all six
    # resultants about the tube-top centre. This also works when the tube ring
    # contains extra nodes at stiffener weld lines and is not perfectly uniform.
    target = [
        loads.shear_x * 1_000,
        loads.shear_y * 1_000,
        -loads.axial_compression * 1_000,
        loads.moment_x * 1_000_000,
        loads.moment_y * 1_000_000,
        loads.torsion_z * 1_000_000,
    ]
    columns: list[list[float]] = []
    for index in interface_nodes:
        x, y, _ = nodes[index]
        columns.extend(
            (
                [1.0, 0.0, 0.0, 0.0, 0.0, -y],
                [0.0, 1.0, 0.0, 0.0, 0.0, x],
                [0.0, 0.0, 1.0, y, -x, 0.0],
            )
        )

    normal = [[0.0 for _ in range(6)] for _ in range(6)]
    for column in columns:
        for row in range(6):
            for col in range(6):
                normal[row][col] += column[row] * column[col]
    multipliers = _solve_linear_system(normal, target)
    nodal_values = [sum(column[row] * multipliers[row] for row in range(6)) for column in columns]

    return {
        node: [
            nodal_values[position * 3],
            nodal_values[position * 3 + 1],
            nodal_values[position * 3 + 2],
            0.0,
            0.0,
            0.0,
        ]
        for position, node in enumerate(interface_nodes)
    }


def _build_load_basis(
    nodes: list[Point3], interface_nodes: list[int]
) -> dict[str, list[list[Any]]]:
    zero = {
        "axial_compression": 0.0,
        "shear_x": 0.0,
        "shear_y": 0.0,
        "moment_x": 0.0,
        "moment_y": 0.0,
        "torsion_z": 0.0,
    }
    unit_cases = {name: LoadInputs(**(zero | {name: 1.0})) for name in zero}
    return {
        name: [
            [node, vector]
            for node, vector in sorted(
                _distribute_resultants(nodes, interface_nodes, unit_loads).items()
            )
        ]
        for name, unit_loads in unit_cases.items()
    }


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    augmented = [row.copy() + [value] for row, value in zip(matrix, vector)]
    size = len(vector)

    for pivot in range(size):
        pivot_row = max(range(pivot, size), key=lambda row: abs(augmented[row][pivot]))
        if abs(augmented[pivot_row][pivot]) < 1e-12:
            raise ValueError("The tube-top load ring cannot reproduce all resultants.")
        augmented[pivot], augmented[pivot_row] = augmented[pivot_row], augmented[pivot]
        pivot_value = augmented[pivot][pivot]
        augmented[pivot] = [value / pivot_value for value in augmented[pivot]]

        for row in range(size):
            if row == pivot:
                continue
            factor = augmented[row][pivot]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[pivot])
            ]

    return [augmented[row][-1] for row in range(size)]


def _create_tube_mesh(geometry: GeometryInputs) -> tuple[list[Point3], list[Triangle]]:
    angles = _analysis_angles(geometry)
    z_levels = _tube_z_levels(geometry)
    around = len(angles)
    nodes: list[Point3] = []
    for z in z_levels:
        for angle in angles:
            nodes.append(
                [
                    geometry.tube_radius * math.cos(angle),
                    geometry.tube_radius * math.sin(angle),
                    z,
                ]
            )

    elements: list[Triangle] = []
    for level in range(len(z_levels) - 1):
        for index in range(around):
            next_index = (index + 1) % around
            a = level * around + index
            b = level * around + next_index
            c = (level + 1) * around + index
            d = (level + 1) * around + next_index
            if (level + index) % 2 == 0:
                elements.extend(([a, b, d], [a, d, c]))
            else:
                elements.extend(([a, b, c], [b, d, c]))
    return nodes, elements


def _create_stiffener_mesh(
    geometry: GeometryInputs,
) -> tuple[list[Point3], list[Triangle]]:
    divisions = max(1, int(geometry.stiffener_divisions))
    nodes: list[Point3] = []
    elements: list[Triangle] = []

    for stiffener in range(geometry.stiffener_count):
        angle = 2 * math.pi * stiffener / geometry.stiffener_count
        index_map: dict[tuple[int, int], int] = {}

        for row in range(divisions + 1):
            for column in range(divisions - row + 1):
                radial = geometry.stiffener_base * column / divisions
                z = geometry.stiffener_height * row / divisions
                radius = geometry.tube_radius + radial
                index_map[(column, row)] = len(nodes)
                nodes.append([radius * math.cos(angle), radius * math.sin(angle), z])

        for row in range(divisions):
            row_length = divisions - row + 1
            for column in range(row_length - 1):
                a = index_map[(column, row)]
                b = index_map[(column + 1, row)]
                c = index_map[(column, row + 1)]
                elements.append([a, b, c])
                if column < divisions - row - 1:
                    d = index_map[(column + 1, row + 1)]
                    elements.append([b, d, c])

    return nodes, elements
