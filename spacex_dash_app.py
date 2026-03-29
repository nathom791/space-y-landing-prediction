# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
from typing import Any, cast

# Load data
df = pd.read_csv("dataset_part_3.csv")

# Create success column: if any LandingPad is 1, then success=1, else 0
landing_pad_cols = [col for col in df.columns if col.startswith("LandingPad_")]
df["success"] = df[landing_pad_cols].sum(axis=1).apply(lambda x: 1 if x > 0 else 0)

# Extract numeric bounds for slider (convert Series to float scalars)
payload_min: float = cast(float, float(df["PayloadMass"].min()))
payload_max: float = cast(float, float(df["PayloadMass"].max()))

# Extract launch site name from the one-hot encoded columns
site_cols = {
    "LaunchSite_CCAFS SLC 40": "CCAFS SLC 40",
    "LaunchSite_KSC LC 39A": "KSC LC 39A",
    "LaunchSite_VAFB SLC 4E": "VAFB SLC 4E",
}


def get_site(row):
    for col, name in site_cols.items():
        if row[col] == 1:
            return name
    return "Unknown"


df["LaunchSite"] = df.apply(get_site, axis=1)

# Initialize Dash app
app = Dash(__name__)

# Define layout
app.layout = html.Div(
    [
        html.H1(
            "SpaceX Launch Data Dashboard",
            style={"textAlign": "center", "marginBottom": 30},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Select Launch Site:"),
                        dcc.Dropdown(
                            id="site-dropdown",
                            options=[{"label": "ALL", "value": "ALL"}]
                            + [
                                {"label": site, "value": site}
                                for site in sorted(df["LaunchSite"].unique())
                            ],
                            value="ALL",
                            style={"width": "100%"},
                        ),
                    ],
                    style={
                        "width": "30%",
                        "display": "inline-block",
                        "marginRight": "5%",
                    },
                ),
                html.Div(
                    [
                        html.Label("Select Payload Mass Range (kg):"),
                        dcc.RangeSlider(
                            id="payload-slider",
                            min=payload_min,
                            max=payload_max,
                            value=[payload_min, payload_max],
                            marks={
                                int(payload_min): f"{int(payload_min)}",
                                int(payload_max): f"{int(payload_max)}",
                            },
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ],
                    style={"width": "65%", "display": "inline-block"},
                ),
            ],
            style={"marginBottom": 30, "padding": "20px", "border": "1px solid #ddd"},
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="pie-chart")],
                    style={
                        "width": "48%",
                        "display": "inline-block",
                        "marginRight": "2%",
                    },
                ),
                html.Div(
                    [dcc.Graph(id="scatter-plot")],
                    style={"width": "48%", "display": "inline-block"},
                ),
            ]
        ),
    ]
)


# Callback 1: Update pie chart based on dropdown selection
@app.callback(Output("pie-chart", "figure"), Input("site-dropdown", "value"))
def update_pie_chart(selected_site: str) -> go.Figure:
    if selected_site == "ALL":
        # Show successes per site
        success_by_site = df.groupby("LaunchSite")["success"].sum()
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=success_by_site.index.tolist(),  # type: ignore
                    values=success_by_site.values.tolist(),  # type: ignore
                    title="Successful Launches by Site",
                )
            ]
        )
    else:
        # Show success/failure distribution for selected site
        site_data = df[df["LaunchSite"] == selected_site]
        success_counts = site_data["success"].value_counts()  # type: ignore
        labels = [
            "Successful" if idx == 1 else "Failed" for idx in success_counts.index
        ]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=success_counts.values.tolist(),  # type: ignore
                    title=f"Launch Outcomes at {selected_site}",
                )
            ]
        )

    return fig


# Callback 2: Update scatter plot based on dropdown and slider selection
@app.callback(
    Output("scatter-plot", "figure"),
    [Input("site-dropdown", "value"), Input("payload-slider", "value")],
)
def update_scatter_plot(selected_site: str, payload_range: Any) -> go.Figure:
    # Filter data by site
    if selected_site == "ALL":
        filtered_df = df.copy()
    else:
        filtered_df = df[df["LaunchSite"] == selected_site]

    # Filter by payload range
    filtered_df = filtered_df[
        (filtered_df["PayloadMass"] >= payload_range[0])
        & (filtered_df["PayloadMass"] <= payload_range[1])
    ]

    # Create scatter plot
    fig = go.Figure()

    # Add successful launches
    successful = filtered_df[filtered_df["success"] == 1]
    fig.add_trace(
        go.Scatter(
            x=successful["PayloadMass"].tolist(),  # type: ignore
            y=successful["success"].tolist(),  # type: ignore
            mode="markers",
            name="Successful",
            marker=dict(size=8, color="green"),
        )
    )

    # Add failed launches
    failed = filtered_df[filtered_df["success"] == 0]
    fig.add_trace(
        go.Scatter(
            x=failed["PayloadMass"].tolist(),  # type: ignore
            y=failed["success"].tolist(),  # type: ignore
            mode="markers",
            name="Failed",
            marker=dict(size=8, color="red"),
        )
    )

    fig.update_layout(
        title=f"Payload Mass vs Launch Outcome ({selected_site})",
        xaxis_title="Payload Mass (kg)",
        yaxis_title="Launch Outcome",
        yaxis=dict(tickvals=[0, 1], ticktext=["Failed", "Successful"]),
        hovermode="closest",
    )

    return fig


if __name__ == "__main__":
    app.run(debug=False, port=8050, host="127.0.0.1")
