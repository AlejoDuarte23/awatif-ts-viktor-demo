import viktor as vkt

from .inputs import read_inputs
from .model import build_payload
from .parametrization import Parametrization
from .webview import render_webview


class Controller(vkt.Controller):
    label = "Awatif base plate"
    parametrization = Parametrization(width=34)

    @vkt.WebView(
        "Base plate analysis",
        duration_guess=7,
        update_label="Reload geometry",
        description="Edit loads, calculate, and explore shell results directly in the WebView.",
    )
    def results_view(self, params, **kwargs) -> vkt.WebResult:
        del kwargs
        try:
            geometry, loads, view = read_inputs(params)
            payload = build_payload(geometry, loads, view, mode="results")
        except ValueError as exc:
            raise vkt.UserError(str(exc)) from exc
        return vkt.WebResult(html=render_webview(payload))
