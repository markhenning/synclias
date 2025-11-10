from flask import Blueprint
from flask import jsonify
from flask_login import login_required

scheduler = Blueprint("scheduler", __name__, template_folder="templates")

## Endpoints for updating the background jobs for ASN and Autosync

@scheduler.route("/autosync")
@login_required
def create_update_autosync():
    from .tasks import create_update_autosync_task
    response = create_update_autosync_task()
    ## to fix, massively later
    return jsonify(response),200

@scheduler.route("/autoasndb")
@login_required
def create_update_asndb_download():
    from .tasks import create_update_autoasndb_task
    response = create_update_autoasndb_task()
    ## to fix, massively later
    return jsonify(response),200

@scheduler.route("/ip_history_scan")
@login_required
def create_update_ip_history_scan():
    from .tasks import create_update_ip_history_scan_task
    response = create_update_ip_history_scan_task()
    ## to fix, massively later
    return jsonify(response),200


