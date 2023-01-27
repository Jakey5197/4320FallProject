"""
    README -- Organization of Callback Functions

    In an effort to compartmentalize our development where possible, all callbacks directly relating
    to pages in our application are in their own files.

    For instance, this file contains the layout logic for the index page of our app-
    this page serves all other paths by providing the searchbar, page routing faculties,
    and data storage objects that the other pages in our app use.

    Having laid out the HTML-like organization of this page, we write the callbacks for this page in
    the neighbor 'app_callbacks.py' file.
"""
from db_manager.augur_manager import AugurManager
import dash
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import sys
import logging
import plotly.io as plt_io
from celery import Celery
from dash import CeleryManager
import worker_settings
import os

logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=logging.DEBUG)

"""CREATE CELERY TASK QUEUE AND MANAGER"""
celery_app = Celery(
    __name__,
    broker=worker_settings.REDIS_URL,
    backend=worker_settings.REDIS_URL,
)

celery_app.conf.update(task_time_limit=84600, task_acks_late=True, task_track_started=True)

celery_manager = CeleryManager(celery_app=celery_app)


"""CREATE DATABASE ACCESS OBJECT AND CACHE SEARCH OPTIONS"""
augur = AugurManager()

# make sure that parameters for Augur connection have been supplied.
client_secret = os.getenv("AUGUR_CLIENT_SECRET", "")
app_id = os.getenv("AUGUR_APP_ID", "")
session_endpoint = os.getenv("AUGUR_SESSION_GENERATE_ENDPOINT", "")
groups_endpoint = os.getenv("AUGUR_USER_GROUPS_ENDPOINT", "")

if not all([client_secret, app_id, session_endpoint, groups_endpoint]):
    logging.critical("ERROR: Client Augur credentials incomplete; can't start.")
    sys.exit(1)
else:
    augur.set_client_secret(client_secret)
    augur.set_app_id(app_id)
    augur.set_session_generate_endpoint(session_endpoint)
    augur.set_user_groups_endpoint(groups_endpoint)

# connect to database
engine = augur.get_engine()
if engine is None:
    logging.critical("Could not get engine; check config or try later")
    sys.exit(1)

# grab list of projects and orgs from Augur database.
augur.multiselect_startup()


"""IMPORT AFTER GLOBAL VARIABLES SET"""
import pages.index.index_callbacks as index_callbacks


"""SET STYLING FOR APPLICATION"""
load_figure_template(["sandstone", "minty", "slate"])

# stylesheet with the .dbc class, this is a complement to the dash bootstrap templates, credit AnnMarieW
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

# making custom plotly template with custom colors on top of the slate design template
plt_io.templates["custom_dark"] = plt_io.templates["slate"]
plt_io.templates["custom_dark"]["layout"]["colorway"] = [
    "#B5B682",  # sage
    "#c0bc5d",  # olive green
    "#6C8975",  # xanadu
    "#485B4E",  # feldgrau (dark green)
    "#3c582d",  # hunter green
    "#376D39",
]  # dartmouth green
plt_io.templates.default = "custom_dark"


"""CREATE APPLICATION"""
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.SLATE, dbc_css, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    background_callback_manager=celery_manager,
)

# expose the application object's server variable so that the wsgi server can use it.
server = app.server

# layout of the app stored in the app_layout file, must be imported after the app is initiated
from pages.index.index_layout import layout

app.layout = layout

if os.getenv("8KNOT_DEBUG", ""):
    app.enable_dev_tools(dev_tools_ui=True, dev_tools_hot_reload=False)

if __name__ == "__main__":
    print(
        "We've deprecated the Flask/Dash debug webserver.\
         Please use gunicorn to run application or docker/podman compose."
    )
