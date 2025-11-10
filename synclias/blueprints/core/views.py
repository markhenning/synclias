from flask import Blueprint
from flask import flash, redirect, render_template, url_for, abort, jsonify
from flask import request
from flask_login import login_required

from synclias.blueprints.core.forms import RouterForm, NameServersForm

## App specific
from flask import current_app
from synclias import db
from sqlalchemy import select
from synclias.models import Site,ASN,Router,Nameserver,SafetyKeyword,Prefs,Result

core = Blueprint("core", __name__, template_folder="templates")


## Main index page, get some stats and display
@core.route("/", methods=["GET"])
@login_required
def home():
    from synclias.blueprints.asndb.tasks import get_asn_file_info
    asndb_info = get_asn_file_info()
    prefs = db.session.query(Prefs).first()
    history = db.session.query(Result).order_by(Result.timestamp.desc()).first()
    if history is None:
        last_sync = "N/A"
    else:
        last_sync = history.timestamp
    stats = {
        "site_count" : db.session.query(Site).count(),
        "keyword_count" : db.session.query(SafetyKeyword).count(),
        "asn_count" : db.session.query(ASN).count(),
        "last_sync" : last_sync,
    }
    return render_template("/index.html",stats=stats, asndb_info=asndb_info, prefs=prefs)

## Main settings page
# GET -  show data
# POST - little more complicated - but deals with updating router settings
@core.route("/settings", methods=('GET', 'POST'))
@login_required
def settings():

    router_form = RouterForm()
    nameservers_form = NameServersForm()

    if request.method == "GET":

        router = db.session.query(Router).first()
        nameservers = db.session.query(Nameserver).all()
        prefs = db.session.query(Prefs).first()
        return render_template("/settings.html", router=router,nameservers=nameservers,prefs=prefs, router_form=router_form, nameservers_form=nameservers_form)

    else:

        current_app.logger.debug("Updating Router Settings")

        # Always the first Router, we don't support more
        router = db.session.query(Router).first()
        
        ## router table should exist, but it needs an automatic first row that could potentially fail
        if router is None:
            current_app.logger.critical(f"Settings Page - Error looking up Router")
            flash(f"Error looking up Router in database")
            return redirect(url_for("core.settings"))

        # Form data -> database
        router.hostname = request.form['hostname'] 
        router.apikey = request.form['apikey']  # type: ignore - TDE prevents linter seeing correct data type
        router.apisecret = request.form['apisecret']  # type: ignore TDE prevents linter seeing correct data type
        router.alias = request.form['alias'] 
        
        ## Yeah, database defaults should really eat these, instead of manual settings
        if 'alias_ipv6' in request.form.keys():
            router.alias_ipv6 = request.form['alias_ipv6']

        if 'https' in request.form.keys():
            router.https = True 
        else:
            router.https = False

        if 'verifytls' in request.form.keys():
            router.verifytls = True 
        else:
            router.verifytls = False 

        if 'ipv6' in request.form.keys():
            router.ipv6 = True 
        else:
            router.ipv6 = False
        
        db.session.commit()
        flash(f"Router settings updated!", 'success')

        return redirect(url_for("core.settings"))

## Nameserver update
# POST receives a single line (one nameserver) from the settings page
@core.route("/nameserver/update/<int:id>", methods=['POST'])
@login_required
def nameserver_update(id):
    current_app.logger.debug("Updating NS")

    nameserver= db.session.scalars(select(Nameserver).where(Nameserver.id == id)).one()

    if nameserver is None:
        current_app.logger.info(f"Error looking up Nameserver {id}")
        flash(f"Error looking up Nameserver in database")
        return redirect(url_for("core.settings"))

    # Form data -> database
    nameserver.hostname = request.form['hostname'] 
    nameserver.token = request.form['token']  # type: ignore - TDE causing incorrect warning
    nameserver.port = int(request.form['port'])
    nameserver.type = request.form['type'] 

    ## Checkboxes don't return anything if they're not checked, so we need to check if the name is actually in the return data
    if 'https' in request.form.keys():
        nameserver.https = True
    else:
        nameserver.https = False 
    
    if 'verifytls' in request.form.keys():
        nameserver.verifytls = True 
    else:
        nameserver.verifytls = False
    
    ## Done, store it
    db.session.commit()
    flash(f"{nameserver.hostname} settings updated!", 'success')
    return redirect(url_for("core.settings"))

## Adding a new nameserver
## POST - called by the Add Nameserver modal on the settings page
@core.route("/nameserver/create/", methods=["POST"])
@login_required
def nameserver_create():
    
    current_app.logger.debug("NS Add called")
    if not request.form:
        abort(400)
    
    if request.form['port'] == '':
        safe_port = 0
    else:
        safe_port = request.form['port']
        
    nameserver = Nameserver(
        hostname = request.form.get('hostname'), # type: ignore
        type = request.form.get('type'), # type: ignore 
        https = ('https' in request.form.keys()), # type: ignore
        port = safe_port, # type: ignore
        verifytls = ('verifytls' in request.form.keys()), # type: ignore
        token = request.form.get('token'), # type: ignore
    )

    db.session.add(nameserver)
    db.session.commit()
    return redirect(url_for("core.settings"))

## Delete nameserver - called by Delete button on Settings page, can't use DELETE as it would require extra Ajax steps, this is simpler
@core.route('/nameserver/delete/<int:id>', methods=["POST"])
@login_required
def nameserver_delete(id):
    
    nameserver = db.get_or_404(Nameserver, id)
    ## Pull out the hostname for logging afterwards, can't reference a deleted NS
    ns = nameserver.hostname
    db.session.delete(nameserver)
    db.session.commit()
    current_app.logger.info(f"Deleted Nameserver: {ns}")
    flash(f"Deleted: {ns}")
    return redirect(url_for("core.settings"))

## Update App Settings/Preferences
## Called by toggle/checkbox/dropdowns on Settings page (E.g. Auto-Sync)
## Simple put to URL
@core.route("/prefs/<string:option>/<int:new_state>", methods=['PUT'])
@login_required
def update_pref_option_by_string(option,new_state):
    
    prefs = db.session.query(Prefs).first()
    if prefs is None:
        current_app.logger.critical(f"Update Prefs - Can't pull preferences from database?")
        abort(500)
    
    current_app.logger.debug(f"Toggle pref option {option} to {new_state}")
    
    ## Check "option" is valid but not user_agent (needs a string, not int)
    if option in prefs.to_json().keys() and option not in ['user_agent']:
        
        ## Options for autosync will impact the scheduled task for autosync, handle here and apply changes
        if option == 'autosync' or option == 'sync_every':
            setattr(prefs, option, new_state) 
            from synclias.blueprints.scheduler.tasks import create_update_autosync_task
            create_update_autosync_task()
        
        ## Options for autosync will impact the scheduled task for autoasndb, hangle here and apply changes
        elif option == 'autoasndb' or option == 'asndb_every':
            setattr(prefs, option, new_state) 
            from synclias.blueprints.scheduler.tasks import create_update_autoasndb_task
            create_update_autoasndb_task()
        
        ## Just a "normal" setting, update the db
        elif option in ['purgedns', 'flush_states','global_dns_history','keep_dns_days']:
            setattr(prefs, option, new_state) 
           
        else:
            abort(400)
        
        db.session.commit()
        return jsonify({ 'option': option, 'setting': new_state},200)
    else:
        abort(400)

## Update Scanner Agent
## Pretty happy to accept anything user wants here
## Called by Scanner Agent modal on settings page
@core.route("/prefs/scanner_agent", methods=["POST"])
@login_required
def update_scanner_agent():
    
    if not request.form:
        abort(400)

    prefs = db.session.query(Prefs).first()
    if prefs is None:
        flash(f"Error finding prefs from database to update", 'critical')
        abort(400)
    
    if prefs:
        prefs.user_agent = request.form['user_agent']
    db.session.commit()
    flash("Saved User Agent", 'info')
    return redirect(url_for("core.settings"))
    
## Commented out docs page, unused but left for future use
# @core.route("/docs")
# @login_required
# def docs():
#     return render_template("/docs.html")




