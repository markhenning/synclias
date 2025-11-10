from flask import Blueprint
from flask import request
from flask import flash, redirect, render_template, url_for, abort, jsonify

from flask_login import login_required

from .forms import AddKeywordForm

## App specific
from flask import current_app
from synclias import db
from sqlalchemy import select
from synclias.models import SafetyKeyword

keywords = Blueprint("keywords", __name__, template_folder="templates")

## Main Page
@keywords.route("/", methods=('GET',"POST"))
@login_required
def page():
    
    if request.method == "GET":
        page_id = request.args.get('page_id', 1, type=int)
        add_keyword_form = AddKeywordForm()

        safety_keywords = db.paginate((select(SafetyKeyword)).order_by(SafetyKeyword.keyword.asc()), page=page_id, per_page=10)

        next_url = url_for('keywords.page', page_id=safety_keywords.next_num) if safety_keywords.has_next else None
        prev_url = url_for('keywords.page', page_id=safety_keywords.prev_num) if safety_keywords.has_prev else None
        return render_template("/keyword.html",  safety_keywords=safety_keywords, add_keyword_form=add_keyword_form, next_url=next_url, prev_url=prev_url)

    else:

        ## POST - Adding keyword
        if not request.form:
            abort(400)
        to_add = request.form.get('keyword')
        in_db = db.session.query(SafetyKeyword).filter_by(keyword = to_add).first()
        if in_db:   
            flash(f"Keyword: \"{to_add}\" already present, ignoring", 'info')
            return redirect(url_for("keywords.page"))
        else:
            if 'exact' in request.form.keys():
                exact = 1
            else:
                exact = 0
            safety_keyword = SafetyKeyword(
                keyword=to_add, # type: ignore
                exact=exact, # type: ignore
            )
            db.session.add(safety_keyword)
            db.session.commit()
            return redirect(url_for("keywords.page"))

## Individual delete
@keywords.route('/delete/<int:id>', methods=["POST"])
@login_required
def delete(id):
    safety_keyword = db.get_or_404(SafetyKeyword, id)
    kw = safety_keyword.keyword
    db.session.delete(safety_keyword)
    db.session.commit()
    flash(f"Deleted: {kw}", 'info')
    return redirect(url_for("keywords.page"))

## Bulk delete - called by the "Delete Selected" button
@keywords.route('/delete/bulk/', methods=["POST"])
@login_required
def delete_bulk():
    
    if not request.form:
        abort(400)
    
    for key in request.form.keys():
        if key.startswith('select'):
            to_delete = key.split('-')[1]
            current_app.logger.info(f"Deleting Keyword: {to_delete}")
            safety_keyword = db.session.get(SafetyKeyword,to_delete)
            sk = safety_keyword.keyword # type: ignore
            db.session.delete(safety_keyword)
            db.session.commit()
            flash(f"Deleted: {sk}")
    return redirect(url_for("keywords.page"))


## Load suggestions from config/settings.py (Importend to app.config on startup)
@keywords.route('/create/suggestions', methods=["POST"])
@login_required
def keyword_add_suggestions():
  
    for suggestion in current_app.config['KEYWORD_SUGGESTIONS']:
        ## Test if it's already in there
        already_present = db.session.scalars(select(SafetyKeyword).where(SafetyKeyword.keyword == suggestion)).all()
        if already_present:
            flash(f"Already present: {suggestion}",category="info")
        else:
            current_app.logger.debug(already_present)
            new_keyword = SafetyKeyword(
                keyword = suggestion, # type: ignore
                exact = False, # type: ignore
            )
            db.session.add(new_keyword)

    ## ... can you tell "exact" got added later? will roll into the above, better, later 
    for suggestion in current_app.config['KEYWORD_SUGGESTIONS_EXACT']:
        ## Test if it's already in there
        already_present = db.session.scalars(select(SafetyKeyword).where(SafetyKeyword.keyword == suggestion)).first()
        if already_present:
            if already_present.exact == 0 or already_present.exact == False:
                already_present.exact = True
                db.session.commit()
                flash(f"Already present: {suggestion}, updated to exact match",category="info")
            else:
                flash(f"Already present: {suggestion}",category="info")
        else:
            current_app.logger.debug(already_present)
            new_keyword = SafetyKeyword(
                keyword = suggestion, # type: ignore
                exact = True, # type: ignore
            )
            db.session.add(new_keyword)

    # Commit and return       
    db.session.commit()
    return redirect(url_for("keywords.page"))

## Change an individual setting per site (e.g "exact match")
@keywords.route("/<string:option>/<int:id>/<int:new_state>", methods=['PUT'])
@login_required
def update_site_option(option,id,new_state):
    
    target = db.get_or_404(SafetyKeyword,id)

    if option == 'exact':
        current_app.logger.debug(f"Toggle keyword {id} option {option} to {new_state}")
        target.exact = new_state
        db.session.commit()
        return jsonify({ 'keyword' : id, 'option': 'exact', 'setting': new_state},200)
    else:
        abort(400)