## Really, we should import these from the SQLAlchemy schema, but it's not automatically supported as far as I can see
## Will add as a todo
# from flask_restx import Namespace, fields

# api = Namespace('models', description='API models')

# router_model = api.model('Router', {
#     # 'name': fields.String,
#     # 'address': fields.String,
#     # 'date_updated': fields.DateTime(dt_format='rfc822'),
    
#     'id' : fields.Integer(description='router id'),
#     'hostname' : fields.String(description='router hostname'),
#     'https' : fields.Boolean(description='use https'),
#     'alias' : fields.String(description='firewall alias'),
#     'verifytls' : fields.Boolean(description='verify management connection tls cert'),
#     'apikey' : fields.String(description='router api key'),
#     'apisecret' : fields.String(description='router api secrret'),
    
# })

# nameserver_model = api.model('Nameserver', {
#     'id' : fields.Integer(description='nameserver id'),
#     'hostname' : fields.String(description='nameserver hostname'),
#     'port' : fields.Integer(description='management port, technitium only'),
#     'https' : fields.Boolean(description='use https, technitium only'),
#     'verifytls' : fields.Boolean(description='verify https cert, technitium'),
#     'token' : fields.String(description='api token, technitium only'),
#     'type' : fields.String(description='nameserver type: standard_ns or technitium'),
# })

# prefs_model = api.model('Prefs', {
#     'id' : fields.Integer(description='always 1'),
#     'autosync' : fields.Boolean(description='enable/disable auto sync'),
#     'sync_every' : fields.Integer(description='autosync every X minutes'),
#     'autoasndb' : fields.Boolean(description='enable/disable auto asn db download'),
#     'asndb_every' : fields.Integer(description='asn db download schedule, every X days'),
#     'purgedns' : fields.Boolean(description='enable/disable purge before query, technitium only'),
#     'user_agent' : fields.String(description='custom user agent for scanner'),
# })

# site_model = api.model('Site', {
#     'id' : fields.Integer(description='site id'),
#     'url': fields.String(description='site url'),
#     'url_group' : fields.String(description='site tld'),
#     'crawl' : fields.Boolean(description='enable/disable site crawl on sync'),
#     'override_safety' : fields.Boolean(description='ignore safety keyworks when removing danger urls'), 
# })

# safetykeyword_model = api.model('SafetyKeyword', {
#     'id' : fields.Integer(description='safetykeywor id'),
#     'keyword' :  fields.String(description='safety keyword'),
# })






        

