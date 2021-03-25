#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import re
import os
import sys
import json
import time
import copy
import argparse
import tempfile
import subprocess

from threading import Thread


threads = {}
results = {}

vmcmd_clone  = 'VBoxManage clonevm {} --name {}_{} --mode machine --options keephwuuids --register'
vmcmd_delete = 'VBoxManage unregistervm {}_{} --delete'
vmcmd_getuid = 'VBoxManage showvminfo {} | grep "^SATA" | sed -e "s/.*UUID: \([^)]*\))/\\1/"'
vmcmd_setuid = 'VBoxManage internalcommands sethduuid {} | grep "UUID changed to:" | sed -e "s/.*: //"'
vmcmd_start  = 'VBoxManage startvm {}_{} --type headless'
vmcmd_acpi   = 'VBoxManage controlvm {}_{} acpipowerbutton'
vmcmd_halt   = 'VBoxManage controlvm {}_{} poweroff'

patch_cmd    = None


# ---------------------------------------------------------------------------------------

def parse_config(conf_file):

    #
    # Read the nodes.
    #
    with open(conf_file) as fd:
        configuration = json.load(fd)

    nodes = []
    gcid_map = {}
    for node_type in configuration['Nodes']:
        for name,profile in configuration['Nodes'][node_type].items():
            host_name = profile[0]
            nodes.append((name, node_type, host_name))

            for gcid in profile[-1]:
                gcid_map[int(gcid,0)] = profile[1]

    #
    # And the connections.
    #
    connections = configuration['Connections']

    #
    # And the constants.
    #
    constants = configuration['Constants']

    #
    # Get the GCID <-> topoID mappings.
    #
    return nodes, connections, constants, gcid_map


# ---------------------------------------------------------------------------------------

def wait(seconds, reason):
    print(reason, end=' ')
    for i in range(seconds):
        print('.', end='')
        sys.stdout.flush()
        time.sleep(1)

    print()


def run(cmd):
    process = os.popen(cmd)
    output = process.read()
    process.close()

    return output


# ----------------------------------------------------------------------------------------------------------------------

def scp(address, local_filename, remote_filename):
    cmd = ['scp',
           '-o', 'UserKnownHostsFile=/dev/null',        # removes warning messages
           '-o', 'StrictHostKeyChecking=no',            # removes warning messages
           '-q',
           '-r', local_filename,
           'tc@{}:{}'.format(address, remote_filename)]

    subprocess.Popen(cmd, stderr=subprocess.DEVNULL).wait()


def ssh(address, cmd_params):
    cmd = ['ssh',
           '-o', 'UserKnownHostsFile=/dev/null',        # removes warning messages
           '-o', 'StrictHostKeyChecking=no',            # removes warning messages
           'tc@{}'.format(address)] + cmd_params

    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return True, output.decode('utf-8')
    except:
        return False, ''

# ----------------------------------------------------------------------------------------------------------------------

def verify_active(node_name, host_name):
    status, output = ssh(host_name, ['whoami'])
    results[node_name] = status and output.startswith('tc')


def active_vms(nodes):
    results.clear()
    threads.clear()

    for node_name,node_type,node_addr in nodes:
        results[node_name] = 'Not Available'
        threads[node_name] = Thread(target=verify_active, args=[node_name, node_addr], daemon=True)

    for node_name,t in threads.items():
        t.start()

    for node_name,t in threads.items():
        t.join(timeout=60.0)
        if t.is_alive():
            print(node_name, 'is still alive')

    return results

# ---------------------------------------------------------------------------------------

#
# Clone the VMs.
#
def clone_vms(nodes):
    for node_name,node_type,node_addr in nodes:
        print('cloning {} : '.format(node_name), end='')
        sys.stdout.flush()
        cmd = vmcmd_clone.format(base_name, base_name, node_name)
        run(cmd)

# ---------------------------------------------------------------------------------------

#
# Remove the VMs.
#
def delete_vms(nodes):
    for node_name,node_type,node_addr in nodes:
        print('deleting {} : '.format(node_name), end='')
        sys.stdout.flush()
        cmd = vmcmd_delete.format(base_name, node_name)
        run(cmd)

# ---------------------------------------------------------------------------------------

#
# Patch the VMs.
#
def patch_vms(nodes):
    args = []
    cmd = patch_cmd

    for node_name,node_type,node_addr in nodes:
        cmd += '{},{},{} '.format(node_name, node_type, node_addr)

    os.system(cmd)

    #
    # Redo the UUIDs.
    #
    for node_name,node_type,node_addr in nodes:
        vm_name = '{}_{}'.format(base_name, node_name)
        vdi_name = '{}/{}.vdi'.format(vm_name, vm_name, node_name)
        vbox_name = '{}/{}.vbox'.format(vm_name, vm_name, node_name)

        cmd = vmcmd_getuid.format(vm_name)
        old_uuid = run(cmd).rstrip()

        cmd = vmcmd_setuid.format(vdi_name)
        new_uuid = run(cmd).rstrip()

        print('patching {} : {} -> {}'.format(node_name, old_uuid, new_uuid))

        with open('{}'.format(vbox_name), 'r+') as f:
            s = f.read()
            f.seek(0)
            s = s.replace(old_uuid, new_uuid)
            f.write(s)
            f.truncate()

# ---------------------------------------------------------------------------------------

#
# Start the VMs.
#
def boot_vms(nodes):

    if len(nodes) > 0:
        for node_name,node_type,node_addr in nodes:
            print('booting {}'.format(node_name))
            cmd = vmcmd_start.format(base_name, node_name)
            run(cmd)
            time.sleep(1)

        wait(30, 'waiting 30 seconds for nodes to boot')

        results = active_vms(nodes)
        reboot_nodes = [ t for t in nodes if not results.get(t[0]) ]

        if len(reboot_nodes) > 0:
            print('{} are unresponsive, trying to reboot'.format(', '.join([t[0] for t in reboot_nodes])))
            time.sleep(5)
            halt_vms(reboot_nodes)
            boot_vms(reboot_nodes)

# ---------------------------------------------------------------------------------------

#
# Halt the VMs.
#
def halt_vms(nodes):
    for node_name,node_type,node_addr in nodes:
        print('halting {}'.format(node_name))
        cmd = vmcmd_acpi.format(base_name, node_name)
        run(cmd)

    wait(15, 'waiting for nodes to quiesce')

    for node_name,node_type,node_addr in nodes:
        print('powering down {} : '.format(node_name), end='')
        sys.stdout.flush()
        cmd = vmcmd_halt.format(base_name, node_name)
        run(cmd)

    cmd = 'ps aux | grep VBoxHeadless | grep -v grep | sed -e "s/.*--comment [^_]*_\([^ ]*\).*/\\1/"'
    running_count = 1
    while running_count != 0:
        time.sleep(2)
        running_nodes = run(cmd).rstrip().split('\n')
        running_count = sum(1 if node_name in running_nodes else 0 for node_name,node_type,node_addr in nodes)
        for node_name,node_type,node_addr in nodes:
            if node_name in running_nodes:
                print('{} still running'.format(node_name))

# ---------------------------------------------------------------------------------------

#
# Run the firmware load.
#
def start_vms(nodes):

    #
    # Transfer the node data to the node.
    #
    for node_name,node_type,node_addr in nodes:
        print('starting {}'.format(node_addr))
        ssh(node_addr, ['./mpsim/mpstart'])

# ---------------------------------------------------------------------------------------

#
# Run the firmware load.
#
def stop_vms(nodes):

    #
    # Transfer the node data to the node.
    #
    for node_name,node_type,node_addr in nodes:
        print('stopping {}'.format(node_addr))
        ssh(node_addr, ['./mpsim/mpstop'])

# ---------------------------------------------------------------------------------------

#
# Load the MPsim personality.
#
def load_vms(nodes):

    #
    # Read the ZFM file line by line.  Strip out the comments and then split the line into key and value.
    #
    zfm_config_file = os.path.join(image_dir, 'zfm.conf')
    zfm_configuration = {}

    with open(zfm_config_file) as f:
        for line in f:
            kv_line, _, comment = line.partition('#')
            kv_line = kv_line.strip()
            try:
                key, value = kv_line.split()
                zfm_configuration[key] = value
            except:
                print('invalid line: {}'.format(kv_line))

    switch_config_file  = zfm_configuration['zfm_switch_node_file']
    compute_config_file = zfm_configuration['zfm_compute_node_file']
    memory_config_file  = zfm_configuration['zfm_memory_node_file']
    io_config_file      = zfm_configuration['zfm_io_node_file']

    #
    # Transfer the profile and attributes to the nodes.
    #
    personalities = {}

    for filename in [switch_config_file, compute_config_file, memory_config_file, io_config_file]:
        with open(filename) as f:
            node_profiles = json.load(f)
            for name, profile in node_profiles.items():
                with open(profile['attributes']) as f:
                    attributes = json.load(f)

                personalities[name] = { 'profile'    : profile,
                                        'attributes' : attributes,
                                        'constants'  : constants,
                                        'gcidmap'    : gcid_map,
                                        'remote'     : [] }

    #
    # Determine the link connections.
    #
    for src,dst in connections.items():
        src_name, src_port = src.split(',')
        dst_name, dst_port = dst.split(',')

        src_node = personalities[src_name]
        dst_node = personalities[dst_name]

        src_addr = src_node['profile']['address'].split(':')[0]
        dst_addr = dst_node['profile']['address'].split(':')[0]

        src_tid = src_node['profile']['TopoID']
        dst_tid = dst_node['profile']['TopoID']

        src_gcids = src_node['profile']['GCIDs']
        dst_gcids = dst_node['profile']['GCIDs']

        src_node['remote'].append((int(src_port), dst_addr, int(dst_port), dst_tid, dst_gcids))
        dst_node['remote'].append((int(dst_port), src_addr, int(src_port), src_tid, src_gcids))

    #
    # Transfer the node data to the node.
    #
    for node_name,node_type,node_addr in nodes:
        print('transferring data to {}'.format(node_addr))

        data = personalities[node_name]
        _, tmp_filename = tempfile.mkstemp()
        with open(tmp_filename, 'w') as f:
            f.write(json.dumps(data, indent=4, sort_keys=True))

        ssh(node_addr, ['rm', '-rf', base_name])
        ssh(node_addr, ['mkdir', base_name])
        scp(node_addr, tmp_filename, '{}/profile'.format(base_name))
        os.remove(tmp_filename)

# ---------------------------------------------------------------------------------------

#
# Update the firmware.
#
def update_vms(nodes):

    for node_name,node_type,node_addr in nodes:
        print('updating {}'.format(node_name))
        ssh(node_addr, ['rm', '-rf', 'mpsim'])
        scp(node_addr, mp_dir, 'mpsim')

# ---------------------------------------------------------------------------------------

#
# Check that the VMs are running.
#
def status_vms(nodes):

    results = active_vms(nodes)
    for node_name,node_type,node_addr in nodes:
        if node_name in results:
            print(node_name, results[node_name])
        else:
            print(node_name, 'Unknown')

# ---------------------------------------------------------------------------------------

vm_functions = { 'clone'  : clone_vms,          # clone the base VM
                 'delete' : delete_vms,         # delete the VMs
                 'patch'  : patch_vms,          # patch the personality file
                 'boot'   : boot_vms,           # boot the VMs
                 'halt'   : halt_vms,           # halt the VMs
                 'load'   : load_vms,           # load the MPsim profile and attributes
                 'update' : update_vms,         # update the MPsim python files
                 'start'  : start_vms,          # start the MPsim software
                 'stop'   : stop_vms,           # stop the MPsim software
                 'status' : status_vms,         # show VM status
}


if __name__ == '__main__':

    function_choices = list(vm_functions.keys())

    parser = argparse.ArgumentParser(description='VM creator')
    parser.add_argument('-c', '--config',   help='original config file',  required=True)
    parser.add_argument('-e', '--env',      help='environmental file',    required=True)
    parser.add_argument('-d', '--dir',      help='image directory',       required=False,  default=os.getcwd())
    parser.add_argument('-v', '--vmdir',    help='VM directory',          required=False,  default=os.getcwd())
    parser.add_argument('-m', '--mpdir',    help='MPsim directory',       required=False,  default=os.getcwd())
    parser.add_argument('-f', '--function', help='action to perform',     required=True)
    parser.add_argument('nodes',                                                              nargs='*')
    args = vars(parser.parse_args())

    #
    # We assume that the configuration filename ends with '.conf'
    #
    cwd = os.getcwd()

    image_dir  = args['dir']
    if not os.path.isabs(image_dir):
        image_dir = os.path.join(cwd, image_dir)

    vm_dir = args['vmdir']
    if not os.path.isabs(vm_dir):
        vm_dir = os.path.join(cwd, vm_dir)

    mp_dir = args['mpdir']
    if not os.path.isabs(mp_dir):
        mp_dir = os.path.join(cwd, mp_dir)

    env_file = args['env']
    if not os.path.isabs(env_file):
        env_file = os.path.join(cwd, env_file)

    config_file = args['config']
    base_name = config_file.split('/')[-1].split('.')[0]
    base_vdi   = '{}/{}.vdi'.format(base_name, base_name)

    patch_cmd = 'vdi_patch -b {} -v {} -e {} '.format(base_name, vm_dir, env_file)

    #
    # Check that all of the requested functions are valid.
    #
    functions = args['function'].split(',')
    if not set(functions).issubset(vm_functions.keys()):
        print('invalid -f parameter : {}'.format(args['function']))
        print('possible values are {}'.format(vm_functions.keys()))
        sys.exit(0)

    #
    # Get the list of nodes to operate on. Pare it down to what was requested.
    #
    nodes, connections, constants, gcid_map = parse_config(args['config'])
    if args['nodes']:
        node_names = [ t[0] for t in nodes ]
        for n in args['nodes']:
            if n not in node_names:
                print('unknown node specified - skipping {}'.format(n))

        new_nodes = []
        for t in nodes:
            if t[0] in args['nodes']:
                new_nodes.append(t)

        nodes = new_nodes

    #
    # Chdir to the VM directory.
    #
    try:
        os.chdir(vm_dir)
    except:
        print('{} is not accessible', vm_dir)
        sys.exit(1)

    #
    # Let's do it.
    #
    try:
        for f in functions:
            vm_functions[f](nodes)
    except KeyboardInterrupt:
        sys.exit(1)

