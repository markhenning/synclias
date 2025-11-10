## Current app state
from flask import current_app

## Utility imports
import requests
import socket

## Celery
from synclias import create_celery_app
from synclias import db
from sqlalchemy import select
from synclias.models import Nameserver
celery = create_celery_app()

## Helper function to update results set
def update_resultset(resultset, from_text, to_text):
    for key in resultset.keys():
        if not key == 'message':
            if resultset[key] == from_text:
                resultset[key] = to_text
    
    return resultset

## "Run test" Background/worker task, much smaller relative to Technitium
@celery.task(bind=True)
def test_nameserver(self, id):

    results = {
        "dbquery" : 'Pending',
        "ip_connectivity"  : 'N/A - Standard Nameserver',
        "query" : 'Pending',
        "login" : 'N/A - Standard Nameserver',
        "cache_clear" : 'N/A - Standard Nameserver',
        "message" : 'Pending'
    }

    ## We're off the waiting queue and executing
    results = update_resultset(results, 'Pending', 'Not run')
    self.update_state(state='PROGRESS', meta=results)

    #### DB Entry tests

    target = db.session.scalars(select(Nameserver).where(Nameserver.id == id)).one()
    current_app.logger.debug(f"Data given:{target}")
    current_app.logger.debug(f"That's {target.hostname}")
    if target:
        results['dbquery'] = 'Pass'
    else:
        results['db_entry'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = 'Nameserver id not found'

        self.update_state(state='FAILED', meta=results)
        return results
    self.update_state(state='PROGRESS', meta=results)

    if not target.hostname:
        results['ip_connectivity'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = 'Hostname or missing'
        self.update_state(state='FAILED', meta=results)
        return results

    
    ### DNS resolve check
 
    from synclias.blueprints.syncer.tasks import resolve_ip_by_nameserver

    test_query = set()
    try:
        ns_ip = socket.gethostbyname(target.hostname)
        test_query = resolve_ip_by_nameserver(current_app.config['DNS_CHECK_DOMAIN'],nameserver=ns_ip)
    except socket.error as e:
        results['ip_connectivity'] = 'Fail'
        results['message'] = f"Error with {target.hostname} - {e.strerror}"
        results = update_resultset(results, 'Not run', 'Skipped')
        self.update_state(state='FAILED', meta=results)
        return results

    if test_query == set():
        results['query'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = f"Failed to resolve {current_app.config['DNS_CHECK_DOMAIN']}"
        self.update_state(state='FAILED', meta=results)
        return results

    results['query'] = 'Pass'
    self.update_state(state='PROGRESS', meta=results)

    results['message'] = 'All tests completed!'
    self.update_state(state='COMPLETED', meta=results)
    return results