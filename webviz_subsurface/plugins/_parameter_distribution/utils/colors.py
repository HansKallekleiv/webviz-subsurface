from typing import Tuple
import plotly.express as px
import plotly.graph_objs as go

EQUINOR_COLORS = [
    "#243746",
    "#eb0036",
    "#919ba2",
    "#7d0023",
    "#66737d",
    "#4c9ba1",
    "#a44c65",
    "#80b7bc",
    "#ff1243",
    "#be8091",
    "#b2d4d7",
    "#ff597b",
    "#bdc3c7",
    "#d8b2bd",
    "#ffe7d6",
    "#d5eaf4",
    "#ff88a1",
]


def color_figure(colorscales, height=None):

    equinor_color_trace = go.Bar(
        customdata=list(range(len(EQUINOR_COLORS[:11]))),
        marker=dict(color=EQUINOR_COLORS[:11]),
        orientation="h",
        type="bar",
        y=["Equinor"] * len(EQUINOR_COLORS[:11]),
        x=[1] * len(EQUINOR_COLORS[:11]),
    )

    color_fig = px.colors.diverging.swatches()
    color_fig.add_trace(equinor_color_trace).update_traces(
        hovertemplate="%{marker.color}<extra></extra>"
    ).update_layout(
        title=None,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height if height is not None else 40 * len(colorscales),
        autosize=True,
        yaxis_showticklabels=False,
    )

    color_fig["data"] = [
        trace
        for trace in color_fig["data"]
        if trace["y"][0] in colorscales + ["Equinor"]
    ]
    return color_fig


def hex_to_rgb(hex_string: str, opacity: float = 1) -> str:
    """Converts a hex color to rgb"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    rgb.append(opacity)
    return f"rgba{tuple(rgb)}"


def rgb_to_hex(color):
    color = color.strip("rgb()")
    color = color.split(",")
    return "#%02x%02x%02x" % (int(color[0]), int(color[1]), int(color[2]))


def find_intermediate_color(
    lowcolor: str, highcolor: str, intermed: float, colortype: str = "tuple"
) -> str:
    """
    Returns the color at a given distance between two colors
    This function takes two color tuples, where each element is between 0
    and 1, along with a value 0 < intermed < 1 and returns a color that is
    intermed-percent from lowcolor to highcolor. If colortype is set to 'rgb',
    the function will automatically convert the rgb type to a tuple, find the
    intermediate color and return it as an rgb color.
    """

    if colortype == "rgba":
        # convert to tuple color, eg. (1, 0.45, 0.7)
        lowcolor = unlabel_rgba(lowcolor)
        highcolor = unlabel_rgba(highcolor)

    diff_0 = float(highcolor[0] - lowcolor[0])
    diff_1 = float(highcolor[1] - lowcolor[1])
    diff_2 = float(highcolor[2] - lowcolor[2])
    diff_3 = float(highcolor[3] - lowcolor[3])

    inter_med_tuple = (
        lowcolor[0] + intermed * diff_0,
        lowcolor[1] + intermed * diff_1,
        lowcolor[2] + intermed * diff_2,
        lowcolor[3] + intermed * diff_3,
    )

    if colortype == "rgba":
        # back to an rgba string, e.g. rgba(30, 20, 10)
        inter_med_rgba = label_rgba(inter_med_tuple)
        return inter_med_rgba

    return inter_med_tuple


def label_rgba(colors: str) -> str:
    """
    Takes tuple (a, b, c, d) and returns an rgba color 'rgba(a, b, c, d)'
    """
    return "rgba(%s, %s, %s, %s)" % (colors[0], colors[1], colors[2], colors[3])


def unlabel_rgba(colors: str) -> Tuple[float, float, float, float]:
    """
    Takes rgba color(s) 'rgba(a, b, c, d)' and returns tuple(s) (a, b, c, d)
    This function takes either an 'rgba(a, b, c, d)' color or a list of
    such colors and returns the color tuples in tuple(s) (a, b, c, d)
    """
    str_vals = ""
    for index, _col in enumerate(colors):
        try:
            float(colors[index])
            str_vals = str_vals + colors[index]
        except ValueError:
            if colors[index] == "," or colors[index] == ".":
                str_vals = str_vals + colors[index]

    str_vals = str_vals + ","
    numbers = []
    str_num = ""
    for char in str_vals:
        if char != ",":
            str_num = str_num + char
        else:
            numbers.append(float(str_num))
            str_num = ""
    return tuple(numbers)