from flask import Blueprint
from flask import jsonify, url_for

from flask_login import login_required

technitium = Blueprint("technitium", __name__, template_folder="templates")

# Basic feature reporting, to easily compare against other NS Plugins
@technitium.route("/features", methods=["GET"])
def get_features():
    features = {
        'cache_clear': True,
    }
    return jsonify(features)

# Trigger clear of single cache entry background task
@technitium.route("/clear_cache/<string:url>", methods=["GET"])
@login_required
def clear_cache_entry(url):
    from .tasks import clear_cache_entry
    task = clear_cache_entry.delay(url)
    return task.id

## Kick off basic tests, return task ID of that test for ajax to poll
@technitium.route('/test/<int:id>', methods=['POST'])
@login_required
def test_technitium(id):
    from .tasks import test_nameserver
    task = test_nameserver.delay(id)
    return jsonify({}), 202, {'Location': url_for('technitium.test_technitium_status', task_id=task.id)}

## Status of task created above
@technitium.route('/test/status/<task_id>', methods=['GET'])
@login_required
def test_technitium_status(task_id):
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
            'status': 'Pending...',
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
            "query" : task.info.get('query'),
            "login" : task.info.get('login'),
            "cache_clear" : task.info.get('cache_clear'),
            "message" : task.info.get('message'),
            'status': str(task.info), 
        }
    return jsonify(response)