import os
import sys
from str_to_bool import str_to_bool


class Config(object):
    FLASK_ENV = 'development'
    TESTING = False

    # Determine the folder of the top-level directory of this project
    BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__),os.path.pardir))
    SECRET_KEY = os.environ["SECRET_KEY"]
    ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]
    DEBUG = bool(str_to_bool(os.getenv("FLASK_DEBUG", "False")))

    ## Set a cache directory for tldextract (docker user has no homedir)
    os.environ["TLDEXTRACT_CACHE"] = BASEDIR + "/cache/tldcache"
    if not os.path.exists(os.environ["TLDEXTRACT_CACHE"]):
        os.makedirs(os.environ["TLDEXTRACT_CACHE"])

    ## Site to use for DNS query testing
    DNS_CHECK_DOMAIN='www.google.com'

    ## List of Safety Keywords to import on "Import Suggestions"
    KEYWORD_SUGGESTIONS = ['google','youtube','apple','microsoft','facebook','twitter','linkedin',
                           'amazon','temu','netflix','cloudfront','tiktok','whatsapp','yahoo','pinterest','twitch','telegram','bing','duckduckgo',
                           'ebay','instagram','chatgpt','discord','reddit','zoom.co']
    KEYWORD_SUGGESTIONS_EXACT = ['x.com']

    ## IP address to use for testing add/remove to aliases
    #  This is only used if the alias is empty
    ADD_REMOVE_TEST_IP='10.200.200.200'

    # DBs
    MARIADB_USER = os.getenv("MARIADB_USER")
    MARIADB_PASSWORD = os.getenv('MARIADB_PASSWORD')
    MARIADB_DATABASE = os.getenv('MARIADB_DATABASE')
    MARIADB_HOSTNAME = os.getenv("MARIADB_HOSTNAME", "db")

    if not MARIADB_USER or not MARIADB_PASSWORD or not MARIADB_DATABASE:
        try:
            sys.exit("Missing Database Connection Details")
        except SystemExit as message:
            print(message)

    SQLALCHEMY_DATABASE_URI = 'mariadb+pymysql://' + MARIADB_USER + ':' + MARIADB_PASSWORD + '@' + MARIADB_HOSTNAME +'/' + MARIADB_DATABASE + '?charset=utf8mb4' # type: ignore
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis.
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redbeat_redis_url = REDIS_URL

    # Celery.
    CELERY_CONFIG = {
        "broker_url": REDIS_URL,
        "result_backend": REDIS_URL,
        "include": ["synclias.blueprints.technitium.tasks",
                    "synclias.blueprints.opnsense.tasks",
                    "synclias.blueprints.asndb.tasks",
                    "synclias.blueprints.syncer.tasks",
                    "synclias.blueprints.scheduler.tasks",
                    "synclias.blueprints.standard_ns.tasks",
                    "synclias.blueprints.ip_history.tasks",
                    ],
        "beat_schedule": {
            'dns_history_15mins': {
                'task': 'synclias.blueprints.ip_history.tasks.update_all_dns_history',
                'schedule': 900,
                #'args': []
            },
            'check_dns_old_records_hourly': { ## Calls the script to check every hour, deletion window (e.g 7 days) is controlled by app settings
                'task': 'synclias.blueprints.ip_history.tasks.clear_dns_history_days',
                'schedule': 3600,
                #'args': []
            },            
	    'ensure_auto_tasks_exist_21_mins': { ## Calls the script to check every hour, deletion window (e.g 7 days) is controlled by app settings
                'task': 'synclias.blueprints.scheduler.tasks.ensure_auto_tasks_exist',
                'schedule': 1260,
                #'args': []
            },
        }
    }

    ASNDB_PATH = BASEDIR + "/shared"
    ## ASN DB Files
    ASNDB_FILE = ASNDB_PATH + '/asn_db'
    ## ASNDB Needs to download a temporary "rib" file, converts to db file
    ASNDB_TEMP_RIB_FILE = ASNDB_PATH + '/latest.rib'
    ASNDB_NAMES_FILE = ASNDB_PATH + '/asn_names'


class ProductionConfig(Config):
    FLASK_ENV = 'production'
    ASNDB_TEMP_RIB_FILE = 'latest-prod.rib'


class DevelopmentConfig(Config):
    DEBUG = True
    ASNDB_TEMP_RIB_FILE = 'latest-dev.rib'

class TestingConfig(Config):
    TESTING = True
    ASNDB_TEMP_RIB_FILE = 'latest-test.rib'
    SQLALCHEMY_DATABASE_URI = "mariadb+pymysql://testing:testing@localhost:3307/synclias?charset=utf8mb4"
    ENCRYPTION_KEY='C1NEbwlzAZULxTuxX-XCSOC994lUCG3_Y3Em_ZhchhI='
    SECRET_KEY='uG6onGkXEiewBiWUf9DS4_LF60wDkNSc62dL2WL1Wl8='
    WTF_CSRF_ENABLED = False



