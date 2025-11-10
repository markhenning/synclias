from flask import Blueprint
from flask import url_for, jsonify
from flask_login import login_required

opnsense = Blueprint("opnsense", __name__, template_folder="templates")

@opnsense.route('/test', methods=['POST'])
@login_required
def test():
    from .tasks import bg_test_router
    task = bg_test_router.delay()
    return jsonify({}), 202, {'Location': url_for('opnsense.test_status', task_id=task.id)}

@opnsense.route('/test/status/<task_id>', methods=['GET'])
@login_required
def test_status(task_id):
    from .tasks import bg_test_router
    task = bg_test_router.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            "dbquery" : 'Pending',
            "ip_connectivity"  : 'Pending',
            "login" : 'Pending',
            "alias_add_remove" : 'Pending',
            "reconfigure" : 'Pending',
            "message" : 'Pending',
            'status': 'Pending...',
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            "dbquery" : task.info.get('dbquery'),
            "ip_connectivity"  : task.info.get('ip_connectivity'),
            "login" : task.info.get('login'),
            "alias_add_remove" : task.info.get('alias_add_remove'),
            "reconfigure" : task.info.get('reconfigure'),
            "message" : task.info.get('message'),
            'status': task.info.get('status'),
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            "dbquery" : task.info.get('dbquery'),
            "ip_connectivity"  : task.info.get('ip_connectivity'),
            "login" : task.info.get('login'),
            "alias_add_remove" : task.info.get('alias_add_remove'),
            "reconfigure" : task.info.get('reconfigure'),
            "message" : task.info.get('message'),
            'status': task.info.get('status'),
            ##'status': task.info.get('status')
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)