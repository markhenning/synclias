from flask_restx import Namespace, Resource, fields
from flask import current_app

from synclias.models import Nameserver
from synclias.extensions import ma
from synclias import db

from sqlalchemy import select

api = Namespace('nameserver', description='nameserver related operations')

nameserver_model = api.model('Nameserver', {
    'id' : fields.Integer(description='nameserver id'),
    'hostname' : fields.String(description='nameserver hostname'),
    'port' : fields.Integer(description='management port, technitium only'),
    'https' : fields.Boolean(description='use https, technitium only'),
    'verifytls' : fields.Boolean(description='verify https cert, technitium'),
    'token' : fields.String(description='api token, technitium only'),
    'type' : fields.String(description='nameserver type: standard_ns or technitium'),
})

class NameserverSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Nameserver
        load_instance = True
        transient = True 

nameserver_schema = NameserverSchema()
nameservers_schema = NameserverSchema(many=True)

### Make a "NameserverList" Schema if we had more

@api.route('/')
class nameserver_api(Resource):
    @api.doc('list nameservers')
    @api.marshal_with(nameserver_model)
    def get(self):
        return nameservers_schema.dump(db.session.query(Nameserver).all()), 200
    
    @api.doc('create_nameserver')
    @api.expect(nameserver_model)
    @api.response(400,"")
    #@api.marshal_with(nameserver_model)  ## Yeah, I know, I built it and didn't use it
    def post(self):
        # current_app.logger.info(api.payload)
      
        ## Check if already present
        already_present = db.session.scalars(select(Nameserver).where(Nameserver.hostname == api.payload['hostname'])).all()
        current_app.logger.debug(already_present)
        if len(already_present) != 0:
            return {'status': 'error:', "message": "already present", "id" : already_present[0].id }, 409

        ## Sanity check comment
        if not api.payload['comment']:
            safe_comment = ""
        else:
            safe_comment = api.payload['comment']

        new_nameserver = Nameserver()

        for key in api.payload:
            if key in nameserver_model.keys():
                if key == 'id':
                    continue
                current_app.logger.debug(f"Looking at {key}")
                setattr(new_nameserver, key, api.payload[key])

        db.session.add(new_nameserver)
        current_app.logger.debug("Nameserver added via API")
        db.session.commit()
        return {'status': 'created', "id": new_nameserver.id }, 201

@api.route('/<int:id>')
@api.param('id', 'The Nameserver identifier')
@api.response(404, 'Nameserver not found')
class nameserver_item_api(Resource):
    @api.doc('delete nameserver')
    def delete(self,id):
        target = Nameserver.query.get_or_404(id)
        db.session.delete(target)
        db.session.commit()
        return {'status': 'ok:', "message": "deleted" }, 200

    @api.doc('update nameserver')
    def put(self,id):
        target = Nameserver.query.get_or_404(id)

        for key in api.payload:
            if key in nameserver_model.keys():
                if key == 'id':
                    continue
                current_app.logger.debug(f"Looking at {key}")
                setattr(target, key, api.payload[key])
        
        db.session.commit()
        return {'status': 'ok:', "message": "updated" }, 200

