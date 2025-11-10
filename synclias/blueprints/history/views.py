from flask import Blueprint
from flask import request
from flask import flash, redirect, render_template, url_for, abort, jsonify
import pickle
from flask_login import login_required

## App specific
from flask import current_app
from synclias import db
from sqlalchemy import select
from synclias.models import Result


history = Blueprint("history", __name__, template_folder="templates")

@history.route("/", methods=['GET'])
@login_required
def page():
    ## Parameter sanity checking
    if request.args.get('log_id') == "undefined":
        log_id = 0
    else:
        log_id = request.args.get('log_id', 0, type=int)
    hide_zero = request.args.get('hide_zero', 0, type=int)
    
    current_app.logger.info(f"Called history log id: {log_id}")
    
    ## Find what they asked for
    if log_id == 0:
        result_entry = db.session.query(Result).order_by(Result.id.desc()).first()
    else:
        result_entry = db.session.scalars(select(Result).where(Result.id == log_id)).first()

        ##Prevent an issue where "hide_zero" is toggled on, whilst a 0 change log is shown, bump to first log with changes
        if result_entry is not None and result_entry.changes == 0 and hide_zero == 1:
            result_entry = db.session.query(Result).where(Result.changes != 0).order_by(Result.id.desc()).first()
    
    ## If there's no logs, or we've filtered them out (no changes), report no logs
    if result_entry is None:
        current_app.logger.info("History - called, but no logs to display")
        return render_template("/no_logs.html", hide_zero=hide_zero, no_logs=True)

    ## Set log_id, it may not not be what originally asked for
    log_id = result_entry.id

    ## Load the object for the required log from the DB
    result_data = pickle.loads(result_entry.result_pickle) # type: ignore

    ## Stats to fill out the dropdown, make query, run query
    if hide_zero == 0:
        log_column_query = select(Result.id, Result.timestamp,Result.changes).order_by(Result.id.desc())
    else:
        log_column_query = select(Result.id, Result.timestamp,Result.changes).where(Result.changes != 0).order_by(Result.id.desc())
    
    log_list = db.session.execute(log_column_query).all()

    ## Final sanity check, I think this is redundant after checks above, will test before removing
    if len(log_list) == 0:
        no_logs = True
        return render_template("/no_logs.html", log_id=log_id,hide_zero=hide_zero, no_logs=True)
    else:
        no_logs = False

    return render_template("/history.html", result_data=result_data, log_list=log_list, log_id=log_id, hide_zero=hide_zero, no_logs=no_logs)