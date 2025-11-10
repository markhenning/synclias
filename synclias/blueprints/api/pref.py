from flask_restx import Namespace, Resource, fields

from synclias.models import Prefs
from synclias.extensions import ma

api = Namespace('prefs', description='preferences')

prefs_model = api.model('Prefs', {
    'id' : fields.Integer(description='always 1'),
    'autosync' : fields.Boolean(description='enable/disable auto sync'),
    'sync_every' : fields.Integer(description='autosync every X minutes'),
    'autoasndb' : fields.Boolean(description='enable/disable auto asn db download'),
    'asndb_every' : fields.Integer(description='asn db download schedule, every X days'),
    'purgedns' : fields.Boolean(description='enable/disable purge before query, technitium only'),
    'user_agent' : fields.String(description='custom user agent for scanner'),
})

class PrefsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Prefs
        load_instance = True
        transient = True 

prefs_schema = PrefsSchema()

@api.route('/')
class prefs_api(Resource):
    @api.doc('get_prefs')
    @api.marshal_with(prefs_model)
    def get(self):
        return db.session.query(Prefs).first(), 200

