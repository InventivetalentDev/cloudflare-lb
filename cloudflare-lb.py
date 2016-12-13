#!/usr/bin/env python

import json
import time
import random
from urllib.request import urlopen
import requests

HOSTS = [
    ['127.0.0.1', 'A'],
    ['127.0.0.2', 'A'],
    ['127.0.0.3', 'A'],
    ['127.0.0.4', 'A'],
    ['127.0.0.5', 'A']
]  # Your A/AAAA value, i.e. 192.168.1.10
PROTO = 'http'  # http or https
PORT = 80  # Defaults to port 80
EMAIL = ''  # Your CloudFlare email address
API = ''  # Your CloudFlare client API key found at https://www.cloudflare.com/my-account
RECORD = 'lb.example.com'  # where you want the load balancer
ZONE = 'example.com'  # Name of the Zone you want to edit (typically the domain name)
DOMAIN = 'example.com'  # Use DOMAIN if this is for the root domain
TTL = 1  # Set TTL
INTERVAL = 60  # how long we wait between runs

ZONE_ID = ''
RECS = []  # RECORDS


def call_api(route, params, method="GET"):
    url = "https://api.cloudflare.com/client/v4" + route
    headers = {
        "X-Auth-Email": EMAIL,
        "X-Auth-Key": API,
        "Content-Type": "application/json",
        "User-Agent": "Cloudflare-LoadBalancer"
    }

    response = requests.request(method=method, url=url, params=params, headers=headers)

    return json.loads(response.text)


def get_zone(name):
    print("\nLooking up zone with name " + name + "...")
    zones = call_api("/zones", {"name": DOMAIN, "status": "active"})
    print(zones)
    if len(zones['result']) == 0:
        print("\nCouldn't find any zones")
        return False

    elif len(zones['result']) == 1:
        zone = zones['result'][0]
        print("\nFound zone '" + zone['name'] + "' with id '" + zone['id'] + "'")
        return zone['id']


def get_recs(zone_id):
    print("\nLoading DNS records")
    rec = call_api("/zones/" + zone_id + "/dns_records", {"name": DOMAIN, "per_page": 100})
    print(rec)
    if rec['success']:
        print(rec['result'])
        return rec['result']
    else:
        return False


def get_rec(zone_id, name, type, content):
    print("\nLooking up " + type + " record '" + name + "' with '" + content + "'")
    rec = call_api("/zones/" + zone_id + "/dns_records", {"name": name, "content": content, "type": type})
    print(rec)
    if rec['success']:
        print(rec['result'])
        return rec['result']
    else:
        return False


def del_rec(zone_id, rec_id, host):
    result = call_api("/zones/" + zone_id + "/dns_record/" + rec_id, {}, "DELETE")
    if result['success']:
        print('Removing:' + host)
    else:
        print('Remove Failed: ' + host + '. ')
        print(result['messages'])


def add_rec(rec):
    result_add = call_api("/zones", {"name": RECORD, "content": rec[0], "type": rec[1]}, "POST")
    if result_add['success']:
        # TODO: maybe modify the "orange cloud" if needed
        return True

    print('Add Failed: {0}.'.format(rec[0]))
    print(result_add['messages'])
    return False


def healthcheck(host):
    # TODO: add IP exception to Cloudflare firewall
    try:
        url = "{0}://{1}:{2}/".format(PROTO, host[0], str(PORT))
        print("\nTesting connection to " + url)
        req = requests.Request(method="GET", url=url, headers={"User-Agent": "Cloudflare-LoadBalancer"})
        r = req.prepare()
        session = requests.session()
        session.send(r)
        print("-> ONLINE")
        if not get_rec(ZONE_ID, RECORD, host[1], host[0]):  # needs to be added
            add_rec(host)
        else:
            print(host[0] + ': Passed')
    except IOError as err:  # we were not able to do what was needed
        print("-> OFFLINE", err)
        rec = get_rec(ZONE_ID, RECORD, host[1], host[0])[0]  # get the id of the record (this SHOULD only return one record)
        rec_id = rec['id']
        if rec_id is not False:
            print(host[0] + ': Removing Host')
            del_rec(ZONE_ID, rec_id, host[0])
        else:
            print(host[0] + ': Still dead')


def get_rec_id(name, host):
    for rec in RECS:
        if rec['name'] == name and rec['content'] == host and (rec['type'] == "A" or rec['type'] == "AAAA"):
            return rec['id']
    return False


if __name__ == "__main__":
    while True:
        ZONE_ID = get_zone(ZONE)
        RECS = get_recs(ZONE_ID)
        start_time = time.time()
        random.shuffle(HOSTS)

        for host in HOSTS:
            healthcheck(host)

        if INTERVAL >= 0:
            lapse = int(time.time() - start_time)
            print("DONE: sleeping for {0} seconds".format(str(INTERVAL - lapse)))
            time.sleep(INTERVAL - lapse)  # sleep for some set time seconds
        else:
            exit()
