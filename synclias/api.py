## This is commented out in app.py for now, work in progress until I can get Marshmallow/Pydantic to talk to SQL-Alchemy properly

from flask_restx import Api

from synclias.blueprints.api.asn import api as asn
from synclias.blueprints.api.keyword import api as keyword
from synclias.blueprints.api.nameserver import api as nameserver
from synclias.blueprints.api.opnsense import api as opnsense
from synclias.blueprints.api.pref import api as pref
from synclias.blueprints.api.site import api as site

api = Api(
    title='OPN_Alias',
    doc='/api/v1/doc',
    version='1.0',
    description='OPN_Alias',
    prefix='/api/v1',
)

api.add_namespace(asn, path='/asn')
api.add_namespace(keyword, path='/keyword')
api.add_namespace(nameserver, path='/nameserver')
api.add_namespace(opnsense, path='/opnsense')
api.add_namespace(pref, path='/pref')
api.add_namespace(site, path='/site')