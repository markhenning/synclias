import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from synclias.models import Prefs
import tldextract
from flask import current_app
from synclias import db

from synclias import create_celery_app
celery = create_celery_app()

## Helper function - Sites page needs tld for making the list reasonably sorted
## takes [site1.tld, site2.tld2] -> [{site1.tld : tld}, {site2.tld2 : tld2}]
def add_tld(url_list):

    siteinfo = {}
    for url in url_list:
        tld = tldextract.extract(url)
        siteinfo[url] = tld.registered_domain
    return siteinfo


def scanner(site, safe_scan=True):

    prefs = db.session.query(Prefs).first()
    status = 500
    notes = '' 

    try:
        ## Sanity check start of string
        if not site.startswith('http'):
            lookupsite = "https://" + site
        else:
            lookupsite = site

        ## URL crawl
        if prefs.user_agent: # type: ignore
            headers = {}
            headers['User-Agent'] = prefs.user_agent # type: ignore
            r = requests.get(lookupsite, headers=headers,timeout=6)
        else:
            r = requests.get(lookupsite, timeout=6)
        status = r.status_code
        r.raise_for_status()

        links = []
        img_links = []
        
        ## safe_scan=False will tear out every fqdn from everywhere in the content
        ## Non safe_scan just looks at hrefs and img links, safer for users and less likely to screw up global js delivery

        ## At this time they both return slightly different dataset formats, which is a problem, but fixed later in the function
        ## safe_scan was added as a hammer later on, need to adjust outputs from each to match
        if safe_scan:
            soup = BeautifulSoup(r.content,features="lxml")
            links = soup.find_all('a', {'href': re.compile(r"^https?://(.*?)/.*$")})
            img_links = soup.find_all('img', {'src': re.compile(r"^https?://(.*?)/.*$")})
        else:
            link_regex = re.compile(r'https?://([a-zA-Z0-9.-]{1,63}?)[/\"\']')  ## Spec says a-z0-9-, but I don't trust people not to put capitals in. I think I need to add \? into the last [], but testing first
            links = re.findall(pattern=link_regex, string=str(r.content))



    except requests.exceptions.ConnectionError as e:
        links = []
        current_app.logger.debug(f'An error occurred: {e}')
        notes = 'Connection Error'
    except requests.exceptions.HTTPError as e:
        links = []
        current_app.logger.debug(f'An error occurred: {e}')
        notes = 'HTTP Error'
    except requests.exceptions.ReadTimeout as e:
        links = []
        current_app.logger.debug(f'An error occurred: {e}')
        notes = 'Timeout Error'
    except requests.exceptions.RequestException as e:
        links = []
        current_app.logger.debug(f'An error occurred: {e}')
        notes = 'Request Failure'

    uris = set()  
    
    ## Add the site url scanned for to the uri list
    if site:
        host_name = urlparse(lookupsite).hostname
        uris.add(host_name)

    if len(links) != 0:
        if safe_scan:
            uri_p = re.compile('^https?://(.*?)/.*$')
            for link in links:
                uri = uri_p.search(link.get('href')) # type: ignore
                if (uri.group(1)):
                    uris.add(uri.group(1))

            ## Should be an expansion of the above, but..
            for link in img_links:
                uri = uri_p.search(link.get('src')) # type: ignore
                if (uri.group(1)):
                    uris.add(uri.group(1))
        
        else:
            for link in links:
                uris.add(link) 

    ## This should be part of the return to JS in another function, it's a messy way of handling this
     
    fqdn_and_domain = {}
    if uris != set():
        fqdn_and_domain = add_tld(uris)

    return uris,fqdn_and_domain, status,notes



## Wrapper for when we need to just hit one site in the background
@celery.task(bind=True)
def scanner_bg(self, site, safe_scan):
    
    self.update_state(state='PROGRESS', meta={'scan_rcode': 'pending', 'notes': 'pending', 'status': 'Scanning'})
    uris,fqdn_and_domain, r_code,notes = scanner(site=site, safe_scan=safe_scan)

    ## Right now "fqdn_and_domain" contains a dict of site : tld, which ideally we should just pass off to Javascript, JSON or otherwise sort it there and display
    ## However, I cannot get it to do that, so I'll sort it here and pass a list
    ## I think this is all now unnecessary, (added "uri's" back in, which should be sortable etc before appending)
    ## Leaving in for now whilst I work elsewhere
    sorted_uris = sorted(fqdn_and_domain.items(), key=lambda x:x[1])
    converted_dict = dict(sorted_uris)
    sorted_url_list = list(converted_dict.keys())

    current_app.logger.debug(f"BG Task Response: {uris}")

    self.update_state(state='PROGRESS', meta={'scan_rcode': r_code, 'status': 'Task completed!', 'result': sorted_url_list})    

    return {'scan_rcode': r_code, 'notes' : notes, 'status': 'Task completed!', 'result': sorted_url_list}


