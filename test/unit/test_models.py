from synclias.models import Site, SafetyKeyword, ASN, Router, Nameserver, Prefs


def test_new_site():
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the email, hashed_password, and role fields are defined correctly
    """
    site = Site(url='mail.google.com', url_group='google.com', crawl=1, override_safety=1)
    site_json = site.to_json()
    assert site.url == 'mail.google.com'
    assert site.url_group == 'google.com'
    assert site.crawl== 1
    assert site.override_safety==1
    assert site_json['url'] == 'mail.google.com'
    assert site_json['url_group'] == 'google.com'
    assert site_json['crawl'] == 1
    assert site_json['override_safety'] == 1


def test_new_safetykeyword():
    safety_keyword = SafetyKeyword(keyword='google',exact=True)
    safety_keyword_json = safety_keyword.to_json()
    assert safety_keyword.keyword == 'google' 
    assert safety_keyword_json['keyword'] == 'google'

def test_new_asn():
    asn = ASN(asn=1234, comment="comment1234")
    asn_json = asn.to_json()
    assert asn.asn == 1234
    assert asn.comment == "comment1234"
    assert asn_json['asn'] == 1234
    assert asn_json['comment'] == 'comment1234'

def test_new_router():
    router = Router(hostname="router.test",https=1,alias="VPN_Websites",verifytls=1,apikey="apikey",apisecret="apisecret")
    router_json = router.to_json()
    assert router.hostname == "router.test"
    assert router.https == 1
    assert router.alias =="VPN_Websites"
    assert router.verifytls == 1
    assert router.apikey =="apikey"
    assert router.apisecret == "apisecret"
    assert router_json['hostname'] == "router.test"
    assert router_json['https'] == 1
    assert router_json['alias'] == "VPN_Websites"
    assert router_json['verifytls'] == 1
    assert router_json['apikey'] == "apikey"
    assert router_json['apisecret'] == "apisecret"

def test_new_nameserver():
    nameserver = Nameserver(hostname="ns1.test",port=53443,type="technitium",https=1,verifytls=1,token="token")
    nameserver_json = nameserver.to_json()
    assert nameserver.hostname=="ns1.test"
    assert nameserver.port==53443
    assert nameserver.type=="technitium"
    assert nameserver.https==1
    assert nameserver.verifytls==1
    assert nameserver.token=="token"
    assert nameserver_json['hostname'] == "ns1.test"
    assert nameserver_json['port'] == 53443
    assert nameserver_json['type'] == "technitium"
    assert nameserver_json['https'] == 1
    assert nameserver_json['verifytls'] == 1
    assert nameserver_json['token'] == "token" 


def test_new_prefs():
    prefs = Prefs(autosync=1,sync_every=6,autoasndb=1,asndb_every=7,purgedns=1,user_agent="Mozilla")
    prefs_json = prefs.to_json()
    assert prefs.autosync==1
    assert prefs.sync_every==6
    assert prefs.autoasndb==1
    assert prefs.asndb_every==7
    assert prefs.purgedns==1
    assert prefs.user_agent=="Mozilla"
    assert prefs_json['autosync'] == 1
    assert prefs_json['sync_every'] == 6
    assert prefs_json['autoasndb'] == 1
    assert prefs_json['asndb_every'] == 7
    assert prefs_json['purgedns'] == 1
    assert prefs_json['user_agent'] == "Mozilla"
    
