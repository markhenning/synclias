

from flask_restx import Namespace, Resource, fields
from flask import current_app
from synclias import db

from sqlalchemy import select
from synclias.models import Site
from synclias.extensions import ma

api = Namespace('sites', description='sites to route')

site_model = api.model('Site', {
    'id' : fields.Integer(description='site id'),
    'url': fields.String(description='site url'),
    'url_group' : fields.String(description='site tld'),
    'crawl' : fields.Boolean(description='enable/disable site crawl on sync'),
    'override_safety' : fields.Boolean(description='ignore safety keyworks when removing danger urls'), 
})

class SiteSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Site
        load_instance = True
        transient = True 

site_schema = SiteSchema()
sites_schema = SiteSchema(many=True)

@api.route('/')
class site_api(Resource):
    @api.doc('list sites')
    @api.marshal_with(site_model)
    def get(self):
        return sites_schema.dump(db.session.query(Site).all()), 200
    
    @api.doc('create_site')
    @api.expect(site_model)
    @api.response(400, "")
    #@api.marshal_with(site_model)  ## Yeah, I know, I built it and didn't use it
    def post(self):
        # current_app.logger.info(api.payload)
      
        ## Check if already present
        already_present = db.session.scalars(select(Site).where(Site.url == api.payload['url'])).all()

        if len(already_present) != 0:
            return {'status': 'error:', "message": "already present", "id" : already_present[0].id }, 409

        ## Sanity check comment
        if not api.payload['comment']:
            safe_comment = ""
        else:
            safe_comment = api.payload['comment']

        new_site = Site(
            url = api.payload['url'], 
            comment = safe_comment, # type: ignore
        )

        db.session.add(new_site)
        current_app.logger.debug("Site added via API")
        db.session.commit()
        return {'status': 'created', "id": new_site.id }, 201

@api.route('/<int:id>')
@api.param('id', 'The Site identifier')
@api.response(404, 'Site not found')
class site_item_api(Resource):
    @api.doc('delete site')
    def delete(self,id):
        target = Site.query.get_or_404(id)
        db.session.delete(target)
        db.session.commit()
        return {'status': 'ok:', "message": "deleted" }, 200

    @api.doc('update site')
    def put(self,id):
        target = Site.query.get_or_404(id)

        for key in api.payload:
            if key in site_model.keys():
                if key == 'id':
                    continue
                current_app.logger.debug(f"Looking at {key}")
                setattr(target, key, api.payload[key])
        
        db.session.commit()
        return {'status': 'ok:', "message": "updated" }, 200

