from synclias import create_app
from synclias.models import Site, Prefs, Router, SafetyKeyword, Nameserver, ASN
import os
import json
from synclias.models import db
from sqlalchemy import select



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