from .model import (
    GeometryDesignInputs,
    GeometryInputs,
    LoadInputs,
    ViewInputs,
    derived_geometry_values,
    resolve_geometry_design,
)


def _as_int(value: float) -> int:
    return int(round(value))


def read_geometry_design(params) -> GeometryDesignInputs:
    design = params.design
    tube = params.tube
    plate = params.plate
    anchors = params.anchors
    stiffeners = params.stiffeners
    material = params.material
    mesh = params.mesh

    return GeometryDesignInputs(
        input_method=design.input_method,
        tube_diameter=tube.outside_diameter,
        tube_height=tube.height,
        tube_thickness=tube.thickness,
        plate_projection=plate.projection,
        plate_diameter=plate.diameter,
        plate_thickness=plate.thickness,
        bolt_count=_as_int(anchors.count),
        bolt_diameter=anchors.bolt_diameter,
        hole_clearance=anchors.hole_clearance,
        hole_diameter=anchors.hole_diameter,
        bolt_center_edge_distance=anchors.edge_distance,
        match_anchor_count=bool(stiffeners.match_anchor_count),
        stiffener_count=_as_int(stiffeners.count),
        stiffener_height_ratio=stiffeners.height_ratio,
        stiffener_base_ratio=stiffeners.base_ratio,
        stiffener_height=stiffeners.height,
        stiffener_base=stiffeners.base,
        stiffener_thickness=stiffeners.thickness,
        elasticity=material.elasticity,
        poisson_ratio=material.poisson_ratio,
        yield_strength=material.yield_strength,
        mesh_density=mesh.density,
    )


def read_inputs(params) -> tuple[GeometryInputs, LoadInputs, ViewInputs]:
    geometry = resolve_geometry_design(read_geometry_design(params))
    loads = LoadInputs()
    view = ViewInputs(
        show_mesh=bool(params.mesh.show_mesh),
    )
    return geometry, loads, view


def relative_inputs_visible(params, **kwargs) -> bool:
    del kwargs
    return params.design.input_method == "Relative"


def advanced_inputs_visible(params, **kwargs) -> bool:
    del kwargs
    return params.design.input_method == "Advanced absolute"


def stiffener_count_visible(params, **kwargs) -> bool:
    del kwargs
    return advanced_inputs_visible(params) or not bool(params.stiffeners.match_anchor_count)


def _derived_output(params, name: str) -> str:
    try:
        geometry = resolve_geometry_design(read_geometry_design(params))
        value = derived_geometry_values(geometry)[name]
    except (AttributeError, TypeError, ValueError):
        return "Check inputs"
    return f"{value:,.1f} mm"


def plate_diameter_output(params, **kwargs) -> str:
    del kwargs
    return _derived_output(params, "plate_diameter")


def hole_diameter_output(params, **kwargs) -> str:
    del kwargs
    return _derived_output(params, "hole_diameter")


def bolt_circle_output(params, **kwargs) -> str:
    del kwargs
    return _derived_output(params, "bolt_circle_diameter")


def clear_edge_output(params, **kwargs) -> str:
    del kwargs
    return _derived_output(params, "clear_edge_distance")


def stiffener_height_output(params, **kwargs) -> str:
    del kwargs
    return _derived_output(params, "stiffener_height")


def stiffener_base_output(params, **kwargs) -> str:
    del kwargs
    return _derived_output(params, "stiffener_base")
