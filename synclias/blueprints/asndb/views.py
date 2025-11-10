from flask import Blueprint
from flask import request
from flask import url_for, jsonify, abort, redirect, flash, render_template
from flask_login import login_required

import tldextract

from .forms import AddASNForm, LookupASNForm

from flask import current_app
from synclias import db

from synclias.models import ASN

asndb = Blueprint("asns", __name__, template_folder="templates")

## Main ASN page
# GET - list ASNs/Lookup form
# POST - if we've got a valid form, load the page (will keep the data) and "start lookup" (Triggers modal open and lookup task)
#      - if no valid form (somehow) - present the page an error and let user figure it out
@asndb.route("/", methods=('GET','POST'))
@login_required
def page():

    add_asn_form = AddASNForm()
    lookup_asn_form = LookupASNForm()
    asns = db.session.query(ASN).all()
    
    if request.method == "GET":
        return render_template("/asn.html", asns=asns, add_asn_form=add_asn_form, lookup_asn_form=lookup_asn_form)
    
    ## Lookup
    ## Add ASN posts to another core, so this MUST be an ASN lookup, handle as such
    if lookup_asn_form.validate_on_submit():
        return render_template("/asn.html", asns=asns, add_asn_form=add_asn_form, lookup_asn_form=lookup_asn_form, start_lookup=True)  
    else:
        ## Just in case
        current_app.logger.info("Post, no lookup data data")
        return render_template("/asn.html", asns=asns, add_asn_form=add_asn_form, lookup_asn_form=lookup_asn_form)

## Create ASN route
@asndb.route("/create", methods=["POST"])
@login_required
def create():
    if not request.form:
        current_app.logger.debug("Rejecting for lack for form")
        abort(400)
    current_app.logger.debug(request.form)
    if (request.form.get('comment')).startswith('ERROR-'): # type: ignore
        temp_comment = "Unknown"
    else:
        temp_comment = request.form.get('comment')
    asn = ASN(
        asn=request.form.get('asn'), # type: ignore
        comment = temp_comment, # type: ignore
    )
    db.session.add(asn)
    db.session.commit()
    return redirect(url_for("asns.page"))

## Get ASN DB Stats (file info)
# Used by Home/Status page, and called by the downloader status check to see if files are actually growing
@asndb.route("/stats", methods=["GET"])
@login_required
def get_asndb_stats():
    from synclias.blueprints.asndb.tasks import get_asn_file_info
    response = get_asn_file_info()
    return jsonify(response)

## Lookup ASN info posted from main page form
## Takes a string, extracts tld from it, uses that to lookup asn/bgp and returns
## TODO - Better naming - "find" vs "get site" function naming is ambiguous
@asndb.route("/find/", methods=['POST'])
@login_required
def find_site_asn_bgp():
    
    url = request.get_json()
    url_site = url['site']

    ## Get the tld from whatever was supplied
    tld = (tldextract.extract(url_site)).top_domain_under_registry_suffix # type: ignore
    current_app.logger.debug(f"Looking up {tld}")
    
    ## Lookup 
    if not tld is None:
        from synclias.blueprints.asndb.tasks import get_site_asn_bgp
        response = get_site_asn_bgp(tld)
    else:
        response = {
            'found' : False,
            'asn' : "Error",
            'asn_name' : "Couldn't find domain in supplied text",
            'bgp' : "Error",
            'subnet_count' : "Error",
            'asn_ip_count' : "Error",
        }

    return jsonify(response)

## Delete - can't directly use DELETE without ajax, browsers don't make them - so it's a POST for now
## Called by Delete button on ASN Page
@asndb.route('/delete/<int:id>', methods=["POST"])
@login_required
def delete(id):
    asn = db.get_or_404(ASN, id)
    db.session.delete(asn)
    db.session.commit()
    flash(f"Deleted ASN: {asn.asn}","info")
    return redirect(url_for("asns.page"))

## ASN DB Download task monitoring
@asndb.route('/download_asndb/status/<task_id>', methods=['GET'])
@login_required
def download_asndb_status(task_id):
    ## This really sucks, we have to launch external 3 external scripts to get/convert the files, those scripts are better than I could ever hope to write though
    ## BUT the download servers can be a little "iffy" there's a real chance it stalls out, so let's monitor what we can

    ## For reference, the three files we'll get/create:
    #ASNDB_TEMP_RIB_FILE = 'latest.rib' -- Downloads first, if this is going to timeout, it'll be here, average download time, 5-10 mins, size: ~80MB
    #ASNDB_FILE = 'asndb' -- Created locally by converting the TEMP_RIB_FILE      
    #ASNDB_NAMES_FILE = 'asn_names' -- Created from downloads from multiple sites (HTTP) and collating
    from synclias.blueprints.asndb.tasks import get_asn_file_info
    from synclias.blueprints.asndb.tasks import download_asn_db_and_names
    task = download_asn_db_and_names.AsyncResult(task_id)
    if task.state == 'PENDING':
    # job did not start yet
        response = {
            'state': task.state,
            'current_step' : "Pending...",
            'message' : 'Awaiting scheduling...',
            'status': task.info.get('status'),
        }
    elif task.state != 'FAILURE':
    ## Task is currently running, let's get some stats at least
 
        ## Work out what we can get info on
        if task.info.get('current_step') == '1/3 - DB Download':
            stats = get_asn_file_info()
            messagetext = f"Currently downloading, have {stats['ASNDB_TEMP_RIB_FILE']['size_mb']} MB, last updated {stats['ASNDB_TEMP_RIB_FILE']['modified']} expected file size ~60-80MB"
            current_app.logger.debug(f"Stats: {stats}")
            current_app.logger.debug(messagetext)
            response = {
                'state': task.state,
                'current_step' : '1/3 - DB Download',
                'message' : messagetext,
                'status': task.info.get('status'),
            }

        elif task.info.get('current_step') == '2/3 - Converting':
            ## No point in getting file info, this just needs to run, it'll finish
            response = {
                'state': task.state,
                'current_step' : '2/3 - Converting',
                'message' : f"Converting downloaded file, this can take up to 5 minutes",
                'status': task.info.get('status'),
            }

        elif task.info.get('current_step') == '3/3 - Names Download':
            ## No point in getting file info, nothing to monitor as it's all in memory until the final write out to disk
            response = {
                'state': task.state,
                'current_step' : '3/3 - Names Download',
                'message' : f"Grabbing ASN names file, this can take up to 5 minutes",
                'status': task.info.get('status'),
            }

        elif task.info.get('current_step') == 'Completed!':
            ## No point in getting file info, nothing to monitor as it's all in memory until the final write out to disk
            response = {
                'state': task.state,
                'current_step' : 'Completed!',
                'message' : f"Completed!",
                'status': task.info.get('status'),
            }

        if 'result' in task.info:
            response = {
                'state': task.state,
                'current_step' : 'Completed!',
                'message' : f"Completed!",
                'status': task.info.get('status'),
            }
            response['result'] = task.info['result']
    else:
        # Task status is FAILED
        response = {
            'state': task.state,
            'current_step' : 'N/A',
            'message' : str(task.info),  # this is the exception raised
            'status': task.info.get('status'),
        }

    ### This set of tests is broken, but in a working way.....
    if task.state == 'SUCCESS':
        current_app.logger.debug(f"Complete!")

        response = {
            'state': task.state,
            'current_step' : 'Completed!',
            'message' : f"Completed!",
            'status': task.info.get('status'),
        }

    return jsonify(response)

## Trigger downloading of the ASN Database
## This can take a while, so background it
## Return task id after creation, ajax on page will use task status above to monitor
@asndb.route("/download_asndb", methods=["POST"])
@login_required
def download_asndb():
    from synclias.blueprints.asndb.tasks import download_asn_db_and_names
    task = download_asn_db_and_names.delay()
    return jsonify({}), 202, {'Location': url_for('asns.download_asndb_status', task_id=task.id)}

