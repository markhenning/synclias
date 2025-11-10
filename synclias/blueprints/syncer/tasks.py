from flask import current_app

import dns.resolver, dns.exception
import socket
import json
import datetime

from synclias.models import Site,ASN,SafetyKeyword,Result
import synclias.blueprints.technitium.tasks as technitium
import synclias.blueprints.opnsense.tasks as opnsense
import synclias.blueprints.asndb.tasks as asndb
import synclias.blueprints.scanner.tasks as scanner
from flask import session

from sqlalchemy import select

import pickle

from synclias import create_celery_app
from synclias import db

from synclias.models import Nameserver,Router,Prefs, IPRecord

celery = create_celery_app()

## Resolve a hostname against a specific DNS Server (and force it into cache)
## Allows us to guarantee the IPs we're adding to the rule will be what any client gets
def resolve_ip_by_nameserver(site,nameserver,qtype='A'):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [nameserver]
    try: 
       answer = resolver.resolve(site,qtype)
       current_app.logger
    except dns.resolver.NoAnswer:
        ## No record, this isn't exactly an error, some sites don't have AAAA records etc
        return set()
    except dns.resolver.NXDOMAIN:
        ## NXDOMAIN, shouldn't happen, but again, it's an "acceptable" reponse (will be flagged as "Didn't resolve" later)
        return set()
    except dns.exception.Timeout:
        current_app.logger.info(f"DNS Server couldn't resolve {site} - External DNS Timeout, if this keeps happening, consider removing it")
        return set()
    except Exception as e:
        ## Catchall - this we flag to the logs
        current_app.logger.info(f"Error in Name resolution for {site} - {e.args} - {e}")
        return set()
    
    ips = set()
    if answer:
        for rdata in answer:
            ips.add(rdata.to_text())
        return ips


## Get a list of fqdns that have "Use historical data" set
def get_historical_sites():

    sites_for_history = db.session.scalars(select(Site).where(Site.use_dns_history == 1)).all()
    historical_sites = []
    if sites_for_history is not None:
        for site in sites_for_history:
            historical_sites.append(site.url)

    return historical_sites

def resolve_all_urls(syncer_obj, sites, clear_cache=False):
    ## This is called by the dns history function, where there is no syncer, So we send a None.
    ## Could use a mock but that has some history that None doesn't worry about

    ## Returns, update as we go
    dns_ips = set()
    dns_ips6 = set()

    # Status Tracking for progress
    purged = 0
    to_purge = len(sites)
    if syncer_obj is not None:
        syncer_obj.update_state(state='PROGRESS', meta={'current': 5, 'total': 10, 'subtask_current' : purged, 'subtask_total' : to_purge, 'status': "DNS Cache Purge"}) 

    # Tracking
    didnt_resolve = []

    ## Resolver likes to have IPs for specific server targetting
    ## Lookup the IPs of the nameservers
    nameservers = db.session.query(Nameserver).all()
    nameserver_ips = []
    for nameserver in nameservers:
        # Lookup the IP, or pass it through if we've got an IP address for the server
        nameserver_ips.append(socket.gethostbyname(nameserver.hostname))
    


    ## Cache Clear
    
    prefs = db.session.query(Prefs).first()
    router = db.session.query(Router).first()
    current_app.logger.debug(f"Trying to clear {sites}")
    if clear_cache:
        if not prefs.purgedns:
            current_app.logger.info(f"SYNCER - Skipping DNS Purge - due to global preference")
        else:
            for site in sites:
                technitium.clear_cache_entry(site)
                purged += 1
                if syncer_obj is not None:
                    syncer_obj.update_state(state='PROGRESS', meta={'current': 5, 'total': 10, 'subtask_current' : purged, 'subtask_total' : to_purge, 'status': "DNS Cache Purge"}) 
            
    
            

    ## Actually resolve the list
    to_resolve = len(sites)
    historical_sites = get_historical_sites()
    resolved = 0
    if syncer_obj is not None:
        syncer_obj.update_state(state='PROGRESS', meta={'current': 6, 'total': 10, 'subtask_current' : resolved, 'subtask_total' : to_resolve, 'status': "DNS Lookups"}) 

    ## Could just stop this for "historical sites", but consistency on everything doing DNS, and resolution checks etc are all in place
    ## And calling "update historical sites" here would cause some wierd loop problemw      
    for site in sites:
        for ns_ip in nameserver_ips:
            dns_ips.update(resolve_ip_by_nameserver(site,ns_ip)) # type: ignore
            if router.ipv6: # type: ignore
                dns_ips6.update(resolve_ip_by_nameserver(site,ns_ip,qtype='AAAA')) # type: ignore

        ## Inject historical records if used
        if site in historical_sites:
            historical_records = db.session.scalars(select(IPRecord).where(IPRecord.fqdn == site)).all()
            if historical_records is not None:
                for h_record in historical_records:
                    if h_record.record_type == 4:
                        dns_ips.add(h_record.record)
                    elif h_record.record_type == 6:
                        dns_ips6.add(h_record.record)

        resolved += 1
        if syncer_obj is not None:
            syncer_obj.update_state(state='PROGRESS', meta={'current': 6, 'total': 10, 'subtask_current' : resolved, 'subtask_total' : to_resolve, 'status': "DNS Lookups"}) 

    if syncer_obj is not None:
        current_app.logger.debug(f"IPv4 resolutions: {dns_ips}")
        current_app.logger.debug(f"IPv6 resolutions: {dns_ips6}")
    return dns_ips, dns_ips6, didnt_resolve

## Work out the complete list of domains by scanning sites
def get_all_urls(syncer_obj):
    
    full_sites = set()
    
    sites = db.session.query(Site).all()

    to_scan = len(sites)
    scanned = 0
    syncer_obj.update_state(state='PROGRESS', meta={'current': 4, 'total': 10, 'subtask_current' : scanned, 'subtask_total' : to_scan, 'status': "Scanning Sites"}) 

    ##Tracking for logging later
    parent_child_sites = {}
    scan_failures = {}
    
    for site in sites:
        if site.crawl:
            links, fqdns_and_domains, rcode, notes = scanner.scanner(site.url)
            full_sites.update(links)
            if rcode != 200:
                current_app.logger.debug(f"Couldn't scan {site.url}, rcode: {rcode}, {notes} consider turn off crawl or adding to safety keyword")
                scan_failures.update({ site.url : f"Rcode: {rcode}, {notes}" })
            parent_child_sites[site.url] = links
        else:
            ## If we're not crawling the site, return just the original
            full_sites.add(site.url)
        scanned += 1
        syncer_obj.update_state(state='PROGRESS', meta={'current': 4, 'total': 10, 'subtask_current' : scanned, 'subtask_total' : to_scan, 'status': "Scanning Sites"}) 


    return full_sites, parent_child_sites, scan_failures

## Prune Safety Keywords from site list
def remove_safety_keywords(site_list):
    
    ## Log what to remove so we can log it
    remove_for_safety = {}
    
    for keywords in db.session.query(SafetyKeyword).all():
        for site in site_list:
            if keywords.exact:
                if keywords.keyword == site:
                    remove_for_safety[site] = keywords.keyword                    
            else:
                if keywords.keyword in site:
                    ## Flag for removal
                    remove_for_safety[site] = keywords.keyword

    ## Remove
    for site in remove_for_safety.keys():
        current_app.logger.info(f"Syncer - Keyword {remove_for_safety[site]} caused removal of {site}")
        site_list.remove(site)

    return site_list, remove_for_safety

## Push "override_safety" sites back into the list
def re_add_forced_urls(site_list):
    
    forced_urls = []
    for site in db.session.query(Site).all():
        if site.override_safety:
            if not site.url in site_list:
                # Put it back in
                site_list.add(site.url)
                ## Track that we did it
                forced_urls.append(site.url)
    return site_list, forced_urls

## Get all subnets inside an ASN
def get_all_asn_subnets():
    
    asn_subnets = set()
    for asn in db.session.query(ASN).all():
        nets = asndb.get_asn_subnets(asn.asn)
        asn_subnets.update(nets) # type: ignore
    return asn_subnets

## Work out differences between two IP sets
def get_set_differences(check_set, target_set):
    
    differences = set()
    for ip in check_set:
        if not ip in target_set:
            differences.add(ip) 
    return differences

def run_preflight():
    ## Test we've got required settings:
    results = {
        'proceed' : True,
        'message' : "",
    }

    ## Originally had a check for "Do we have any sites listed"
    ## Removed to allow deletion of all sites from Alias
    ## Message is here to remind that that decision was made
    
    #Router ok?
    router_preflight = opnsense.preflight_test()
    current_app.logger.info(f"Preflight complete - {router_preflight}")
    if not router_preflight['proceed']:
        results['proceed'] = False
        results['message'] = router_preflight['message']
        return results
    
    # Nameservers?
    ns_count = Nameserver.query.count()
    if ns_count == 0:
        results['proceed'] = False
        results['message'] = "No Nameservers configured!"

    return results

def record_sync_log(sync_log, changes=0):
    now = datetime.datetime.now()
    result_record = Result(
        changes = changes,
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S'), # type: ignore
        result_pickle = pickle.dumps(sync_log), # type: ignore
    )
    db.session.add(result_record)
    db.session.commit()


@celery.task(bind=True)
def run_syncer(self):

    ## Dict to put data into as we go, this could get huge
    ## For now, it's a copy of a lot of data, once working will replace individual variables (to_add) etc, no point in duplication
    sync_log = {}
    sync_log['stats'] = {}
    now = datetime.datetime.now()
    sync_log['stats']['start_time'] = now.strftime('%Y-%m-%d %H:%M:%S')


    # Update that task is off the waiting list and executing
    self.update_state(state='PROGRESS', meta={'current': 1, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "Preflight Checks"})

    ###### Preflight Checks
    preflight_results = run_preflight()

    current_app.logger.info(f"Preflight: {preflight_results}")

    sync_log.update({'preflight' : preflight_results})
    current_app.logger.warning(sync_log)

    if not preflight_results['proceed']:
        current_app.logger.warning(f"Preflight failed - {preflight_results['message']}")
        self.update_state(state='FAILED', meta={'current': 1, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': f"Preflight fail - {preflight_results['message']}"}) 
        record_sync_log(sync_log)
        return {'current': 1, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': f'{preflight_results['message']}', 'result': "Failed"}

    ######## Data Gathering

    ## Current OpnSense running config - TODO - move to preflight
    router = db.session.query(Router).first()
    if router is None:
        record_sync_log(sync_log=sync_log)
        self.update_state(state='FAILED', meta={'current': 2, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "Error: Could't get Router info"})  
        return {'current': 2, 'total': 10, 'subtask_current' : 1, 'subtask_total' : 1, 'status': 'Could not get router info', 'result': "Failed"}

    prefs = db.session.query(Prefs).first()
    if router is None:
        record_sync_log(sync_log=sync_log)
        self.update_state(state='FAILED', meta={'current': 2, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "Error: Could't get Preferences"})  
        return {'current': 2, 'total': 10, 'subtask_current' : 1, 'subtask_total' : 1, 'status': 'Could not get preferences', 'result': "Failed"}

    nameservers = db.session.query(Nameserver).all()
    if nameservers is None:
        ## If preflight passed, this shouldn't be possible, but never say never
        record_sync_log(sync_log=sync_log)
        self.update_state(state='FAILED', meta={'current': 2, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "Error: Could't get Nameservers"})
        return {'current': 2, 'total': 10, 'subtask_current' : 1, 'subtask_total' : 1, 'status': 'Could not get Nameservers', 'result': "Failed"}     

    ###### Pull in curent alias ips

    self.update_state(state='PROGRESS', meta={'current': 2, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "Getting Alias IPs"})  
    alias = router.alias # type: ignore
    alias_ips = opnsense.get_alias_ips(opnsense.get_alias_json(router.alias))

    sync_log.update({'alias': {}})
    sync_log['alias'].update({'ipv4' : list(alias_ips)})

    if router.ipv6:
        alias_ipv6 = opnsense.get_alias_ips(opnsense.get_alias_json(router.alias_ipv6))
        sync_log['alias'].update({'ipv6' : list(alias_ipv6)})
    
    current_app.logger.warning(sync_log)

    ###### ASN Subnet gathering
    self.update_state(state='PROGRESS', meta={'current': 3, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "Getting ASNs"})    

    asn_subnets = get_all_asn_subnets()

    ####### Site Scanning
    self.update_state(state='PROGRESS', meta={'current': 4, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "Scanning Sites"})    

    ## Get the complete list of URLs, including crawling sites as needed
    active_urls, sync_log['discovery_map'], sync_log['scan_failures'] = get_all_urls(self)
    current_app.logger.debug(f"Parent-Child Mapping: {sync_log['discovery_map'] }")

    ## List Manipulation - Safety Keywords, and "Override Safety Keywords"
    active_urls, sync_log['keyword_removals'] = remove_safety_keywords(active_urls)
    current_app.logger.debug(f"Removed by keyword: {sync_log['keyword_removals']}")
    
    active_urls, sync_log['forced_entries'] = re_add_forced_urls(active_urls)
    current_app.logger.debug(f"Forced back in: {sync_log['forced_entries']}")

    ###### DNS Work begins, clear and query all sites
    self.update_state(state='PROGRESS', meta={'current': 5, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "DNS Cache Work"})   

    ## Check if we can actually clear caches, this should really call "/features", otherwise it'll be a future bug
    if prefs.purgedns:
        cache_clear = True
        for nameserver in nameservers:
            if nameserver.type == "standard_ns":
                cache_clear = False
                current_app.logger.info(f"SYNCER - Skipped DNS Purge - {nameserver.hostname} is read-only")
    else:
        cache_clear = False


    ## Resolve every url to an IP address in a set, allow it to clear cache if enabled and DNS servers support it (checked inside that function)
    dns_ips, dns_ipv6s, sync_log['unresolved_urls'] = resolve_all_urls(self, active_urls, clear_cache=cache_clear)
    current_app.logger.debug(f"Unresolved URLs: {sync_log['unresolved_urls']}")

    ####### Calculate required changes
    self.update_state(state='PROGRESS', meta={'current': 7, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "Calculating Changes"})   

    full_ips = set()
    full_ips.update(dns_ips)
    full_ips.update(asn_subnets)

    ##### Differencing

    ## Work out what we need to do
    to_add = get_set_differences(full_ips, alias_ips)
    to_remove = get_set_differences(alias_ips, full_ips)
    current_app.logger.warning(sync_log)
    current_app.logger.warning(f"To add: {to_add}")
    sync_log['ipv4'] = {}
    sync_log['ipv4']['to_add'] = list(to_add)
    sync_log['ipv4']['to_remove'] = list(to_remove)

    ## Check if we need to actually do anything and whether a "reconfigure" is needed
    need_reconfigure = False
    if len(to_add) > 0:
        need_reconfigure = True
    if len(to_remove) > 0:
        need_reconfigure = True

    current_app.logger.info(f"SYNCER - Calculation - Entries to add: {len(to_add)}")
    current_app.logger.info(f"SYNCER - Calculation - Entries to remove: {len(to_remove)}")

    ## Same again, if IPv6 needed
    if router.ipv6:
        to_add_ipv6 = get_set_differences(dns_ipv6s, alias_ipv6)
        to_remove_ipv6 = get_set_differences(alias_ipv6, dns_ipv6s)
        
        sync_log['ipv6'] = {}
        sync_log['ipv6']['to_add'] = list(to_add_ipv6)
        sync_log['ipv6']['to_remove'] = list(to_remove_ipv6)
        if len(to_add_ipv6) > 0:
            need_reconfigure = True
        if len(to_remove_ipv6) > 0:
            need_reconfigure = True
        current_app.logger.info(f"SYNCER - Calculation - Entries to add IPv6: {len(to_add_ipv6)}")
        current_app.logger.info(f"SYNCER - Calculation - Entries to remove IPv6: {len(to_remove_ipv6)}")

    ###### Sync

    sync_log['stats']['alias_changes'] = len(to_add) + len(to_remove) 
    if router.ipv6:
        sync_log['stats']['alias_changes'] = sync_log['stats']['alias_changes'] + len(to_add_ipv6) + len(to_remove_ipv6) 

    sync_log['stats']['alias_changes']
    self.update_state(state='PROGRESS', meta={'current': 8, 'total': 10, 'subtask_current' : 0, 'subtask_total' : sync_log['stats']['alias_changes'], 'status': "Add/Remove IPs"})   

    alias_changes_completed = 0
    ## Actually do the add/removes
    for ip in to_add:
        opnsense.modify_alias("add",alias,ip)
        alias_changes_completed += 1
        self.update_state(state='PROGRESS', meta={'current': 8, 'total': 10, 'subtask_current' : alias_changes_completed, 'subtask_total' : sync_log['stats']['alias_changes'], 'status': "Add/Remove IPs"})   
    for ip in to_remove:
        opnsense.modify_alias("delete",alias,ip)
        alias_changes_completed += 1
        self.update_state(state='PROGRESS', meta={'current': 8, 'total': 10, 'subtask_current' : alias_changes_completed, 'subtask_total' : sync_log['stats']['alias_changes'], 'status': "Add/Remove IPs"})   
    
    ## Repeat for IPv6 if needed
    if router.ipv6:
        alias_to_modify = router.alias_ipv6
        for ip in to_add_ipv6:
            opnsense.modify_alias("add",alias_to_modify,ip)
            alias_changes_completed += 1
            self.update_state(state='PROGRESS', meta={'current': 8, 'total': 10, 'subtask_current' : alias_changes_completed, 'subtask_total' : sync_log['stats']['alias_changes'], 'status': "Add/Remove IPs"})   
    
        for ip in to_remove_ipv6:
            opnsense.modify_alias("delete",alias_to_modify,ip)
            alias_changes_completed += 1
            self.update_state(state='PROGRESS', meta={'current': 8, 'total': 10, 'subtask_current' : alias_changes_completed, 'subtask_total' : sync_log['stats']['alias_changes'], 'status': "Add/Remove IPs"})   
    
    ###### Reconfigure and Flush States if needed
    current_app.logger.info(f"SYNCER - IP Changes - Complete, proceeding to reconfigure")
    self.update_state(state='PROGRESS', meta={'current': 9, 'total': 10, 'subtask_current' : 0, 'subtask_total' : 1, 'status': "Reconfigure and flush"})    

    sync_log['stats']['needed_reconfigured'] = need_reconfigure
    sync_log['stats']['status_flushed'] = "Not used"
    if need_reconfigure:
        opnsense.reconfigure_aliases()    
        if prefs.flush_states: # type: ignore
            if opnsense.flush_states():
                sync_log['stats']['status_flushed'] = "Success"
                current_app.logger.info(f"SYNCER - Flushed States")
            else:
                current_app.logger.warning(f"SYNCER - Flushed States was specified, but didn't function")
                sync_log['stats']['status_flushed'] = "Failed"

    self.update_state(state='PROGRESS', meta={'current': 10, 'total': 10, 'subtask_current' : 1, 'subtask_total' : 1, 'status': "Complete"}) 

    ## just dumping out for now
    current_app.logger.warning(sync_log)

    now = datetime.datetime.now()

    sync_log['stats']['end_time'] = now.strftime('%Y-%m-%d %H:%M:%S')
    record_sync_log(sync_log=sync_log,changes=sync_log['stats']['alias_changes'])
    return {'current': 10, 'total': 10, 'subtask_current' : 1, 'subtask_total' : 1, 'status': 'Sync completed', 'result': "Done"}

