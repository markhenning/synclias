from synclias import create_app
from synclias.models import Site, Prefs, Router, SafetyKeyword, Nameserver, ASN
import os
import json
from synclias.models import db
from sqlalchemy import select

# /asn[GET]
def test_asn_page_with_fixture(test_client,init_database,log_in_default_user):
    ## Test Home page with a logged in user
    response = test_client.get('/asn/',follow_redirects=True)
    assert response.status_code == 200
    assert b'ASN Lookup' in response.data
    assert b'VPN Routed ASNs' in response.data

# /asn[POST]
def test_asn_add_with_fixture(test_client,init_database,log_in_default_user):
    response = test_client.post('/asn/',data={'asn': 12345678, 'comment' : ""},follow_redirects=True)
    assert b'value="12345678"' in response.data
    assert response.status_code == 200

# synclias/blueprints/asndb/views.py:@asndb.route("/asn/asndb_stats", methods=["GET"])
def test_db_stats_with_fixture(test_client,init_database,log_in_default_user):
    ## Test db_stats returns a json object with the right fields, NOT that it returns the file is there
    response = test_client.get('/asn/stats')
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['ASNDB_FILE']['exists'] == True or data['ASNDB_FILE']['exists'] == False
    assert data['ASNDB_NAMES_FILE']['exists'] == True or data['ASNDB_NAMES_FILE']['exists'] == False
    assert data['ASNDB_NAMES_FILE']['exists'] == True or data['ASNDB_NAMES_FILE']['exists'] == False

### THIS NEEDS TO CAUSE UPDATE TO FAIL FOR API, Form validation prevents it on site though
# def test_asn_bad_add_with_fixture(test_client,init_database,log_in_default_user):
#     response = test_client.post('/asn',data={'asn': '1aa234', 'comment' : ""})
#     print(response.data)
#     assert response.status_code == 200
