import os
from datetime import datetime
import pyasn
import json
from dns import resolver
from flask import current_app

from synclias import create_celery_app
celery = create_celery_app()

## File check/stats reporting
## Called by /stats and by download task status monitor
def get_asn_file_info():
    file_info = {}
    for handle in ['ASNDB_FILE','ASNDB_TEMP_RIB_FILE','ASNDB_NAMES_FILE']:
        if os.path.exists(current_app.config[handle]):
            stats = os.stat(current_app.config[handle])
            response = {
                "filename" : current_app.config[handle],
                "exists" : True,
                "size_mb" : '{:.2f}'.format((stats.st_size / 1024 / 1024)) ,
                "modified" : (datetime.fromtimestamp(stats.st_mtime)).strftime("%Y-%m-%d %H:%M:%S"),
            }
        else:
            response = {
                "filename" : current_app.config[handle],
                "exists" : False,
                "size_mb" : "",
                "modified" : "",
            }
        file_info[handle] = response

    return file_info

## 
## Lookup functions
##

## Take ASN integer, return ASN Name
def get_asn_name(asn):
    current_app.logger.debug(f"Outside if, looking for {asn}")
    names_file = current_app.config['ASNDB_NAMES_FILE']
    if os.path.isfile(names_file):
        with open(names_file, 'r') as file:
            names = json.load(file)
            if names:
                current_app.logger.debug(f"Looking for {asn}")
                asn_str = str(asn)
                try:
                    response = names[asn_str]
                    return response
                except KeyError:
                    current_app.logger.info(f"ASN LOOKUP - Failed to look up ASN Name for {asn}")
                    return 'ERROR- ASN Name not found in DB'
            else:
                return 'ERROR- ASN Name not found in DB'
    else:
        return 'ERROR- Missing ASN Names file'

## Get ASN of a given IP
def get_asn(ip):
    if os.path.isfile(current_app.config['ASNDB_FILE']):
        asndb = pyasn.pyasn(current_app.config['ASNDB_FILE'])
        asn,bgp = asndb.lookup(ip)
        return asn
    else:
        return 0

## Get subnets in ASN
def get_asn_subnets(asn):
    if os.path.isfile(current_app.config['ASNDB_FILE']):
        asndb = pyasn.pyasn(current_app.config['ASNDB_FILE'])
        current_app.logger.info(f"Looking for subnets for asn:{asn}")
        subnets = asndb.get_as_prefixes(asn)
        return subnets
    else:
        current_app.logger.debug("Didn't find ASNDB file")
        return []

## How many IPs in supplied ASN
def get_asn_ip_count(asn):
    if os.path.isfile(current_app.config['ASNDB_FILE']):
        asndb = pyasn.pyasn(current_app.config['ASNDB_FILE'])
        asn_ip_count = asndb.get_as_size(asn)
        return asn_ip_count
    else:
        return 0

## Take fqdn, return ASN, simple wrapper
def get_asn_for_site(url):
    res = resolver
    ip = res.resolve(url,'A')[0].to_text() # type: ignore
    asn = get_asn(ip)
    return asn

## Lookup full ASN/BGP/Subnet/IP Count info for a given url (should be fqnd)
def get_site_asn_bgp(url):
    if os.path.isfile(current_app.config['ASNDB_FILE']):
        res = resolver
        try:
            ip = res.resolve(url,'A')[0].to_text() # type: ignore
        except:
            current_app.logger.warning(f"ASN INFO - Error resolving {url} to IP")
            ip = '0.0.0.0'

        asndb = pyasn.pyasn(current_app.config['ASNDB_FILE'])
        asn,bgp = asndb.lookup(ip)
        
        current_app.logger.debug(f"Looking for details on asn: {asn}")

        asn_name = get_asn_name(asn)

        if asn_name.startswith("ERROR-"):
            response = {
            'found' : False,
            'asn' : "Error",
            'asn_name' : asn_name,
            'bgp' : "Error",
            'subnet_count' : "Error",
            'asn_ip_count' : "Error",
            }
            return response

        else:
            response = {
                'found' : True,
                'asn' : asn,
                'asn_name' : asn_name,
                'bgp' : bgp,
                'subnet_count' : len(get_asn_subnets(asn)),  # type: ignore
                'asn_ip_count' : get_asn_ip_count(asn),
            }
            return response
 
    ## Missing DB File, nothing we can do here
    else:
        current_app.logger.info(f"ASN LOOKUP - Missing DB File")
        response = {
            'found' : False,
            'asn' : '',
            'asn_name' : '',
            'bgp' : '',
            'subnet_count' : '',
            'asn_ip_count' : '',
        }

    return response

##
## DB Downloader functions
## Will be deliberately made unreachable for shipping, with db file supplied due to download stall issues


@celery.task(bind=True)
def download_asn_db_and_names(self):
    
    ## Download latest RIB data file
    self.update_state(state='PROGRESS', meta={'current_step': '1/3 - DB Download', 'message' : "Downloading..."}) 
    current_app.logger.info("Download start")
    current_app.logger.info(current_app.config['ASNDB_FILE'])
    current_app.logger.info(current_app.config['ASNDB_TEMP_RIB_FILE'])
    current_app.logger.info(current_app.config['ASNDB_NAMES_FILE'])
    db_download = os.system(f"pyasn_util_download.py --latestv4 --filename={current_app.config['ASNDB_TEMP_RIB_FILE']}")

    
    if db_download == 0:
        
        ## Convert RIB to usable format
        self.update_state(state='PROGRESS', meta={'current_step': '2/3 - Converting', 'message' : "Converting..."}) 
        db_convert = os.system(f"pyasn_util_convert.py --single {current_app.config['ASNDB_TEMP_RIB_FILE']} {current_app.config['ASNDB_FILE']} --no-progress")
        if db_convert == 0:
            
            ## Download ASN Names
            self.update_state(state='PROGRESS', meta={'current_step': '3/3 - Names Download', 'message' : "Downloading..."}) 
            names_download = os.system(f"pyasn_util_asnames.py -o {current_app.config['ASNDB_NAMES_FILE']}")
            if names_download == 0:

                ## Finish
                self.update_state(state='PROGRESS', meta={'current_step': 'Completed!', 'message' : "Complete!"})
                return {'current_step': 'Finished!', 'message' : "Complete!"}

    ## Error returns           
            return {'current_step': '3/3 - Names Download', 'message' : "Failed!"}
        else:
            
            return {'current_step': '2/3 - Converting', 'message' : "Failed!"}
    else:
        
        return {'current_step': '1/3 - DB Download', 'message' : "Failed!"}
 



