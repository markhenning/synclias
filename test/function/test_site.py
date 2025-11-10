from synclias import create_app
from synclias.models import Site, Prefs, Router, SafetyKeyword, Nameserver, ASN
import os
import json
from synclias.models import db
from sqlalchemy import select

def test_home_page_redirect_with_fixture(test_client,init_database):
    ## Ensure trying to access the site when not logged in
    # redirects to the auth manager
    response = test_client.get('/')
    assert response.status_code == 302
    assert b'/auth/login' in response.data
    assert b'Status' not in response.data

def test_home_page_with_fixture(test_client,init_database,log_in_default_user):
    ## Test Home page with a logged in user
    response = test_client.get('/')
    assert response.status_code == 200
    assert b'Status' in response.data

#synclias/blueprints/core/views.py:@core.route("/docs")
def test_docs_page_with_fixture(test_client,init_database,log_in_default_user):
    ## Test Home page with a logged in user
    response = test_client.get('/docs')
    assert response.status_code == 200
    assert b'Configuration' in response.data

#  /site" ["GET","POST"]
def test_site_page_with_fixture(test_client,init_database,log_in_default_user):
    ## Test Home page with a logged in user
    response = test_client.get('/site',follow_redirects=True)
    assert response.status_code == 200
    assert b'Site Group' in response.data
    assert b'Override Safety Keywords' in response.data
    assert b'Action' in response.data

# /site ["POST"] - Without data
def test_site_add_no_form_with_fixture(test_client,init_database,log_in_default_user):
    response = test_client.post('/site',follow_redirects=True)
    assert response.status_code == 400

# /site ["POST"]
def test_site_add_with_fixture(test_client,init_database,log_in_default_user):
    response = test_client.post('/site',data={'url': 'mail.google.com'},follow_redirects=True)
    assert response.status_code == 200
    assert b'Site Group' in response.data
    assert b'Override Safety Keywords' in response.data
    assert b'Action' in response.data
    assert b'mail.google.com' in response.data

# /asn[GET]
def test_asn_page_with_fixture(test_client,init_database,log_in_default_user):
    ## Test Home page with a logged in user
    response = test_client.get('/asn/',follow_redirects=True)
    print(response.data)
    assert response.status_code == 200
    assert b'ASNs are groups of networks that are managed' in response.data
    assert b'VPN Routed ASNs' in response.data

# /asn[POST]
def test_asn_add_with_fixture(test_client,init_database,log_in_default_user):
    response = test_client.post('/asn',data={'asn': 12345678, 'comment' : ""},follow_redirects=True)
    assert b'value="12345678"' in response.data
    assert response.status_code == 200

# /site ["POST"]

### THIS NEEDS TO CAUSE UPDATE TO FAIL FOR API, Form validation kills it on the site
# def test_asn_bad_add_with_fixture(test_client,init_database,log_in_default_user):
#     response = test_client.post('/asn',data={'asn': '1aa234', 'comment' : ""})
#     print(response.data)
#     assert response.status_code == 200

# /scanner GET
def test_scanner_page_with_fixture(test_client,init_database,log_in_default_user):
    ## Test Scanner page with a logged in user
    response = test_client.get('/scanner',follow_redirects=True)
    assert response.status_code == 200
    assert b'Link Scanner' in response.data

# /scanner post
def test_scanner_results_add_with_fixture(test_client,init_database,log_in_default_user):
    pass

# /settings GET
def test_settings_page_with_fixture(test_client,init_database,log_in_default_user):
    ## Test Settings page with a logged in user
    response = test_client.get('/settings')
    assert response.status_code == 200

# /settings POST
## Test settings change
def test_settings_update_with_fixture(test_client,init_database,log_in_default_user):
    response = test_client.post('/settings',data={'hostname': 'newrouter.address', 'apikey':"newapikey", 'apisecret': 'newapisecret','https': 1, 'verifytls': 1, 'alias': 'newVPN_Websites'},follow_redirects=True)
    router = db.session.query(Router).first()
    assert response.status_code == 200
    assert router.hostname == 'newrouter.address'
    assert router.apikey == 'newapikey'
    assert router.apisecret == 'newapisecret'
    assert router.https == 1
    assert router.verifytls == 1
    assert router.alias == 'newVPN_Websites'
    assert b'name="hostname" required size="32" type="text" value="newrouter.address">' in response.data

# /settings POST
## Test settings change, with unchecked forms
def test_settings_update_unchecked_boxes_with_fixture(test_client,init_database,log_in_default_user):
    response = test_client.post('/settings',data={'hostname': 'newerrouter.address', 'apikey':"newerapikey", 'apisecret': 'newerapisecret','https': [], 'verifytls': [], 'alias': 'newerVPN_Websites'},follow_redirects=True)
    router = db.session.query(Router).first()
    assert response.status_code == 200
    assert router.hostname == 'newerrouter.address'
    assert router.apikey == 'newerapikey'
    assert router.apisecret == 'newerapisecret'
    assert router.https == 0
    assert router.verifytls == 0
    assert router.alias == 'newerVPN_Websites'
    assert b'name="hostname" required size="32" type="text" value="newerrouter.address">' in response.data  

# //keyword/create/suggestionsPOST
## Test Import Suggested keywords
def test_import_suggested_keywords_with_fixture(test_client,init_database,log_in_default_user):
    response = test_client.post('/keyword/create/suggestions',follow_redirects=True)
    assert response.status_code == 200
    assert b'google' in response.data
    assert b'microsoft' in response.data
    assert b'apple' in response.data
    assert b'facebook' in response.data

def test_keyword_add_duplicate_fixture(test_client,init_database,log_in_default_user):
    response = test_client.post('/keyword/create/suggestions',follow_redirects=True)
    assert response.status_code == 200
    assert b'Already present: google' in response.data
    assert b'Already present: microsoft' in response.data

# /keyword/delete/<int:id>' ["POST"]
def test_keyword_delete_with_fixture(test_client,init_database,log_in_default_user):
    keyword = SafetyKeyword(
        keyword='asdfghjklasdfghjkl',
	exact=True,
        )
    db.session.add(keyword)
    db.session.commit()
    confirmed_added = db.session.get(SafetyKeyword,keyword.id)
    #confirmed_added = SafetyKeyword.query.get(keyword.id)
    assert confirmed_added.keyword == 'asdfghjklasdfghjkl'
    response = test_client.post(f"/keyword/delete/{keyword.id}",follow_redirects=True)
    assert response.status_code == 200
    assert db.session.get(SafetyKeyword,confirmed_added.id) is None


# synclias/blueprints/asndb/views.py:@asndb.route("/asn/asndb_stats", methods=["GET"])
def test_db_stats_with_fixture(test_client,init_database,log_in_default_user):
    ## Test db_stats returns a json object with the right fields, NOT that it returns the file is there
    response = test_client.get('/asn/stats')
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['ASNDB_FILE']['exists'] == True or data['ASNDB_FILE']['exists'] == False
    assert data['ASNDB_NAMES_FILE']['exists'] == True or data['ASNDB_NAMES_FILE']['exists'] == False
    assert data['ASNDB_NAMES_FILE']['exists'] == True or data['ASNDB_NAMES_FILE']['exists'] == False

# /keyword GET
def test_keyword_page_with_fixture(test_client,init_database,log_in_default_user):
    ## Test Home page with a logged in user
    response = test_client.get('/keyword',follow_redirects=True)
    assert response.status_code == 200
    assert b'Safety Keywords' in response.data
    assert b'Add Keyword' in response.data

# /keyword POST
def test_keyword_add_with_fixture(test_client,init_database,log_in_default_user):
    pass

#synclias/blueprints/technitium/views.py:@technitium.route("/technititum/features", methods=["GET"])   
def test_technitium_features_with(test_client,init_database,log_in_default_user):
    response = test_client.get('/technitium/features',follow_redirects=True)
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['cache_clear'] == True

# synclias/blueprints/standard_ns/views.py:@standard_ns.route("/standard_ns/features", methods=["GET"])
def test_standard_ns_features_with(test_client,init_database,log_in_default_user):
    response = test_client.get('/standard_ns/features',follow_redirects=True)
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['cache_clear'] == False

##/prefs/scanner_agent["POST"]
def test_set_user_agent_string_features_with(test_client,init_database,log_in_default_user):
    response = test_client.post('/prefs/scanner_agent', data = { 'user_agent' : "Test User Agent" })
    prefs = db.session.scalars(select(Prefs)).first()
    assert response.status_code == 302
    assert prefs.user_agent == "Test User Agent"

##/prefs/scanner_agent["POST"]
def test_set_user_agent_blank_features_with(test_client,init_database,log_in_default_user):
    prefs = db.session.scalars(select(Prefs)).first()
    prefs.user_agent = "Test User Agent"
    db.session.commit()
    response = test_client.post('/prefs/scanner_agent', data = { 'user_agent' : "" })
    prefs = db.session.scalars(select(Prefs)).first()
    assert response.status_code == 302
    assert prefs.user_agent == ""

##/nameserver/create/ [POST]
def test_create_nameserver_standard_features_with(test_client,init_database,log_in_default_user):
    response = test_client.post('/nameserver/create/', data = { 'hostname' : "test-ns45645", 'type' : 'standard_ns', 'port' : 0, 'token' :1, 'https': [], 'verifytls' : []},follow_redirects=True)
    assert response.status_code == 200
    assert b'test-ns45645' in response.data
    assert b'id="hostname" value="test-ns45645">' in response.data
    nameserver = db.session.scalars(select(Nameserver).filter(Nameserver.hostname=="test-ns45645")).first()
    assert nameserver.hostname == "test-ns45645"
    assert nameserver.type == 'standard_ns'

##/nameserver/update/ [POST]
def test_update_nameserver_standard_features_with(test_client,init_database,log_in_default_user):
    
    ## Add a nameserver to change
    new_nameserver = Nameserver(
        hostname = "test-pre-update",
        type = 'technitium',
        port = 53443,
        token = "old-token",
        https = 1, 
        verifytls = 1,
    )
    db.session.add(new_nameserver)
    db.session.commit()
    nameserver = db.session.scalars(select(Nameserver).filter(Nameserver.hostname=="test-pre-update")).first()
    assert nameserver.hostname == "test-pre-update"
    assert nameserver.type == 'technitium'

    ## Update with 'https' and 'verifytls' present'
    response = test_client.post(f"/nameserver/update/{nameserver.id}", data = { 'hostname' : "test-post-update", 'type' : 'technitium', 'port' : 444, 'token' : "new-token", 'https': 1, 'verifytls' : 1},follow_redirects=True)
    assert response.status_code == 200
    nameserver = db.session.scalars(select(Nameserver).filter(Nameserver.hostname=="test-post-update")).first()
    assert nameserver.port == 444
    assert nameserver.token == "new-token"

    ## Update without 'https' and 'verifytls' present'
    response = test_client.post(f"/nameserver/update/{nameserver.id}", data = { 'hostname' : "test-post-post-update", 'type' : 'technitium', 'port' : 555, 'token' : "newer-token"},follow_redirects=True)
    assert response.status_code == 200
    nameserver = db.session.scalars(select(Nameserver).filter(Nameserver.hostname=="test-post-post-update")).first()
    assert nameserver.port == 555
    assert nameserver.token == "newer-token"


    
        # hostname=request.form.get('hostname'), # type: ignore 
        # type = request.form.get('type'), # type: ignore  
        # https = True, # type: ignore 
        # port = safe_port, # type: ignore 
        # verifytls = True, # type: ignore 
        # token = request.form.get('token'), # type: ignore 

# synclias/blueprints/core/views.py:@core.route("/nameserver/update/<int:id>", methods=['POST'])
# synclias/blueprints/core/views.py:@core.route('/nameserver/delete/<int:id>', methods=["POST"])

# /url_find/", methods=['POST'])

#synclias/blueprints/core/views.py:@core.route("/site/crawl/<int:id>/<int:new_state>", methods=['PUT'])

#  synclias/blueprints/opnsense/views.py:@opnsense.route('/test_router/', methods=['POST'])
# synclias/blueprints/opnsense/views.py:@opnsense.route('/status/router_test/<task_id>', methods=['GET'])
# synclias/blueprints/scanner/views.py:@scanner.route("/url_find/", methods=['POST'])
# synclias/blueprints/scanner/views.py:@scanner.route("/scanner/<string:url>", methods=["GET","POST"])
# synclias/blueprints/scanner/views.py:@scanner.route('/status/scanner/<task_id>', methods=['GET','POST'])
# synclias/blueprints/auth/views.py:@auth.route('/auth/login', methods=['GET', 'POST'])
# synclias/blueprints/auth/views.py:@auth.route('/auth/change_password', methods=['GET', 'POST'])
# synclias/blueprints/auth/views.py:@auth.route('/auth/logout',methods=['GET'])

# synclias/blueprints/standard_ns/views.py:@standard_ns.route('/test_standard_ns/<int:id>', methods=['POST'])
# synclias/blueprints/standard_ns/views.py:@standard_ns.route('/status/standard_ns_test/<task_id>', methods=['GET'])

# synclias/blueprints/technitium/views.py:@technitium.route("/clear_cache/<string:url>", methods=["GET"])
# synclias/blueprints/technitium/views.py:@technitium.route('/test_technitium/<int:id>', methods=['POST'])
# synclias/blueprints/technitium/views.py:@technitium.route('/status/technitium_test/<task_id>', methods=['GET'])
# synclias/blueprints/syncer/views.py:@syncer.route('/sync', methods=['POST'])
# synclias/blueprints/syncer/views.py:@syncer.route('/status/syncer/<task_id>', methods=['GET'])

# synclias/blueprints/asndb/views.py:@asndb.route("/asn/find/", methods=['POST'])
# synclias/blueprints/asndb/views.py:@asndb.route('/asn/status/db_download/<task_id>', methods=['GET'])
# synclias/blueprints/asndb/views.py:@asndb.route("/asn/download_db", methods=["POST"])
# synclias/blueprints/asndb/views.py:# @asndb.route("/asn/lookup/asn/<string:ip>", methods=["GET"])
# synclias/blueprints/asndb/views.py:# @asndb.route("/asn/lookup/site/", methods=["POST"])
# synclias/blueprints/asndb/views.py:# @asndb.route("/asn/lookup/subnets/<string:asn>", methods=["GET"])
# synclias/blueprints/core/views.py:@core.route('/site/delete/<int:id>', methods=["POST"])

# synclias/blueprints/core/views.py:@core.route("/asn/create", methods=["POST"])
# synclias/blueprints/core/views.py:@core.route('/asn/delete/<int:id>', methods=["POST"])


# synclias/blueprints/core/views.py:@core.route('/keyword/create/suggestions', methods=["POST"])
# synclias/blueprints/core/views.py:@core.route("/settings", methods=('GET', 'POST'))

# synclias/blueprints/core/views.py:@core.route("/site/crawl/<int:id>/<int:new_state>", methods=['PUT'])
# synclias/blueprints/core/views.py:@core.route("/site/override/<int:id>/<int:new_state>", methods=['PUT'])
# synclias/blueprints/core/views.py:@core.route("/prefs/autosync/<int:new_state>", methods=['PUT'])
# synclias/blueprints/core/views.py:@core.route("/prefs/sync_every/<int:new_state>", methods=['PUT'])
# synclias/blueprints/core/views.py:@core.route("/prefs/autoasndb/<int:new_state>", methods=['PUT'])
# synclias/blueprints/core/views.py:@core.route("/prefs/asndb_every/<int:new_state>", methods=['PUT'])
# synclias/blueprints/core/views.py:@core.route("/prefs/purgedns/<int:new_state>", methods=['PUT'])
# synclias/blueprints/core/views.py:@core.route("/prefs/scanner_agent", methods=["POST"])
# synclias/blueprints/core/views.py:@core.route("/bulk_add_site/", methods=["POST"])
# synclias/blueprints/core/views.py:@core.route("/add_ns/", methods=["POST"])
# synclias/blueprints/scheduler/views.py:@scheduler.route("/schedule/autosync")
# synclias/blueprints/scheduler/views.py:@scheduler.route("/schedule/autoasndb")
