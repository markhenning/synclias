from flask_restx import Namespace, Resource, fields
from flask import current_app

from synclias.models import SafetyKeyword
from synclias.extensions import ma
from synclias import db

from sqlalchemy import select


api = Namespace('keyword', description='keyword related operations')

safetykeyword_model = api.model('SafetyKeyword', {
    'id' : fields.Integer(description='safetykeyword id'),
    'keyword' :  fields.String(description='safety keyword'),
})

class SafetyKeywordSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SafetyKeyword
        load_instance = True
        transient = True 

safetykeyword_schema = SafetyKeywordSchema()
@api.route('/')
class keyword_api(Resource):
    @api.doc('list keywords')
    @api.marshal_with(safetykeyword_model)
    def get(self):
        return safetykeyword_schema.dump(db.session.query(SafetyKeyword).all()), 200
    
    @api.doc('create_keyword')
    @api.expect(safetykeyword_model)
    @api.response(400, "")
    #@api.marshal_with(safetykeyword_model)  ## Yeah, I know, I built it and didn't use it
    def post(self):
        # current_app.logger.info(api.payload)
      
        ## Check if already present
        already_present = db.session.scalars(select(SafetyKeyword).where(SafetyKeyword.keyword == api.payload['keyword'])).all()
        current_app.logger.debug(already_present)
        if len(already_present) != 0:
            return {'status': 'error:', "message": "already present", "id" : already_present[0].id }, 409

        ## Sanity check comment
        if not api.payload['comment']:
            safe_comment = ""
        else:
            safe_comment = api.payload['comment']

        new_keyword = SafetyKeyword(
            keyword=api.payload['keyword'],
            comment = safe_comment,
        )

        db.session.add(new_keyword)
        current_app.logger.debug("SafetyKeyword added via API")
        db.session.commit()
        return {'status': 'created', "id": new_keyword.id }, 201

@api.route('/<int:id>')
@api.param('id', 'The SafetyKeyword identifier')
@api.response(404, 'SafetyKeyword not found')
class keyword_item_api(Resource):
    @api.doc('delete keyword')
    def delete(self,id):
        target = SafetyKeyword.query.get_or_404(id)
        db.session.delete(target)
        db.session.commit()
        return {'status': 'ok:', "message": "deleted" }, 200

    @api.doc('update keyword')
    def put(self,id):
        target = SafetyKeyword.query.get_or_404(id)

        for key in api.payload:
            if key in safetykeyword_model.keys():
                if key == 'id':
                    continue
                current_app.logger.debug(f"Looking at {key}")
                setattr(target, key, api.payload[key])
        
        db.session.commit()
        return {'status': 'ok:', "message": "updated" }, 200