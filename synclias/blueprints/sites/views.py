from flask import Blueprint
from flask import request
from flask import url_for, jsonify, redirect, abort, flash, render_template

from tldextract import tldextract
from flask_login import login_required
from .forms import AddSiteForm
from synclias.models import Site

from synclias import db
from sqlalchemy import select
from flask import current_app

sites = Blueprint("sites", __name__, template_folder="templates")

@sites.route("/", methods=["GET","POST"])
@login_required
def site():
    if request.method == "GET":
        add_site_form = AddSiteForm()
        
        ## Pagination work - calculate entries on this page, next/prev pages. "1" = Page 1 of results, overriden if parameter "page" passed
        page = request.args.get('page', 1, type=int)
        sites = Site.query.order_by('url_group').paginate(page=page,per_page=10)
        
        next_url = url_for('sites.site', page=sites.next_num) \
        if sites.has_next else None
        prev_url = url_for('sites.site', page=sites.prev_num) \
        if sites.has_prev else None

        return render_template("/site.html", sites=sites, add_site_form=add_site_form, next_url=next_url, prev_url=prev_url)

    else:
        ### Sanitise input
        # No form
        if not request.form:
            abort(400)
        
        # Remove whitespace, common in copy/pasted urls
        url = request.form.get('url')
        if url is None:
            abort(400)

        url = url.strip()

        ## No wildcards check
        if '*' in url:
            flash(f"Wildcards aren't possible - rejecting {url}")
            return redirect(url_for("sites.site"))
        
        ## Checkit loos like a hostname and get it's domain
        tld = tldextract.extract(request.form.get('url')) # type: ignore
        if not tld.fqdn:
            flash(f"Site supplied {url} not understood, rejecting",'info')
            return redirect(url_for("sites.site"))           
        
        already_present = db.session.scalars(select(Site).where(Site.url == tld.fqdn)).all()
        if already_present:
            flash(f"Site: {tld.fqdn} already present",'info')
            return redirect(url_for("sites.site"))

        ## Build and save new site.
        site = Site(
            url=tld.fqdn, # type: ignore
            url_group=tld.top_domain_under_public_suffix # type: ignore
        )
        db.session.add(site)
        db.session.commit()
        return redirect(url_for("sites.site"))


@sites.route('/delete_bulk/', methods=["POST"])
@login_required
def delete_bulk():

    for key in request.form.keys():
        if key.startswith('select'):
            to_delete = key.split('-')[1]
            current_app.logger.info(f"{to_delete}")
            site = db.session.get(Site,to_delete)
            if site is not None:
                site_url = site.url
                db.session.delete(site)
                db.session.commit()
                flash(f"Deleted: {site_url}")
            else:
                ## Genuinely amazed if you get here, but never say never.
                flash(f"Error finding site {to_delete}")
    return redirect(url_for("sites.site"))

@sites.route('/delete/<int:id>', methods=["POST"])
@login_required
def delete(id):
    site = db.get_or_404(Site, id)
    db.session.delete(site)
    db.session.commit()
    return redirect(url_for("sites.site"))

@sites.route("/<string:option>/<int:id>/<int:new_state>", methods=['PUT'])
@login_required
def update_site_option(option,id,new_state):
    target = Site.query.get_or_404(id)

    ## Check it's valid, but not in columns we don't update
    if option in target.to_json().keys() and option not in ['id','url','url_group']:

        current_app.logger.debug(f"Toggle site {id} option {option} to {new_state}")
        
        ## Sanity checked enough, trust what we've got
        setattr(target,option,new_state)

        db.session.commit()
        return jsonify({ 'site' : id, 'option': option, 'setting': new_state},200)
    else:
        abort(400)


@sites.route("/create/bulk/", methods=["POST"])
@login_required
def create_bulk_site():

    ## data format received - [('site1', 'www.foo.com'), ('site2', 'www.bar.com')....]
    for row in request.form.items():

        to_add = row[1]

        if '*' in to_add:
            flash(f"Wildcards aren't possible - rejecting {to_add} (I'm not sure how you got that in there!)",'info')
            continue
        
        current_app.logger.debug(f"Got site: {to_add}, looking in DB")
        in_db = db.session.query(Site).filter_by(url = to_add).first()
        if not in_db:
            current_app.logger.debug(f"Not found, adding")
            tld = tldextract.extract(to_add)
            site = Site(
                url = to_add, # type: ignore
                url_group=tld.top_domain_under_public_suffix, # type: ignore
            )
            db.session.add(site)
            db.session.commit()
        else:
            flash(f"Site: {to_add} already present",'info')
            current_app.logger.debug(f"Already in database, skipping {to_add}")

    return redirect(url_for("sites.site"))

