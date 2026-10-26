import importlib.util
import math
import sys
import unittest
from pathlib import Path

MODEL_PATH = Path(__file__).parents[1] / "app" / "model.py"
SPEC = importlib.util.spec_from_file_location("base_plate_model", MODEL_PATH)
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)

GeometryInputs = MODEL.GeometryInputs
GeometryDesignInputs = MODEL.GeometryDesignInputs
LoadInputs = MODEL.LoadInputs
ViewInputs = MODEL.ViewInputs
build_payload = MODEL.build_payload
derived_geometry_values = MODEL.derived_geometry_values
resolve_geometry_design = MODEL.resolve_geometry_design


class TestBasePlateModel(unittest.TestCase):
    def setUp(self):
        self.loads = LoadInputs(
            axial_compression=200.0,
            shear_x=20.0,
            shear_y=-10.0,
            moment_x=35.0,
            moment_y=-12.0,
            torsion_z=8.0,
        )
        self.payload = build_payload(
            GeometryInputs(),
            self.loads,
            ViewInputs(),
            mode="results",
        )

    def test_plate_contains_triangular_shell_elements(self):
        analysis = self.payload["analysis"]
        self.assertGreater(len(analysis["nodes"]), 20)
        self.assertGreater(len(analysis["elements"]), 20)
        self.assertTrue(all(len(element) == 3 for element in analysis["elements"]))
        self.assertEqual(analysis["yieldStrength"], 280.0)
        self.assertLess(len(self.payload["geometry"]["plate"]["elements"]), 350)

    def test_default_loads_align_mx_with_vy(self):
        loads = LoadInputs()
        self.assertEqual(loads.shear_x, 0.0)
        self.assertEqual(loads.shear_y, 20.0)
        self.assertEqual(loads.moment_x, -10.0)

    def test_relative_geometry_preserves_the_default_design(self):
        geometry = resolve_geometry_design(GeometryDesignInputs())
        derived = derived_geometry_values(geometry)

        self.assertEqual(geometry.tube_radius, 100.0)
        self.assertEqual(geometry.plate_radius, 220.0)
        self.assertEqual(geometry.bolt_diameter, 22.0)
        self.assertEqual(geometry.bolt_nominal_diameter, 20.0)
        self.assertEqual(geometry.stiffener_count, 7)
        self.assertTrue(math.isclose(geometry.stiffener_height, 150.0))
        self.assertTrue(math.isclose(geometry.stiffener_base, 110.004, abs_tol=1e-9))
        self.assertEqual(derived["plate_diameter"], 440.0)
        self.assertEqual(derived["bolt_circle_diameter"], 340.0)
        self.assertEqual(derived["clear_edge_distance"], 39.0)

    def test_advanced_geometry_uses_absolute_dimensions(self):
        geometry = resolve_geometry_design(
            GeometryDesignInputs(
                input_method="Advanced absolute",
                tube_diameter=240.0,
                plate_diameter=520.0,
                hole_diameter=26.0,
                stiffener_count=8,
                stiffener_height=175.0,
                stiffener_base=125.0,
            )
        )

        self.assertEqual(geometry.tube_radius, 120.0)
        self.assertEqual(geometry.plate_radius, 260.0)
        self.assertEqual(geometry.bolt_diameter, 26.0)
        self.assertEqual(geometry.stiffener_count, 8)
        self.assertEqual(geometry.stiffener_height, 175.0)
        self.assertEqual(geometry.stiffener_base, 125.0)

    def test_relative_geometry_can_use_an_independent_stiffener_count(self):
        geometry = resolve_geometry_design(
            GeometryDesignInputs(match_anchor_count=False, stiffener_count=5)
        )
        self.assertEqual(geometry.stiffener_count, 5)

    def test_every_bolt_has_supported_boundary_nodes(self):
        groups = self.payload["analysis"]["boltNodeGroups"]
        self.assertEqual(len(groups), GeometryInputs().bolt_count)
        self.assertTrue(all(len(group) >= 3 for group in groups))

    def test_mesh_avoids_skinny_triangles(self):
        nodes = self.payload["analysis"]["nodes"]
        for component_name in ("plate", "tube", "stiffeners"):
            minimum_angle = 180.0
            elements = self.payload["geometry"][component_name]["elements"]
            for element in elements:
                points = [nodes[index] for index in element]
                for origin, first, second in (
                    (points[0], points[1], points[2]),
                    (points[1], points[2], points[0]),
                    (points[2], points[0], points[1]),
                ):
                    vector_a = [first[i] - origin[i] for i in range(3)]
                    vector_b = [second[i] - origin[i] for i in range(3)]
                    length_a = math.sqrt(sum(value**2 for value in vector_a))
                    length_b = math.sqrt(sum(value**2 for value in vector_b))
                    cosine = sum(a * b for a, b in zip(vector_a, vector_b)) / (length_a * length_b)
                    angle = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
                    minimum_angle = min(minimum_angle, angle)
            self.assertGreater(minimum_angle, 20.0, component_name)

    def test_mesh_density_presets_increase_element_count(self):
        element_counts = []
        for density in ("Coarse", "Medium", "Fine"):
            payload = build_payload(
                GeometryInputs(mesh_density=density),
                self.loads,
                ViewInputs(),
                mode="model",
            )
            element_counts.append(payload["metadata"]["shellElements"])
            self.assertEqual(payload["metadata"]["meshDensity"], density)

        self.assertEqual(element_counts, sorted(element_counts))
        self.assertEqual(len(element_counts), len(set(element_counts)))

    def test_distributed_loads_preserve_resultants(self):
        analysis = self.payload["analysis"]
        nodes = analysis["nodes"]
        nodal_loads = dict(analysis["loads"])

        force = [0.0, 0.0, 0.0]
        moment = [0.0, 0.0, 0.0]
        for node_index, vector in nodal_loads.items():
            x, y, z = nodes[node_index]
            fx, fy, fz = vector[:3]
            force[0] += fx
            force[1] += fy
            force[2] += fz
            moment[0] += y * fz - z * fy
            moment[1] += z * fx - x * fz
            moment[2] += x * fy - y * fx

        expected_force = [
            self.loads.shear_x * 1_000,
            self.loads.shear_y * 1_000,
            -self.loads.axial_compression * 1_000,
        ]
        expected_moment = [
            self.loads.moment_x * 1_000_000
            - GeometryInputs().tube_height * self.loads.shear_y * 1_000,
            self.loads.moment_y * 1_000_000
            + GeometryInputs().tube_height * self.loads.shear_x * 1_000,
            self.loads.torsion_z * 1_000_000,
        ]

        for actual, expected in zip(force, expected_force):
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-6))
        for actual, expected in zip(moment, expected_moment):
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-4))

    def test_client_load_basis_reconstructs_the_initial_nodal_loads(self):
        analysis = self.payload["analysis"]
        magnitudes = {
            "axial_compression": self.loads.axial_compression,
            "shear_x": self.loads.shear_x,
            "shear_y": self.loads.shear_y,
            "moment_x": self.loads.moment_x,
            "moment_y": self.loads.moment_y,
            "torsion_z": self.loads.torsion_z,
        }
        reconstructed = {}
        for name, magnitude in magnitudes.items():
            for node_index, vector in analysis["loadBasis"][name]:
                combined = reconstructed.setdefault(node_index, [0.0] * 6)
                for index, value in enumerate(vector):
                    combined[index] += magnitude * value

        expected = dict(analysis["loads"])
        self.assertEqual(reconstructed.keys(), expected.keys())
        for node_index, vector in reconstructed.items():
            for actual, target in zip(vector, expected[node_index]):
                self.assertTrue(math.isclose(actual, target, rel_tol=1e-10, abs_tol=1e-6))

    def test_tube_and_stiffeners_share_the_analysis_mesh(self):
        geometry = self.payload["geometry"]
        analysis = self.payload["analysis"]

        self.assertEqual(len(analysis["elements"]), len(analysis["elementThicknesses"]))
        self.assertGreater(len(geometry["tube"]["elements"]), 0)
        self.assertGreater(len(geometry["stiffeners"]["elements"]), 0)
        self.assertTrue(
            set(geometry["plate"]["nodeIndices"]) & set(geometry["tube"]["nodeIndices"])
        )
        self.assertTrue(
            set(geometry["plate"]["nodeIndices"]) & set(geometry["stiffeners"]["nodeIndices"])
        )
        for name, expected_thickness in (
            ("plate", GeometryInputs().plate_thickness),
            ("tube", GeometryInputs().tube_thickness),
            ("stiffeners", GeometryInputs().stiffener_thickness),
        ):
            component = geometry[name]
            for element, element_index in zip(component["elements"], component["elementIndices"]):
                self.assertEqual(element, analysis["elements"][element_index])
                self.assertEqual(expected_thickness, analysis["elementThicknesses"][element_index])


if __name__ == "__main__":
    unittest.main()
