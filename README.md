## Synclias

[Synclias Docs](https://synclias.pages.dev/)

Best effort routing of sites over a VPN connection for OPNsense routers

In short, we'll take a list of sites you specify, crawl them for links, find out the right IPs and make a firewall alias on the router.
We then repeat the process on a set schedule.

Instantly techy people will say "but that'll break", and yes, it doesn't work for some sites, and any site you can't view over a VPN definitely won't work, but in general, you'll find sites don't move about that often. At home, I run a sync every 24 hours and in 3 months, I've had to manually push the sync button once.


## Docker Hub Image
Easiest way, already built and ready!

Instructions, compose and .env  are on [Docker Hub](https://hub.docker.com/repository/docker/mhenning/synclias/general)

## Clone and Build it yourself
# clone this repo

# copy the env-sample file
cp env-sample-docker .env

# edit the .env file
Set the following:
    MARIADB_USERNAME - Any username you like for the database connection
    MARIADB_PASSWORD - Any password you like
    MARIADB_DATABASE - Any DB you want to use
    ENCRYPTION_KEY - This has to be a 32 char string of upper, lower and numbers (sorry, I know it's a pain, use a password generator)
    SECRET_KEY - Any length, use another string from your password generator

# 

# Run!
docker compose -f docker-compose-build.yaml up

(Add a "-d" to detach afterwards)

Once it's all up and running you should be able to access https://localhost:8000
(Front end proxy coming soon!)

Set a password, configure your router and nameservers, then start adding sites
