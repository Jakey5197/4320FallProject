from dash import html, dcc, callback
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from dateutil.relativedelta import *  # type: ignore
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values, color_seq
from queries.prs_query import prs_query as prq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time

"""
NOTE: VARIABLES TO CHANGE:

(5) CONTEXT OF GRAPH
(6) IDs of Dash components
(7) COLUMN_WITH_DATETIME
(8) COLUMN_WITH_DATETIME
(9) COLUMN_TO_SORT_BY
(10) Comments before callbacks
(11) QUERY_USED, QUERY_NAME, QUERY_INITIALS

NOTE: IMPORTING A VISUALIZATION INTO A PAGE
(1) Include the visualization file in the visualization folder for the respective page
(2) Import the visualization into the page_name.py file using "from .visualizations.visualization_file_name import gc_visualization_name"
(3) Add the card into a column in a row on the page

NOTE: ADDITIONAL DASH COMPONENTS FOR USER GRAPH CUSTOMIZATIONS

If you add Dash components (ie dbc.Input, dbc.RadioItems, dcc.DatePickerRange...) the ids, html_for, and targets should be in the
following format: f"component-identifier-{PAGE}-{VIZ_ID}"

NOTE: If you change or add a new query, you need to do "docker system prune -af" before building again

NOTE: If you use an alert or take code from a visualization that uses one, make sure to update returns accordingly in the NAME_OF_VISUALIZATION_graph

For more information, check out the new_vis_guidance.md
"""


# TODO: Remove unused imports and edit strings and variables in all CAPS
# TODO: Remove comments specific for the template

PAGE = "Group5"  # EDIT FOR CURRENT PAGE
VIZ_ID = "change_request_duration"  # UNIQUE IDENTIFIER FOR VIZUALIZATION

change_request_duration = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Change Request Duration",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """         The pourpose of this metric is to monitor if the change requests submitted
                                        are being delt with efficiently by ratioing the number of open change requests
                                        in a specified amount of time with the number of change requests that have been closed
                                        in that same amount of time. The number of closed change requests is divided by the
                                        number of open pull requests. Having change requests delt with in an efficient
                                        manner helps to decrease merge conflicts."""
                            ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",
                    placement="top",
                    is_open=False,
                ),
                dcc.Loading(
                    dcc.Graph(id=f"{PAGE}-{VIZ_ID}"),
                ),
                dbc.Form(
                    [
                        dbc.Row(
                            [
                                dbc.Label(
                                    "Date Interval:",
                                    html_for=f"date-radio-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    [
                                        dbc.RadioItems(
                                            id=f"date-radio-{PAGE}-{VIZ_ID}",
                                            options=[
                                                {
                                                    "label": "Trend",
                                                    "value": "D",
                                                },  # TREND IF LINE, DAY IF NOT
                                                # {"label": "Week","value": "W",}, UNCOMMENT IF APPLICABLE
                                                {"label": "Month", "value": "M"},
                                                {"label": "Year", "value": "Y"},
                                            ],
                                            value="M",
                                            inline=True,
                                        ),
                                    ]
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "About Graph",
                                        id=f"popover-target-{PAGE}-{VIZ_ID}",
                                        color="secondary",
                                        size="sm",
                                    ),
                                    width="auto",
                                    style={"paddingTop": ".5em"},
                                ),
                            ],
                            align="center",
                        ),
                    ]
                ),
            ]
        )
    ],
)


# callback for graph info popover
@callback(
    Output(f"popover-{PAGE}-{VIZ_ID}", "is_open"),
    [Input(f"popover-target-{PAGE}-{VIZ_ID}", "n_clicks")],
    [State(f"popover-{PAGE}-{VIZ_ID}", "is_open")],
)
def toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open


# callback for VIZ TITLE graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    # Output(f"check-alert-{PAGE}-{VIZ_ID}", "is_open"), USE WITH ADDITIONAL PARAMETERS
    # if additional output is added, change returns accordingly
    [
        Input("repo-choices", "data"),
        Input(f"date-radio-{PAGE}-{VIZ_ID}", "value"),
        # add additional inputs here
    ],
    background=True,
)
def change_request_duration_graph(repolist, interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=prq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=prq, repos=repolist)

    start = time.perf_counter()
    logging.warning(f"{VIZ_ID}- START")

    # test if there is data
    if df.empty:
        logging.warning(f"{VIZ_ID} - NO DATA AVAILABLE")
        return nodata_graph

    # function for all data pre processing, COULD HAVE ADDITIONAL INPUTS AND OUTPUTS
    df = process_data(df, interval)

    fig = create_figure(df, interval)

    logging.warning(f"{VIZ_ID} - END - {time.perf_counter() - start}")
    return fig


def process_data(df: pd.DataFrame, interval):
    # Convert to datetime objects rather than strings
    df["created"] = pd.to_datetime(df["created"], utc=True)
    df["closed"] = pd.to_datetime(df["closed"], utc=True)

    # Order values chronologically by created date
    df = df.sort_values(by="created", axis=0, ascending=True)

    # Group by repo_id and calculate the number of open and closed requests
    df["time_to_close"] = (df["closed"] - df["created"]).dt.days

    return df


def create_figure(df: pd.DataFrame, interval):
    # Create a line graph with plotly
    fig = go.Figure()

    # Add a trace for each repo
    fig.add_trace(go.Scatter(
        x=df["created"],
        y=df["time_to_close"],
        mode='lines',
        name='Duration of PRs'
    ))


    # Set the layout
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Change Request Duration (Days)",
        title=f"Change Request Duration over Time ({interval})",
        hovermode="x"
    )

    return fig

