from dash import Input, Output, callback


def varviz_callback(app, get_uuid, dframe):
    @app.callback(
        Output(get_uuid("main-varviz"), "children"),
        Input({"id": get_uuid("selections-varviz"), "selector": "x"}, "value"),
        Input({"id": get_uuid("selections-varviz"), "selector": "y"}, "value"),
    )
    def _update_varviz_scatter(x, y):
        print(x)
