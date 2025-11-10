import os

## DB Imports
from synclias import db
import sqlalchemy as sa
import sqlalchemy.orm as so

## Cryptography imports for TDE
import pickle
from cryptography.fernet import Fernet
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import event, text, JSON, DateTime, PickleType, column

# Authentication imports
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional

## Pull in the encryption key from store
encryption_key = os.environ['ENCRYPTION_KEY']


## Definition for Encrypted so allow for transparent data encryption
class Encrypted(sa.TypeDecorator):
    impl = sa.Text
    cache_ok = True

    def __init__(self, encryption_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encryption_key = encryption_key
        self.fernet = Fernet(encryption_key.encode())

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = self.fernet.encrypt(pickle.dumps(value)).decode()
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = pickle.loads(self.fernet.decrypt(value.encode()))
        return value

## DB/Table Classes

class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    role: so.Mapped[str] = so.mapped_column(sa.String(60))
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) # type: ignore


class Site(db.Model):
    __tablename__ = 'Sites'
    id : Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column((sa.String(64)),nullable=False, index=True, unique=True)
    url_group : Mapped[str] = mapped_column((sa.String(64)))
    crawl : Mapped[bool]= mapped_column(default=True, nullable=False)
    override_safety : Mapped[bool] = mapped_column(default=False, nullable=False)
    use_dns_history: Mapped[bool] = mapped_column(default=False, nullable=False)

    def to_json(self):
        return {
            'id' : self.id,
            'url': self.url,
            'url_group' : self.url_group,
            'crawl' : self.crawl,
            'override_safety' : self.override_safety,
            'use_dns_history' : self.use_dns_history,
        }
    
class SafetyKeyword(db.Model):
    __tablename__ = 'SafetyKeywords'
    id : Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column((sa.String(64)),nullable=False)
    exact: Mapped[bool]


    def to_json(self):
        return {
            'id' : self.id,
            'keyword': self.keyword,
            'exact' : self.exact,
        }

class ASN(db.Model):
    __tablename__ = 'ASNs'
    id : Mapped[int] = mapped_column(primary_key=True)
    asn: Mapped[int] = mapped_column(nullable=False) 
    comment : Mapped[str] = mapped_column(sa.String(64))

    def to_json(self):
        return {
            'id' : self.id,
            'asn': self.asn,
            'comment' : self.comment,
        }

##
## If you update Router, YOU MUST update the event listener for table creation, below
##
class Router(db.Model):
    __tablename__ = 'Router'
    id : Mapped[int] = mapped_column(primary_key=True)
    hostname : Mapped[str] = mapped_column(sa.String(64))
    https : Mapped[bool]
    alias : Mapped[str] = mapped_column(sa.String(64))
    ipv6 : Mapped[bool]
    alias_ipv6 : Mapped[str] = mapped_column(sa.String(64))
    verifytls : Mapped[bool]
    apikey : so.Mapped[dict[str, str]] = so.mapped_column(Encrypted(encryption_key))
    apisecret : so.Mapped[dict[str, str]] = so.mapped_column(Encrypted(encryption_key))

    def to_json(self):
        return {
            'hostname' : self.hostname,
            'https' : self.https,
            'alias' : self.alias,
            'ipv6' : self.ipv6,
            'alias_ipv6' : self.alias_ipv6,
            'verifytls' : self.verifytls,
            'apikey' : self.apikey,
            'apisecret' : self.apisecret,
        }

## Insert a row on table creation to store the data we care about
@event.listens_for(Router.__table__, 'after_create') # type: ignore
def create_router(target, connection, *args, **kwargs):
    
    # Can't just store "blank", need to encrypt it with a key or the site gets very angry
    f = Fernet(encryption_key)
    enc_blank = f.encrypt(pickle.dumps("Blank")).decode()
    insert = f'INSERT INTO `Router` (`id`, `hostname`, `https`, `alias`, `ipv6`, `alias_ipv6`, `verifytls`, `apikey`, `apisecret`) VALUES (1,"router",0,"alias",0,"alias_ipv6",0,"{enc_blank}","{enc_blank}");'
    connection.execute(text(insert))


class Nameserver(db.Model):
    __tablename__ = 'Nameservers'
    id : Mapped[int] = mapped_column(primary_key=True)
    hostname : Mapped[str] = mapped_column(sa.String(64))
    https : Mapped[bool] 
    port : Mapped[int]
    verifytls : Mapped[bool]
    token : so.Mapped[dict[str, str]] = so.mapped_column(Encrypted(encryption_key))
    type : Mapped[str] = mapped_column((sa.String(64)),default="standard_ns")

    def to_json(self):
        return {
            'hostname' : self.hostname,
            'https' : self.https,
            'type' : self.type,
            'port' : self.port,
            'verifytls' : self.verifytls,
            'token' : self.token,
        }

##
## If you update Prefs, YOU MUST update the event listener for table creation, below
##
class Prefs(db.Model):
    __tablename__ = 'Prefs'
    id : Mapped[int] = mapped_column(primary_key=True)
    autosync : Mapped[bool] = mapped_column(default=False, nullable=False)
    sync_every : Mapped[int] = mapped_column(default=24, nullable=False)
    autoasndb : Mapped[bool] = mapped_column(default=False, nullable=False)
    asndb_every : Mapped[int] = mapped_column(default=30, nullable=False)
    purgedns : Mapped[bool] = mapped_column(default=True, nullable=False)
    user_agent : Mapped[str] = mapped_column(sa.String(128), default = '')
    global_dns_history : Mapped[bool] = mapped_column(default=False, nullable=False)
    flush_states : Mapped[bool] = mapped_column(default=False, nullable=False)
    keep_dns_days : Mapped[int] = mapped_column(default=30, nullable=False)

    def to_json(self):
        return {
            'id' : self.id,
            'autosync' : self.autosync,
            'sync_every' : self.sync_every,
            'autoasndb' : self.autoasndb,
            'asndb_every' : self.asndb_every,
            'purgedns' : self.purgedns,
            'user_agent' : self.user_agent,
            'global_dns_history' : self.global_dns_history,
            'flush_states' : self.flush_states,
            'keep_dns_days' : self.keep_dns_days,
        }


## Insert a row on table creation to store the data we care about
@db.event.listens_for(Prefs.__table__, 'after_create') # type: ignore
def create_prefs(target, connection, *args, **kwargs):
    insert_text = "INSERT INTO `Prefs` (`id`, `autosync`, `sync_every`, `autoasndb`, `asndb_every`, `purgedns`, `user_agent`,`global_dns_history` ,`flush_states`, `keep_dns_days`)"
    values_text = "VALUES (1,0,24,0,30,1,'',0,0,30);"
    connection.execute(text(insert_text + " " + values_text)
    ## Need to replace the lines above with default values in model, but the DB doesn't like "default, server default" etc, TODO
    # insert_text = "INSERT INTO `Prefs` () VALUES ()"
    # connection.execute(text(insert_text)
    )

class Result(db.Model):
    __tablename__ = 'Results'
    id : Mapped[int] = mapped_column(primary_key=True)
    changes : Mapped[int]
    timestamp : Mapped[str] = mapped_column(DateTime)
    result_pickle : Mapped[str] = mapped_column(PickleType)

    def to_json(self):
            return {
                'id' : self.id,
                'changes' : self.changes,
                'timestamp' : self.timestamp,
                'result_pickle' : self.result_pickle,
            }
    
class IPRecord(db.Model):
    __tablename__ = 'ip_records'
    id : Mapped[int] = mapped_column(primary_key=True)
    fqdn : Mapped[str] = mapped_column(sa.String(64), index=True)  ## Yes, this should really be a foreign key
    record: Mapped[str] = mapped_column(sa.String(40))
    record_type: Mapped[int]
    last_seen: Mapped[str] = mapped_column(DateTime)

    def to_json(self):
        return {
            'id' : self.id,
            'fqdn' : self.fqdn,
            'record' : self.record,
            'last_seen' : self.last_seen
        }
    


