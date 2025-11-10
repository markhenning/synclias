from flask import Blueprint
from flask import jsonify, url_for
from flask_login import login_required

standard_ns = Blueprint("standard_ns", __name__, template_folder="templates")

@standard_ns.route("/features", methods=["GET"])
def get_features():
    features = {
        'cache_clear': False,
    }
    return jsonify(features)

@standard_ns.route('/test/<int:id>', methods=['POST'])
@login_required
def test_standard_ns(id):
    from .tasks import test_nameserver
    task = test_nameserver.delay(id)
    return jsonify({}), 202, {'Location': url_for('standard_ns.test_standard_ns_status', task_id=task.id)}

@standard_ns.route('/test/status/<task_id>', methods=['GET'])
@login_required
def test_standard_ns_status(task_id):
    from .tasks import test_nameserver
    task = test_nameserver.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            "dbquery" : 'Pending',
            "ip_connectivity"  : 'Pending',
            "query" : 'Pending',
            "login" : 'Pending',
            "cache_clear" : 'Pending',
            "message" : 'Pending',
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            "dbquery" : task.info.get('dbquery'),
            "ip_connectivity"  : task.info.get('ip_connectivity'),
            "query" : task.info.get('query'),
            "login" : task.info.get('login'),
            "cache_clear" : task.info.get('cache_clear'),
            "message" : task.info.get('message'),
            'status': task.info.get('status')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            "dbquery" : task.info.get('dbquery'),
            "ip_connectivity"  : task.info.get('ip_connectivity'),
            "query" : task.info.get('query'),
            "login" : task.info.get('login'),
            "cache_clear" : task.info.get('cache_clear'),
            "message" : task.info.get('message'),
            ##'status': task.info.get('status')
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)