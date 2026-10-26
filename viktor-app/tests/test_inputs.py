import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace

APP_DIR = Path(__file__).parents[1] / "app"
PACKAGE_NAME = "base_plate_inputs_test_app"
package = ModuleType(PACKAGE_NAME)
package.__path__ = [str(APP_DIR)]
sys.modules[PACKAGE_NAME] = package


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


load_module(f"{PACKAGE_NAME}.model", APP_DIR / "model.py")
INPUTS = load_module(f"{PACKAGE_NAME}.inputs", APP_DIR / "inputs.py")


def make_params(input_method="Relative"):
    return SimpleNamespace(
        design=SimpleNamespace(input_method=input_method),
        tube=SimpleNamespace(
            outside_diameter=200.0,
            height=300.0,
            thickness=8.0,
        ),
        plate=SimpleNamespace(
            projection=120.0,
            diameter=440.0,
            thickness=20.0,
        ),
        anchors=SimpleNamespace(
            count=7,
            bolt_diameter=20.0,
            hole_clearance=2.0,
            hole_diameter=22.0,
            edge_distance=50.0,
        ),
        stiffeners=SimpleNamespace(
            match_anchor_count=True,
            count=7,
            height_ratio=50.0,
            base_ratio=91.67,
            height=150.0,
            base=110.0,
            thickness=10.0,
        ),
        material=SimpleNamespace(
            elasticity=200_000.0,
            poisson_ratio=0.30,
            yield_strength=280.0,
        ),
        mesh=SimpleNamespace(density="Medium", show_mesh=True),
    )


class TestInputs(unittest.TestCase):
    def test_relative_param_paths_resolve_the_geometry(self):
        geometry, loads, view = INPUTS.read_inputs(make_params())

        self.assertEqual(geometry.tube_radius, 100.0)
        self.assertEqual(geometry.plate_radius, 220.0)
        self.assertEqual(geometry.bolt_diameter, 22.0)
        self.assertEqual(loads.axial_compression, 20.0)
        self.assertTrue(view.show_mesh)
        self.assertEqual(view.result_component, "von_mises")

    def test_visibility_switches_between_input_methods(self):
        relative = make_params("Relative")
        advanced = make_params("Advanced absolute")

        self.assertTrue(INPUTS.relative_inputs_visible(relative))
        self.assertFalse(INPUTS.advanced_inputs_visible(relative))
        self.assertFalse(INPUTS.relative_inputs_visible(advanced))
        self.assertTrue(INPUTS.advanced_inputs_visible(advanced))
        self.assertTrue(INPUTS.stiffener_count_visible(advanced))

    def test_derived_outputs_include_units(self):
        params = make_params()
        self.assertEqual(INPUTS.plate_diameter_output(params), "440.0 mm")
        self.assertEqual(INPUTS.hole_diameter_output(params), "22.0 mm")
        self.assertEqual(INPUTS.bolt_circle_output(params), "340.0 mm")
        self.assertEqual(INPUTS.clear_edge_output(params), "39.0 mm")


if __name__ == "__main__":
    unittest.main()
