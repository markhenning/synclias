from synclias import create_app
from synclias.models import Site, Prefs, Router, SafetyKeyword, Nameserver, ASN
import os
import json
from synclias.models import db
from sqlalchemy import select

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
        exact=False,
        )
    db.session.add(keyword)
    db.session.commit()
    confirmed_added = db.session.get(SafetyKeyword,keyword.id)
    #confirmed_added = SafetyKeyword.query.get(keyword.id)
    assert confirmed_added.keyword == 'asdfghjklasdfghjkl'
    response = test_client.post(f"/keyword/delete/{keyword.id}",follow_redirects=True)
    assert response.status_code == 200
    assert db.session.get(SafetyKeyword,confirmed_added.id) is None
