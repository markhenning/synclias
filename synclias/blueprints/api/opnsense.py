from flask_restx import Namespace, Resource, fields

from synclias.models import Router
from synclias.extensions import ma
from synclias import db

from sqlalchemy import select

api = Namespace('opnsense', description='opnsense related operations')

router_model = api.model('Router', {
    
    'id' : fields.Integer(description='router id'),
    'hostname' : fields.String(description='router hostname'),
    'https' : fields.Boolean(description='use https'),
    'alias' : fields.String(description='firewall alias'),
    'verifytls' : fields.Boolean(description='verify management connection tls cert'),
    'apikey' : fields.String(description='router api key'),
    'apisecret' : fields.String(description='router api secrret'),
    
})

## Marshmallow work, to be completed
# class RouterSchema(ma.SQLAlchemyAutoSchema):
#     class Meta:
#         model = Router
#         load_instance = True
#         transient = True 

# router_schema = RouterSchema()

### Make a "RouterList" Schema if we had more

@api.route('/')
class router_c(Resource):
    @api.doc('get_router')
    @api.marshal_with(router_model)
    def get(self):
        #current_app.logger.info(router_schema.dump_fields)
        #current_app.logger.debug(db.session.query(Router).first())
        #return router_schema.dump(db.session.query(Router).first()), 200
        return db.session.query(Router).first(), 200

    # @api.doc('update_opnsense')
    # # @api.marshal_with(router_class)
    # def update(self):
    #     current_app.logger.info(db.session.query(Router).first())
    #     return router_schema.dump(db.session.query(Router).first()), 200




        # current_app.logger.info("Hello router function in api")
        
        # target = db.session.query(Router).first()
        # current_app.logger.info(target)
        # return router_schema.jsonify(target)
        # '''Fetch a opnsense given its identifier'''
        # for opnsense in opnsenses:
        #     if opnsense['id'] == id:
        #         return opnsense
        # api.abort(404)
# def router_api_list():    
#     all_notes = Router.query.all()
#     return jsonify(router_schema.dump(all_notes))

# opnsenses = [
#     {'id': 'rout1', 'name': 'router1'},
# ]

# @api.route('/')
# class opnsenseList(Resource):
#     @api.doc('list_opnsenses')
#     @api.marshal_list_with(opnsense)
#     def get(self):
#         '''List all opnsenses'''
#         return opnsenses

# @api.route('/<id>')
# @api.param('id', 'The opnsense identifier')
# @api.response(404, 'opnsense not found')
# class opnsense(Resource):
#     @api.doc('get_opnsense')
#     @api.marshal_with(opnsense)
#     def get(self, id):
#         current_app.logger.info("Hello from opnsense")
#         current_app.logger.info(db.session.query(Router).first())
#         '''Fetch a opnsense given its identifier'''
#         for opnsense in opnsenses:
#             if opnsense['id'] == id:
#                 return opnsense
#         api.abort(404)