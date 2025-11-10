import requests
from requests import RequestException
import socket
from flask import current_app
from synclias import db

from synclias.models import Router

from synclias import create_celery_app
celery = create_celery_app()

## Helper Functions
def make_auth(router):
    auth = (router.apikey,router.apisecret)
    return auth

def make_conn_prefix(router):
    if router.https:
        proto = "https"
    else:
        proto = "http"
    conn_prefix = proto + "://" + router.hostname 
    return conn_prefix

## Dealing with the alias...
def get_alias_json(alias):
    
    router = db.session.query(Router).first()
    if router is None:
        return {}
    current_app.logger.debug(f"Triggered - Get URL List")
    path = 'api/firewall/alias_util/list'
    auth = make_auth(router)
    conn_prefix = make_conn_prefix(router)
    url = conn_prefix + "/" + path + "/" + alias
    
    try:
        r = requests.get(url,auth=auth,verify=router.verifytls) # type: ignore
        if r.status_code == 200:
            return r.json()
        else:
            return {}
    except:
        return {}    

def get_alias_ips(alias_json):
    ips = set()
    if 'rows' in alias_json.keys():
        for row in alias_json['rows']:
            ips.add(row['ip'])
    else:
        current_app.logger.warning(f"WARNING: No IPs found in Alias JSON")
    return ips

## Router modification functions

def modify_alias(mode, alias, ip):
    router = db.session.query(Router).first()
    if router is None:
        return 500
    else:    
        url = make_conn_prefix(router) + "/api/firewall/alias_util/" + mode + "/" + alias
        post_data = { "address" : ip }

        r = requests.post(url,json=post_data, auth=make_auth(router), verify=router.verifytls) # type: ignore
        return r.status_code

def flush_states():
    router = db.session.query(Router).first()
    url = make_conn_prefix(router) + "/api/diagnostics/firewall/flush_states"
    #post_data = { "address" : ip }

    result = False
    try:
        r = requests.post(url, auth=make_auth(router), verify=router.verifytls) # type: ignore
        r.raise_for_status()
        
        r_json = r.json()
        if r_json['result'] == 'ok':
            result = True
    except requests.exceptions.HTTPError as e:
        current_app.logger.warning(f"HTTP error occurred: {e}")
        result = False
    except requests.exceptions.RequestException as e:
        current_app.logger.warning(f"Request error: {e}")
        result = False
        
    return result

def test_db_entry():
    ## Lookup test
    results = {
        'pass' : False,
        'message' : "",
    }

    target = db.session.query(Router).first()
    if target is None:
        results['pass'] = False
        results['message'] = 'Router DB entry not found'
    else:    
        results['pass'] = True

    return results

def test_connectivity():
    ## Test connectivity

    results = {
        'pass' : False,
        'message' : "",
    }

    target = db.session.query(Router).first()
    if target is None:
        results['message'] = "Error - Settings not found in database"
        return results

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if target.https:
        port = 443
    else:
        port = 80
    try:
        s.connect((target.hostname, port))
        results['pass'] = True
        results['message'] = ""
    except socket.error as error:
        results['pass'] = False
        results['message'] = error.strerror
        return results
    finally:
        s.close()

    return results

def test_api_secret_present():

    results = {
        'pass' : False,
        'message' : "",
    }

    target = db.session.query(Router).first()
    if target is None:
        results['pass'] = False
        results['message'] = 'Database entry error - Router'
        return results      

    if not target.apisecret or not target.apikey:
        results['pass'] = False
        results['message'] = 'Missing Key/Secret'
    else:
        results['pass'] = True
    return results

def test_reconfigure_aliases():

    results = {
        'pass' : False,
        'message' : "",
    }

    target = db.session.query(Router).first()
    if target is None:
        results['message'] = "Error - Settings not found in database"
        return results
    
    path = 'api/firewall/alias/reconfigure'
    url = make_conn_prefix(target) + "/" + path
    
    try: 
        r = requests.post(url, auth=make_auth(target),verify=target.verifytls)
        
        if r.status_code == 200:
            results['pass'] = True
        else: 
            results['pass'] = False
            results['message'] = "API Login Error"

    except RequestException as e:
            results['pass'] = False
            results['message'] = f"API Login unknown error {e}"

    return results

def reconfigure_aliases():
    target = db.session.query(Router).first()
    if target is None:
        return 500
    
    path = 'api/firewall/alias/reconfigure'
    url = make_conn_prefix(target) + "/" + path
    r = requests.post(url, auth=make_auth(target),verify=target.verifytls) 
    return r.status_code


def test_api_login():
    target = db.session.query(Router).first()

    results = {
        'pass' : False,
        'message' : "",
    }
       
    if target is None:
        results['message'] = "Error - Settings not found in database"
        return results

    api_url = make_conn_prefix(target) +  "/api/firewall/alias/get/"

    try:
        r = requests.get(api_url,auth=make_auth(target),verify=target.verifytls)
        r.raise_for_status()
        reply = r.json()

        found_ipv4 = False
        found_ipv6 = False

        ## This is due to the OPNsense API layout
        aliases = reply['alias']['aliases']['alias']

        for key in aliases.keys():
            if aliases[key]['name'] == target.alias:
                current_app.logger.debug("Found ipv4 alias")
                found_ipv4 = True
            if aliases[key]['name'] == target.alias_ipv6:
                current_app.logger.debug("Found ipv6 alias")
                found_ipv6 = True
        
        if not target.ipv6: # type: ignore
            if found_ipv4:
                current_app.logger.debug("Signalling IPv4 Alias OK")
                results['pass'] = True
                results['message'] = "Alias found"
                return results
            else:
                current_app.logger.debug("Signalling IPv4 Alias fail")
                results['pass'] = False
                results['message'] = "Alias not found"
                return results
        else:
            if found_ipv6 and found_ipv4:
                current_app.logger.debug("Signalling IPv4 and 6 OK")
                results['pass'] = True
                results['message'] = "Aliases for IPv4 and 6 found"
                
            else:
                results['pass'] = False
                if found_ipv4 and not found_ipv6:
                    results['message'] = "Found IPv4 Alias, but not IPv6"
                elif not found_ipv4 and found_ipv6:
                    results['message'] = "Found IPv6 Alias, but not IPv4"
            return results
        
          
    except requests.RequestException as e:
        current_app.logger.debug(f'Test API Error - {e}')
        results['message'] = f"Connection error - {e}"
        return results
    

def test_add_remove_ip():

    results = {
        'pass' : False,
        'message' : "",
    }

    target = db.session.query(Router).first()
    if target is None:
        results['message'] = "Error - Settings not found in database"
        return results

    ## Alias Add_Remove
    alias_content = get_alias_json(target.alias)
    alias_ips = get_alias_ips(alias_content)

    if len(alias_ips) != 0:
        # Remove and re-add the last element of the array, if there is one
        current_app.logger.debug(f"Alias IPs before work: {alias_ips}")
        test_ip= (list(alias_ips))[-1]
        current_app.logger.debug(f"Removing/re-adding: {test_ip}")
        delete_results = modify_alias("delete",target.alias,test_ip)
        add_results = modify_alias("add",target.alias,test_ip)
    
    else:
        ## Random RFC1918 address, this is fine, because it's empty and we're deleting before reconfigure
        test_ip=current_app.config['ADD_REMOVE_TEST_IP']
        add_results = modify_alias("add",target.alias,test_ip)
        delete_results = modify_alias("delete",target.alias,test_ip)

    if delete_results == 200 and add_results == 200:
        results['pass'] = True
    else:
        results['pass'] = False
        results['message'] = "Error, delete gave HTTP {delete_results}, add {add_results}"
    
    return results

## Helper function for mass updating text in testing results below
def update_resultset(resultset, from_text, to_text):
    for key in resultset.keys():
        ## Safety - don't update "message", I need that
        if not key == 'message':
            if resultset[key] == from_text:
                resultset[key] = to_text

    return resultset

def preflight_test():
    results = test_router()

    # db_results = test_db_entry()
    # if not db_results['pass']:
    #     return "Preflight Fail - DB Entry"
    # conn_results = test_connectivity()
    # if not conn_results['pass']:
    #     return "Preflight Fail - Connectivity to Router"
    # api_secret_results = test_api_secret_present()
    # if not api_secret_results['pass']:
    #     return "Preflight Fail - Credentials missing"
    # add_remove_results = test_add_remove_ip()
    # if not add_remove_results['pass']:
    #     return "Preflight Fail - Router comms, check settings"

    current_app.logger.info(results)

    reply = {
        'proceed' : True,
        'message' : results.pop('message')
    }

    for result in results.keys():
        ## Yes, this is messy
        if results[result] != 'Pass':
            reply['proceed'] = False

    return reply

@celery.task(bind=True)
def bg_test_router(self):
     return test_router(self=self)


def test_router(self=None):
    ## Self is None when called direct (e.g preflight, or "self" when called from celery task)
    ## This way I can use the same code twice
    results = {
        "dbquery" : 'Pending',
        "ip_connectivity"  : 'Pending',
        "login" : 'Pending',
        "alias_add_remove" : 'Pending',
        "reconfigure" : 'Pending',
        "message" : 'Pending'
    }

    ## Task is now on queue, update vars
    if self is not None:
        self.update_state(state='PROGRESS', meta=results)
    
    results = update_resultset(results, 'Pending', 'Not run')

    ## DB Router Lookup test
    db_results = test_db_entry()
    
    if db_results['pass']:
        results['dbquery'] = 'Pass'
    else:
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = db_results['message']
        if self is not None:
            self.update_state(state='FAILED', meta=results)
        return results
 

    # Tested it, now ok to lead it in:
    target = db.session.query(Router).first()

    conn_results = test_connectivity()

    if conn_results['pass']:
        results['ip_connectivity'] = 'Pass'
    else:
        results['ip_connectivity'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = conn_results['message']
        if self is not None:
            self.update_state(state='FAILED', meta=results)
        return results
    
    if self is not None:
        self.update_state(state='PROGRESS', meta=results)

    ## Validate data present
    if not target.apisecret or not target.apikey: # type: ignore
        results['login'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = 'Missing Key/Secret'
        if self is not None:
            self.update_state(state='FAILED', meta=results)
        return results

    api_secret_results = test_api_secret_present()
    if api_secret_results['pass']:
        results['login'] = 'Pass'
    else:
        results['login'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = api_secret_results['message']
        return results   

    login_results = test_api_login()
    if login_results['pass']:
        results['login'] = 'Pass'
    else:
        results['login'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = login_results['message']
        return results
    
    if self is not None:
        self.update_state(state='PROGRESS', meta=results)

    ## Alias
    add_remove_results = test_add_remove_ip()
    if add_remove_results['pass']:
        results['alias_add_remove'] = 'Pass'
    else:
        results['alias_add_remove'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = add_remove_results['message']
        return results
    
    if self is not None:
        self.update_state(state='PROGRESS', meta=results)

    ## Reconfigure Alias

    reconfigure_results = test_reconfigure_aliases()
    if reconfigure_results['pass']:
        results['reconfigure'] = 'Pass'
    else:
        results['alias_add_remove'] = 'Fail'
        results = update_resultset(results, 'Not run', 'Skipped')
        results['message'] = reconfigure_results['message']
        return results


    results['message'] = 'All Tests Completed!'

    if self is not None:
        self.update_state(state='PROGRESS', meta=results)

    return results

    


