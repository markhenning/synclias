from flask import current_app

from synclias import db
from sqlalchemy import select
from synclias.models import Site,Prefs,IPRecord

from synclias import create_celery_app
celery = create_celery_app()

from datetime import datetime, timedelta

## Create or update an IPRecord
# (Yes, I'm aware record types of A and AAAA, but I want 4/6, and storing "AAAA" rather than a single char seemed pointless)
## Timestamp should be passed in to have same for all times in scan
def update_dns_history(fqdn="invalid",dns_ip="0.0.0.0",record_type=4,timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')):
    
    ## Sanity check
    if record_type != 4 and record_type != 6:
        current_app.logger.warning("DNS Record Log - Error, passed invalid record type, ignoring")
    elif fqdn == "invalid":
        current_app.logger.warning("DNS Record Log - Error, passed invalid fqdn, ignoring")
    else:
        
        ## Check if "fqdn - record" it already exists, if so update
        ip_record = db.session.scalars(select(IPRecord).where(IPRecord.fqdn == fqdn).where(IPRecord.record_type == record_type).where(IPRecord.record == dns_ip)).first()
        if ip_record is not None:
            ip_record.last_seen = timestamp
            db.session.commit()
        else:
            ## New record
            ip_record = IPRecord(
                fqdn = fqdn, # type: ignore
                record = dns_ip, # type: ignore
                record_type = record_type, # type: ignore
                last_seen = timestamp, # type: ignore
            )
            current_app.logger.debug(f"Adding first sighting of DNS entry:  {ip_record.record} timestamp: {timestamp}")
            db.session.add(ip_record)
            db.session.commit()   

## Lookup all sites listed for DNS history and update record table
## Celery task, loaded from config/settings.py on startup, runs every 30 mins
@celery.task
def update_all_dns_history():
    ## Get all sites that are marked for history

    prefs = db.session.query(Prefs).first()
    if prefs is None:
        return "Error loading preferences from DB"

    ## Global override switch - collect for all configured sites, or just the ones marked on Sites page
    if prefs.global_dns_history:
        current_app.logger.info("Using all sites for DNS History scan")
        sites_with_history = db.session.scalars(select(Site)).all()
    else:
        current_app.logger.info("Using marked sites for DNS History scan")
        sites_with_history = db.session.scalars(select(Site).where(Site.use_dns_history == 1)).all()
    
    ## Sanity check - could have no sites configured for history
    if sites_with_history is None:
        current_app.logger.info(f"Historical DNS Scan called, no sites marked for history")
    
    else:
        # DNS Query and record store
        timestamp= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        from synclias.blueprints.syncer.tasks import resolve_all_urls
        
        for site in sites_with_history:
            ## Reusing the code from syncer - 
            # "None" is passed instead of "self" - during sync, self is used to report status updates
            dns_ips, dns_ips6, didnt_resolve = resolve_all_urls(None, [site.url])

            ## Database it all up
            if dns_ips is not None:
                for dns_ip in dns_ips:
                    update_dns_history(fqdn=site.url,dns_ip=dns_ip,record_type=4,timestamp=timestamp)

            if dns_ips6 is not None:
                for dns_ip in dns_ips6:
                    update_dns_history(fqdn=site.url,dns_ip=dns_ip,record_type=6,timestamp=timestamp)

## Purge old DNS entries based on timestamp
## Celery task, loaded into scheduler on startup in config/settings.py
@celery.task
def clear_dns_history_days():
    
    prefs = db.session.query(Prefs).first()
    target_time = datetime.now() - timedelta(days=prefs.keep_dns_days)
    to_delete = db.session.query(IPRecord).filter(IPRecord.last_seen < target_time).all()
    
    if to_delete is None:
        current_app.logger.info(f"DNS History Clear - Nothing to clear")
    else:
        for record in to_delete:
            db.session.delete(record)
        db.session.commit()

## Scrub history task. no referenced/linked to in any way at this time
def clear_dns_history():
    to_delete = db.session.query(IPRecord).all()

    for record in to_delete:
        db.session.delete(record)
    db.session.commit()