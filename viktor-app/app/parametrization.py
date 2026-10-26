import viktor as vkt

from .inputs import (
    advanced_inputs_visible,
    bolt_circle_output,
    clear_edge_output,
    hole_diameter_output,
    plate_diameter_output,
    relative_inputs_visible,
    stiffener_base_output,
    stiffener_count_visible,
    stiffener_height_output,
)


class Parametrization(vkt.Parametrization):
    intro = vkt.Section("Awatif model", initially_expanded=True)
    intro.copy = vkt.Text("""# Parametric tubular base plate

Define the connection from a few design-intent dimensions. Relative mode derives
the plate, anchors, and stiffeners when the tube size changes. Advanced mode keeps
direct control of every absolute dimension.
""")

    design = vkt.Section("Design method", initially_expanded=True)
    design.input_method = vkt.OptionField(
        "Input method",
        options=["Relative", "Advanced absolute"],
        default="Relative",
        variant="radio-inline",
        description="Relative mode keeps connected dimensions coordinated; Advanced absolute exposes direct dimensions.",
    )

    tube = vkt.Section("Tube")
    tube.outside_diameter = vkt.NumberField(
        "Outside diameter",
        default=200.0,
        min=50.0,
        suffix="mm",
        description="Outside diameter of the tubular column.",
        flex=50,
    )
    tube.height = vkt.NumberField(
        "Height",
        default=300.0,
        min=100.0,
        suffix="mm",
        flex=50,
    )
    tube.thickness = vkt.NumberField(
        "Wall thickness",
        default=8.0,
        min=2.0,
        suffix="mm",
        flex=50,
    )
    plate = vkt.Section("Plate layout")
    plate.projection = vkt.NumberField(
        "Projection beyond tube",
        default=120.0,
        min=20.0,
        suffix="mm",
        description="Radial distance from the tube face to the plate edge.",
        flex=50,
        visible=relative_inputs_visible,
    )
    plate.diameter = vkt.NumberField(
        "Plate diameter",
        default=440.0,
        min=100.0,
        suffix="mm",
        flex=50,
        visible=advanced_inputs_visible,
    )
    plate.thickness = vkt.NumberField(
        "Plate thickness", default=20.0, min=4.0, suffix="mm", flex=50
    )

    anchors = vkt.Section("Anchors")
    anchors.count = vkt.NumberField("Number of bolts", default=4, min=3, max=20, step=1, flex=50)
    anchors.bolt_diameter = vkt.NumberField(
        "Nominal bolt diameter",
        default=20.0,
        min=8.0,
        suffix="mm",
        flex=50,
        description="Used for the displayed bolt shank and for deriving the relative-mode hole diameter.",
    )
    anchors.hole_clearance = vkt.NumberField(
        "Hole clearance",
        default=2.0,
        min=0.0,
        suffix="mm",
        description="Added to the nominal bolt diameter to obtain the analysis hole diameter.",
        flex=50,
        visible=relative_inputs_visible,
    )
    anchors.hole_diameter = vkt.NumberField(
        "Hole diameter",
        default=22.0,
        min=8.0,
        suffix="mm",
        flex=50,
        visible=advanced_inputs_visible,
    )
    anchors.edge_distance = vkt.NumberField(
        "Bolt center edge distance",
        default=50.0,
        min=15.0,
        suffix="mm",
        description="Distance from the bolt centerline to the plate edge.",
        flex=50,
    )

    stiffeners = vkt.Section("Stiffeners")
    stiffeners.match_anchor_count = vkt.BooleanField(
        "Match the number of anchors",
        default=True,
        description="Keeps one stiffener between each adjacent pair of anchors.",
        visible=relative_inputs_visible,
    )
    stiffeners.count = vkt.NumberField(
        "Number of stiffeners",
        default=7,
        min=3,
        max=16,
        step=1,
        flex=50,
        visible=stiffener_count_visible,
    )
    stiffeners.height_ratio = vkt.NumberField(
        "Height / tube height",
        default=50.0,
        min=10.0,
        max=90.0,
        step=1.0,
        suffix="%",
        flex=50,
        visible=relative_inputs_visible,
    )
    stiffeners.base_ratio = vkt.NumberField(
        "Base / plate projection",
        default=91.67,
        min=20.0,
        max=95.0,
        step=0.5,
        suffix="%",
        flex=50,
        visible=relative_inputs_visible,
    )
    stiffeners.height = vkt.NumberField(
        "Height",
        default=150.0,
        min=20.0,
        suffix="mm",
        flex=50,
        visible=advanced_inputs_visible,
    )
    stiffeners.base = vkt.NumberField(
        "Base length",
        default=110.0,
        min=20.0,
        suffix="mm",
        flex=50,
        visible=advanced_inputs_visible,
    )
    stiffeners.thickness = vkt.NumberField("Thickness", default=10.0, min=2.0, suffix="mm", flex=50)

    derived = vkt.Section("Derived geometry", initially_expanded=True)
    derived.plate_diameter = vkt.OutputField("Plate diameter", value=plate_diameter_output)
    derived.hole_diameter = vkt.OutputField("Hole diameter", value=hole_diameter_output)
    derived.bolt_circle = vkt.OutputField("Bolt-circle diameter", value=bolt_circle_output)
    derived.clear_edge = vkt.OutputField("Clear edge distance", value=clear_edge_output)
    derived.stiffener_height = vkt.OutputField("Stiffener height", value=stiffener_height_output)
    derived.stiffener_base = vkt.OutputField("Stiffener base", value=stiffener_base_output)

    material = vkt.Section("Steel")
    material.elasticity = vkt.NumberField(
        "Young's modulus",
        default=200_000.0,
        min=1_000.0,
        suffix="MPa",
        flex=50,
    )
    material.poisson_ratio = vkt.NumberField(
        "Poisson ratio",
        default=0.30,
        min=0.01,
        max=0.49,
        step=0.01,
        flex=50,
    )
    material.line_break = vkt.LineBreak()
    material.yield_strength = vkt.NumberField(
        "Yield strength",
        default=280.0,
        min=1.0,
        suffix="MPa",
        description="Sets the top of the Von Mises color scale; the solver remains linear-elastic.",
        flex=50,
    )

    mesh = vkt.Section("Analysis mesh")
    mesh.density = vkt.OptionField(
        "Mesh density",
        options=["Coarse", "Medium", "Fine"],
        default="Medium",
        variant="radio-inline",
        description="Coarse is fastest, Medium is balanced, and Fine adds local detail but may take more than a minute to solve.",
    )
    mesh.show_mesh = vkt.BooleanField("Display mesh", default=False)
