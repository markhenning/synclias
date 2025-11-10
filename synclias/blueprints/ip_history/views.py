from flask import Blueprint, render_template
from flask_login import login_required

## App specific
from synclias import db
from sqlalchemy import select
from synclias.models import IPRecord


ip_history = Blueprint("ip_history", __name__, template_folder="templates")

## Super basic page, added for debugging really, will add sorting some day
@ip_history.route("/", methods=['GET'])
@login_required
def page():

    ip_history = db.session.scalars(select(IPRecord).order_by(IPRecord.fqdn)).all()

    return render_template("/ip_history.html", ip_history=ip_history)