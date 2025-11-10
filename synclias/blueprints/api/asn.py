from flask_restx import Namespace, Resource, fields
from flask import current_app
from flask import jsonify
from flask_login import login_required
from synclias import db

from sqlalchemy import select
from synclias.models import ASN
from synclias.extensions import ma

api = Namespace('asn', description='asn related operations')

asn_model = api.model('ASN', {
    'id' :  fields.Integer(description='asn application db id'),
    'asn' :  fields.Integer(description='asn number'),
    'comment' :  fields.String(description='optional comments'),
})

class ASNSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ASN
        load_instance = True
        transient = True 

asn_schema = ASNSchema()
asns_schema = ASNSchema(many=True)

@api.route('/')
class asn_api(Resource):
    @api.doc('list asns')
    @api.marshal_with(asn_model)
    def get(self):
        return asns_schema.dump(db.session.query(ASN).all()), 200
    
    @api.doc('create_asn')
    @api.expect(asn_model)
    @api.response(400, 'Bad Request - check asn is int, comment is required (even if blank)')
    #@api.marshal_with(asn_model)  ## Yeah, I know, I built it and didn't use it
    def post(self):
        # current_app.logger.info(api.payload)
        if not isinstance(api.payload['asn'], int):
            api.abort(400)
            return {'status': 'error:', "message": "Bad input data (check asn is int)" }, 404
        
        ## Check if already present
        already_present = db.session.scalars(select(ASN).where(ASN.asn == api.payload['asn'])).all()
        current_app.logger.debug(already_present)
        if len(already_present) != 0:
            return {'status': 'error:', "message": "already present", "id" : already_present[0].id }, 409

        ## Sanity check comment
        if not api.payload['comment']:
            safe_comment = ""
        else:
            safe_comment = api.payload['comment']

        new_asn = ASN(
            asn=api.payload['asn'],
            comment = safe_comment,
        )

        db.session.add(new_asn)
        current_app.logger.debug("ASN added via API")
        db.session.commit()
        return {'status': 'created', "id": new_asn.id }, 201

@api.route('/<int:id>')
@api.param('id', 'The ASN identifier')
@api.response(404, 'ASN not found')
class asn_item_api(Resource):
    @api.doc('delete asn')
    def delete(self,id):
        target = ASN.query.get_or_404(id)
        db.session.delete(target)
        db.session.commit()
        return {'status': 'ok:', "message": "deleted" }, 200

    @api.doc('update asn')
    def put(self,id):
        target = ASN.query.get_or_404(id)

        for key in api.payload:
            if key in asn_model.keys():
                if key == 'id':
                    continue
                current_app.logger.debug(f"Looking at {key}")
                setattr(target, key, api.payload[key])
        
        db.session.commit()
        return {'status': 'ok:', "message": "updated" }, 200

