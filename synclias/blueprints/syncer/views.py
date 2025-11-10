from flask import Blueprint
from flask import url_for, abort, jsonify
from flask import session
from flask_login import login_required

syncer = Blueprint("syncer", __name__, template_folder="templates")

## Start sync, return task id for monitoring
@syncer.route('/sync', methods=['POST'])
@login_required
def sync():
    from .tasks import run_syncer
    task = run_syncer.delay()
    return jsonify({}), 202, {'Location': url_for('syncer.taskstatus', task_id=task.id)}

## Report current state of task, called by ajax request
@syncer.route('/sync/status/<task_id>', methods=['GET'])
@login_required
def taskstatus(task_id):
    from .tasks import run_syncer
    task = run_syncer.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 7,
            'subtask_current' : 0,
            'subtask_total' : 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'subtask_current' : task.info.get('subtask_current', 0),
            'subtask_total' : task.info.get('subtask_total',1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 7,
            'total': 7,
            'subtask_current' : 0,
            'subtask_total' : 1,
            'status': str(task.info),  # this is the exception raised
        }
        session['sync_task_id'] = "Blank"
    return jsonify(response)