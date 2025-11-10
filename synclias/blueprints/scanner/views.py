from flask import Blueprint
from flask import request
from flask import url_for, jsonify, render_template

from flask_login import login_required
from .forms import ScannerForm

from flask import current_app

scanner = Blueprint("scanner", __name__, template_folder="templates")

@scanner.route("/", methods=('GET', 'POST'))
@login_required
def page():
    form = ScannerForm()
    
    ## First call with a get
    if request.method == "GET":
        return render_template("/scanner.html", form=form)

    ## If they posted ok, popup with a modal for the scan 
    if form.validate_on_submit():
        return render_template("/scanner.html", form=form, start_scan=True)
    else:
        ## Re-send the initial core with error
        return render_template("/scanner.html", form=form)

@scanner.route("/scan/", methods=['POST'])
@login_required
def scan():

    req_json = request.get_json()

    if req_json['safe_scan']:
        current_app.logger.info(f"Safe")
        safe = True
    else:
        current_app.logger.info(f"Unsafe")
        safe = False
    
    from .tasks import scanner_bg
    task = scanner_bg.delay(req_json['site'],safe)
    return jsonify({}), 202, {'Location': url_for('scanner.taskstatus', task_id=task.id)}


@scanner.route('/scanner/scan/status/<task_id>', methods=['GET','POST'])
@login_required
def taskstatus(task_id):
    from synclias.blueprints.scanner.tasks import scanner_bg
    task = scanner_bg.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'sites': 0,
            'scan_rcode' : 202,
            'notes' : '',
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'sites': task.info.get('sites', 0),
            'scan_rcode': task.info.get('scan_rcode', 1),
            'notes' : task.info.get('notes', 2),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 7,
            'scan_rcode': task.info.get('scan_rcode', 1),
            'notes' : '',
            'status': str(task.info), 
        }
    return jsonify(response)