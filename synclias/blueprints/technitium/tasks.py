## Current app state
from flask import current_app

## Utility imports
import requests
from requests import RequestException
import dns.resolver as resolver
import socket

## Celery
from synclias import create_celery_app
from synclias.models import Nameserver
from synclias import db
from sqlalchemy import select
celery = create_celery_app()

@celery.task
def clear_cache_entry(entry):
    ## Push a specified DNS entry out of cache
    ## current_app.logger.debug(f"Clearing {entry} from DNS cache")

    for nameserver in db.session.query(Nameserver).all():   
        
        if nameserver.https:
            proto = "https"
        else:
            proto = "http"
   
        conn_prefix = proto + "://" + nameserver.hostname + ":" + str(nameserver.port)
        api_call = conn_prefix + '/api/cache/delete?token=' + nameserver.token + '&domain=' + entry
        r = requests.get(api_call, verify=nameserver.verifytls)

## Helper function to update all of the "Pending" to "Skipped" properties in testing result set 
def update_resultset(resultset, from_text, to_text):
    for key in resultset.keys():
        if not key == 'message':
            if resultset[key] == from_text:
                resultset[key] = to_text
    
    return resultset

@celery.task(bind=True)
def test_nameserver(self, id):

    # Set up results, modify as we go
    results = {
        "dbquery" : 'Pending',
        "ip_connectivity"  : 'Pending',
        "query" : 'Pending',
        "login" : 'Pending',
        "cache_clear" : 'Pending',
        "message" : 'Pending'
    }

    # Flag process has started executing, no longer wating
    self.update_state(state='PROGRESS', meta=results)

    results = update_resultset(results, 'Pending', 'Not run')

    ## DB Entry test
    target = db.session.scalars(select(Nameserver).where(Nameserver.id == id)).one()
    current_app.logger.debug(f"Data given:{target}")
    if target:
        results['dbquery'] = 'Pass'
    else:
        results['db_entry'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = 'Nameserver id not found'

        self.update_state(state='FAILED', meta=results)
        return results
    self.update_state(state='PROGRESS', meta=results)

    if not target.port or not target.hostname:
        results['ip_connectivity'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = 'Hostname or port missing'
        self.update_state(state='FAILED', meta=results)
        return results

    
    # IP Socket Connectivity Test
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((target.hostname, target.port))
    except socket.error as error:
        results['ip_connectivity'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = error.strerror
        self.update_state(state='FAILED', meta=results)
        return results
    finally:
        sock.close()
    
    results['ip_connectivity'] = 'Pass' 
    self.update_state(state='PROGRESS', meta=results)
    
    from synclias.blueprints.syncer.tasks import resolve_ip_by_nameserver

    ## DNS Query check
    test_query = set()
    try:
        ns_ip = socket.gethostbyname(target.hostname)
        test_query = resolve_ip_by_nameserver(current_app.config['DNS_CHECK_DOMAIN'],nameserver=ns_ip)
    except socket.error as e:
        results['query'] = 'Fail'
        results['message'] = f"Error with {target.hostname} - {e.strerror}"
        self.update_state(state='FAILED', meta=results)
        return results

    ## If there's no resolved IPs, we've failed
    if test_query == set():
        results['query'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = f"Failed to resolve {current_app.config['DNS_CHECK_DOMAIN']}"
        self.update_state(state='FAILED', meta=results)
        return results

    results['query'] = 'Pass'
    self.update_state(state='PROGRESS', meta=results)

    ## Login check
    if not target.token:
        results['login'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = 'Token missing'
        return results

    ## URL Build
    if target.https:
        proto = "https"
    else:
        proto = "http"

    api_test_url = proto + '://' + target.hostname + ':' + str(target.port) + '/api/user/session/get?token=' + target.token

    login_failed = False
    try:
        r = requests.get(api_test_url, verify=target.verifytls)
        r.raise_for_status()

        reply = r.json()
        login_failed = False

    ## If we couldn't connect, try to be verbose about it.
    except requests.exceptions.ConnectionError as e:
        current_app.logger.debug(f'DNS API Login Check Error -  {e}')
        results['message'] = f'DNS API Login Check Error -  {e}'
        login_failed = True
    except requests.exceptions.HTTPError as e:
        current_app.logger.debug(f'DNS API Login Check Error -  {e}')
        results['message'] = f'DNS API Login Check Error -  {e}'
        login_failed = True
    except requests.exceptions.ReadTimeout as e:
        current_app.logger.debug(f'DNS API Login Check Error -  {e}')
        results['message'] = f'DNS API Login Check Error -  {e}'
        login_failed = True
    except RequestException as e:
        results['message'] = f'DNS API Unknown Error -  {e}'
        login_failed = True

    if not login_failed:
        if reply['status'] == 'ok':
            results['login'] = 'Pass'
        else:
            ## Connected, talked to Technitium, but it didn't like it for some reason
            login_failed = True
            results['message'] = reply['errorMessage']

    if login_failed == True:
        results['login'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        self.update_state(state='FAILED', meta=results)
        return results


    ## API Cache clear call
    ## We already looked up google, so try to kick it out of the cache
    api_call = proto + '://' + target.hostname + ':' + str(target.port) + '/api/cache/delete?token=' + target.token + '&domain=google.com' # type: ignore
    r = requests.get(api_call, verify=target.verifytls)

    api_cache_failed = False
    try:
        r = requests.get(api_test_url, verify=target.verifytls)
        r.raise_for_status()

        reply = r.json()
        api_cache_failed  = False

    except RequestException as e:
        current_app.logger.debug(f'DNS API Cache Clear Check Error -  {e}')
        api_cache_failed  = True
        results['message'] = reply[f" Cache Clear Check Error -  {e}"]

    if reply['status'] == 'ok':
        results['cache_clear'] = 'Pass'
    else:
        api_cache_failed  = True

    if api_cache_failed  == True:
        results['cache_clear'] = 'Fail'
        results['message'] = reply['errorMessage']
        self.update_state(state='FAILED', meta=results)
        return results  

    ## End of tests, signal the win
    results['message'] = 'All tests completed!'
    self.update_state(state='COMPLETED', meta=results)
    return results