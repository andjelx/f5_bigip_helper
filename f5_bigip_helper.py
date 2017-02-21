#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Invoke:
$ python script.py [-b base_config.yml] config.yml [--clean]
clean - will delete all objects cpecified in config
config.yml parameters will be applied over base_config.yml if exists


Tested with python >= 3.5
Author: Andrey Zhelnin
Version: 0.2
"""

from f5.bigip import BigIP
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import sys
import yaml
import argparse


# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_params(config):
    if 'params' in config:
        return { x: config['params'][x] for x in config['params'] }
    else:
        return {}

def main():

    # parsing agrs
    parser = argparse.ArgumentParser(description='Automatic BigIP F5 config creation')
    parser.add_argument("config", help="specify config file, e.g. config.yml")
    parser.add_argument("-b", "--baseconfig", help="specify base config file, e.g. base_config.yml")
    parser.add_argument("--clean", help="delete all objects cpecified in config",
                        action="store_true")
    args = parser.parse_args()

    with open(args.config, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    if args.baseconfig:
        with open(args.baseconfig, 'r') as ymlfile:
            base_cfg = yaml.load(ymlfile)
    else:
        base_cfg = {}

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
    # Get VIP name & pool names
    vip_name = cfg['vip']['name']
    vip_prefix = ''.join(vip_name.split('-')[:-1])
    nodes_ports = []
    for n in cfg['nodes']:
        nodes_ports.append(cfg['nodes'][n]['port'])
    pool_name = "P-{}-{}".format(vip_prefix, nodes_ports[0])
    if not args.clean:
        # Create pool
        try:
            print("Creating pool: %s" % pool_name)
            # https://devcentral.f5.com/wiki/iControlREST.APIRef_tm_ltm_pool.ashx
            cfg_pool_params = { x: cfg['pool']['params'][x] for x in cfg['pool']['params'] }
            base_pool_params = { x: base_cfg['pool']['params'][x] for x in base_cfg['pool']['params'] }
            pool_params = {**base_pool_params, **cfg_pool_params}
            pool_id = create_pool(name=pool_name, partition=partition,
                        description=description, **pool_params)
            print()
        except:
            pool_id = bigip.ltm.pools.pool.load(partition=partition, name=pool_name)
                             
        # Create nodes
        pool_members = []
        for node in cfg['nodes']:
            # Create node only if required
            if cfg['nodes'][node]['exists'].upper() != 'Y':
                print("Creating node: %s" % node)
                create_node(name=node, partition=partition,
                        description=description,
                        address=cfg['nodes'][node]['address'])

            print("Adding %s as pool member to %s" % (node, pool_name))
            cfg_pool_params = get_params(cfg['nodes'][node])
            #{ x: cfg['nodes'][node]['params'][x] for x in cfg['nodes'][node]['params'] }
            base_pool_params = { x: base_cfg['node']['params'][x] for x in base_cfg['node']['params'] }
            pool_params = {**base_pool_params, **cfg_pool_params}
            pool_m_name = "%s:%s" % (node, cfg['nodes'][node]['port'])
            pool_params['name'] = pool_m_name
            pool_params['partition'] = partition
            pool_member = create_pool_member(pool_id, pool_params)
            pool_members.append(pool_member)
            print()

        # Create Virtual server
        # https://devcentral.f5.com/wiki/iControlREST.APIRef_tm_ltm_virtual.ashx
        print("Creating Virtual server: %s" % vip_name)
        cfg_vip_params = { x: cfg['vip']['params'][x] for x in cfg['vip']['params'] }
        base_vip_params = { x: base_cfg['vip']['params'][x] for x in base_cfg['vip']['params'] }
        vip_params = {**base_vip_params, **cfg_vip_params}
        destination = "%s:%s" % (cfg['vip']['destination'], cfg['vip']['port'])
        vip_id = create_vip(name=vip_name, partition=partition,
                description=description, destination=destination,
                pool=pool_name, vlansEnabled=True,
                **vip_params)
      
    else:
        print("Cleaning up")
        if bigip.ltm.virtuals.virtual.exists(partition=partition, name=vip_name):
            print("Deleting Virtual Server %s" % vip_name)
            vip = bigip.ltm.virtuals.virtual.load(partition=partition, name=vip_name)
            vip.delete()

        if bigip.ltm.pools.pool.exists(partition=partition, name=pool_name):
            print("Deleting pool %s" % pool_name)
            pool = bigip.ltm.pools.pool.load(partition=partition, name=pool_name)
            pool.delete()

        for node in cfg['nodes']:
            if bigip.ltm.nodes.node.exists(partition=partition, name=node) and \
                   cfg['nodes'][node]['exists'].upper() != 'Y':
                node_id = bigip.ltm.nodes.node.load(partition=partition, name=node)
                print("Deleting node %s" % node)
                node_id.delete()
    
if __name__ == "__main__":
    # execute only if run as a script
    sys.exit(main())
