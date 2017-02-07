#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Invoke:
$ python script.py config.yml [clean]
clean - will delete all objects cpecified in config

Tested with python >= 3.5
Created: Andrey Zhelnin
Version: 0.1
"""

from f5.bigip import BigIP
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import sys
import yaml


# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

if len(sys.argv) <= 1:
    print("You must specify config file, e.g. config.yml")
    sys.exit(1)
else:
    cfile = sys.argv[1]

CLEAN = False
if len(sys.argv) > 2 and 'clean' in sys.argv[2]:
    CLEAN = True

with open(cfile, 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

# Reload credentials from config
cfg['bigip'] = {
      'ip': '192.168.1.245',
      'user': 'restapi',
      'password': 'password'
}

partition = cfg['partition']['name']
# Connect to the BigIP
bigip = BigIP(cfg['bigip']['ip'],cfg['bigip']['user'],cfg['bigip']['password'])

# Create a new vip
def create_vip(**kwargs):
    myvip = bigip.ltm.virtuals.virtual.create(**kwargs)
    return myvip


# Create a new pool
def create_pool(**kwargs):
    mypool = bigip.ltm.pools.pool.create(**kwargs)
    return mypool

# Create new node
def create_node(**kwargs):
    mynode = bigip.ltm.nodes.node.create(**kwargs)
    return mynode
    
# Create new pool member
def create_pool_member(pool_id, params):
    pool_member = pool_id.members_s.members.create(**params)
    return pool_member


description = "Created according to %s" % cfg['change']
if not CLEAN:
    # Create pool
    try:
        print("Creating pool: %s" % cfg['pool']['name'])
        # https://devcentral.f5.com/wiki/iControlREST.APIRef_tm_ltm_pool.ashx
        pool_params = { x: cfg['pool']['params'][x] for x in cfg['pool']['params'] }
        pool_id = create_pool(name=cfg['pool']['name'], partition=partition,
                    description=description, **pool_params)
        print()
    except:
        pool_id = bigip.ltm.pools.pool.load(partition=partition, name=cfg['pool']['name'])
                         
    # Create nodes
    pool_members = []
    for node in cfg['nodes']:
        # Create node only if required
        if cfg['nodes'][node]['exists'].upper() != 'Y':
            print("Creating node: %s" % node)
            create_node(name=node, partition=partition,
                    description=description,
                    address=cfg['nodes'][node]['address'])

        print("Adding %s as pool member to %s" % (node, cfg['pool']['name']))
        pool_params = { x: cfg['nodes'][node]['params'][x] for x in cfg['nodes'][node]['params'] }
        pool_m_name = "%s:%s" % (node, cfg['nodes'][node]['port'])
        pool_params['name'] = pool_m_name
        pool_params['partition'] = partition
        pool_member = create_pool_member(pool_id, pool_params)
        pool_members.append(pool_member)
        print()

    # Create Virtual server
    # https://devcentral.f5.com/wiki/iControlREST.APIRef_tm_ltm_virtual.ashx
    print("Creating Virtual server: %s" % cfg['vip']['name'])
    vip_params = { x: cfg['vip']['params'][x] for x in cfg['vip']['params'] }
    destination = "%s:%s" % (cfg['vip']['destination'], cfg['vip']['port'])
    vip_id = create_vip(name=cfg['vip']['name'], partition=partition,
            description=description, destination=destination,
            pool=cfg['pool']['name'], vlansEnabled=True,
            **vip_params)
  
else:
    print("Cleaning up")
    if bigip.ltm.virtuals.virtual.exists(partition=partition, name=cfg['vip']['name']):
        print("Deleting Virtual Server %s" % cfg['vip']['name'])
        vip = bigip.ltm.virtuals.virtual.load(partition=partition, name=cfg['vip']['name'])
        vip.delete()

    if bigip.ltm.pools.pool.exists(partition=partition, name=cfg['pool']['name']):
        print("Deleting pool %s" % cfg['pool']['name'])
        pool = bigip.ltm.pools.pool.load(partition=partition, name=cfg['pool']['name'])
        pool.delete()

    for node in cfg['nodes']:
        if bigip.ltm.nodes.node.exists(partition=partition, name=node) and \
               cfg['nodes'][node]['exists'].upper() != 'Y':
            node_id = bigip.ltm.nodes.node.load(partition=partition, name=node)
            print("Deleting node %s" % node)
            node_id.delete()
    
