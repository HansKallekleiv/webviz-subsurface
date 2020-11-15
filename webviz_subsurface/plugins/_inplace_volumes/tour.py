def tour(parent):
    return [
        {
            "id": parent.uuid("layout"),
            "content": ("Dashboard displaying in place volumetric results. "),
        },
        {
            "id": parent.uuid("graph"),
            "content": (
                "Chart showing results for the current selection. "
                "Different charts and options can be selected from the menu above."
            ),
        },
        {
            "id": parent.uuid("table"),
            "content": (
                "The table shows statistics for the current active selection. "
                "Rows can be filtered by searching, and sorted by "
                "clicking on a column header."
            ),
        },
        {
            "id": parent.uuid("response"),
            "content": "Select the volumetric calculation to display.",
        },
        {
            "id": parent.uuid("plot-type"),
            "content": (
                "Controls the type of the visualized chart. "
                "Per realization shows bars per realization, "
                "while the boxplot shows the range per sensitivity."
            ),
        },
        {
            "id": parent.uuid("group"),
            "content": ("Allows grouping of results on a given category."),
        },
        {
            "id": parent.uuid("filters"),
            "content": (
                "Filter on different combinations of e.g. zones, facies and regions "
                "(The options will vary dependent on what was included "
                "in the calculation.)"
            ),
        },
    ]
