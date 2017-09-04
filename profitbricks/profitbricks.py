#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '1.0'}

DOCUMENTATION = '''
---
module: profitbricks
short_description: Create, destroy, start, stop, and reboot a ProfitBricks virtual machine.
description:
     - Create, destroy, update, start, stop, and reboot a ProfitBricks virtual machine. When the virtual machine is created it can optionally wait for it to be 'running' before returning.
version_added: "2.0"
options:
  auto_increment:
    description:
      - Whether or not to increment a single number in the name for created virtual machines.
    default: yes
    choices: ["yes", "no"]
  name:
    description:
      - The name of the virtual machine.
    required: true
  image:
    description:
      - The system image ID for creating the virtual machine, e.g. a3eae284-a2fe-11e4-b187-5f1f641608c8.
    required: true
  image_password:
    description:
      - Password set for the administrative user.
    required: false
    version_added: "2.2"
  ssh_keys:
    description:
      - Public SSH keys allowing access to the virtual machine.
    required: false
    version_added: "2.2"
  volume_availability_zone:
    description:
      - The storage availability zone assigned to the volume.
    required: false
    default: None
    choices: [ "AUTO", "ZONE_1", "ZONE_2", "ZONE_3" ]
    version_added: "2.3"
  datacenter:
    description:
      - The datacenter to provision this virtual machine.
    required: false
    default: null
  cores:
    description:
      - The number of CPU cores to allocate to the virtual machine.
    required: false
    default: 2
  ram:
    description:
      - The amount of memory to allocate to the virtual machine.
    required: false
    default: 2048
  cpu_family:
    description:
      - The CPU family type to allocate to the virtual machine.
    required: false
    default: AMD_OPTERON
    choices: [ "AMD_OPTERON", "INTEL_XEON" ]
    version_added: "2.2"
  availability_zone:
    description:
      - The availability zone assigned to the server.
    required: false
    default: AUTO
    choices: [ "AUTO", "ZONE_1", "ZONE_2" ]
    version_added: "2.3"
  volume_size:
    description:
      - The size in GB of the boot volume.
    required: false
    default: 10
  bus:
    description:
      - The bus type for the volume.
    required: false
    default: VIRTIO
    choices: [ "IDE", "VIRTIO"]
  instance_ids:
    description:
      - list of instance ids, currently only used when state='absent' to remove instances.
    required: false
  count:
    description:
      - The number of virtual machines to create.
    required: false
    default: 1
  location:
    description:
      - The datacenter location. Use only if you want to create the Datacenter or else this value is ignored.
    required: false
    default: us/las
    choices: [ "us/las", "de/fra", "de/fkb" ]
  assign_public_ip:
    description:
      - This will assign the machine to the public LAN. If no LAN exists with public Internet access it is created.
    required: false
    default: false
  lan:
    description:
      - The ID of the LAN you wish to add the servers to.
    required: false
    default: 1
  nat:
    description:
      - Boolean value indicating if the private IP address has outbound access to the public Internet.
    required: false
    default: false
    version_added: "2.3"
  subscription_user:
    description:
      - The ProfitBricks username. Overrides the PROFITBRICKS_USERNAME environement variable.
    required: false
    default: null
  subscription_password:
    description:
      - THe ProfitBricks password. Overrides the PROFITBRICKS_PASSWORD environement variable.
    required: false
    default: null
  wait:
    description:
      - wait for the instance to be in state 'running' before returning
    required: false
    default: "yes"
    choices: [ "yes", "no" ]
  wait_timeout:
    description:
      - how long before wait gives up, in seconds
    default: 600
  remove_boot_volume:
    description:
      - remove the bootVolume of the virtual machine you're destroying.
    required: false
    default: "yes"
    choices: ["yes", "no"]
  state:
    description:
      - create or terminate instances
    required: false
    default: "present"
    choices: [ "running", "stopped", "absent", "present" ]

requirements:
    - "python >= 2.6"
    - "profitbricks >= 3.0.0"
author:
    - "Matt Baldwin (baldwin@stackpointcloud.com)"
    - "Ethan Devenport (@edevenport)"
'''

EXAMPLES = '''

# Note: These examples do not set authentication details, see the AWS Guide for details.

# Provisioning example. This will create three servers and enumerate their names.

- profitbricks:
    datacenter: Tardis One
    name: web%02d.stackpointcloud.com
    cores: 4
    ram: 2048
    volume_size: 50
    cpu_family: INTEL_XEON
    image: a3eae284-a2fe-11e4-b187-5f1f641608c8
    location: us/las
    count: 3
    assign_public_ip: true

# Removing Virtual machines

- profitbricks:
    datacenter: Tardis One
    instance_ids:
      - 'web001.stackpointcloud.com'
      - 'web002.stackpointcloud.com'
      - 'web003.stackpointcloud.com'
    wait_timeout: 500
    state: absent

# Starting Virtual Machines.

- profitbricks:
    datacenter: Tardis One
    instance_ids:
      - 'web001.stackpointcloud.com'
      - 'web002.stackpointcloud.com'
      - 'web003.stackpointcloud.com'
    wait_timeout: 500
    state: running

# Stopping Virtual Machines

- profitbricks:
    datacenter: Tardis One
    instance_ids:
      - 'web001.stackpointcloud.com'
      - 'web002.stackpointcloud.com'
      - 'web003.stackpointcloud.com'
    wait_timeout: 500
    state: stopped

'''

import re
import uuid
import time

HAS_PB_SDK = True

try:
    from profitbricks import __version__ as sdk_version
    from profitbricks.client import (ProfitBricksService, Volume, Server,
                                    Datacenter, NIC, LAN)
except ImportError:
    HAS_PB_SDK = False

LOCATIONS = ['us/las',
             'de/fra',
             'de/fkb']

CPU_FAMILIES = ['AMD_OPTERON',
                'INTEL_XEON']

DISK_TYPES = ['HDD',
              'SSD']

BUS_TYPES = ['VIRTIO',
             'IDE']

AVAILABILITY_ZONES = ['AUTO',
                      'ZONE_1',
                      'ZONE_2',
                      'ZONE_3']

uuid_match = re.compile(
    '[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}', re.I)


def _wait_for_completion(profitbricks, promise, wait_timeout, msg):
    if not promise: return
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)
        operation_result = profitbricks.get_request(
            request_id=promise['requestId'],
            status=True)

        if operation_result['metadata']['status'] == "DONE":
            return
        elif operation_result['metadata']['status'] == "FAILED":
            raise Exception(
                'Request failed to complete ' + msg + ' "' + str(
                    promise['requestId']) + '" to complete.')

    raise Exception(
        'Timed out waiting for async operation ' + msg + ' "' + str(
            promise['requestId']
            ) + '" to complete.')


def _create_machine(module, profitbricks, datacenter, name):
    cores = module.params.get('cores')
    ram = module.params.get('ram')
    cpu_family = module.params.get('cpu_family')
    volume_size = module.params.get('volume_size')
    disk_type = module.params.get('disk_type')
    availability_zone = module.params.get('availability_zone')
    volume_availability_zone = module.params.get('volume_availability_zone')
    image_password = module.params.get('image_password')
    ssh_keys = module.params.get('ssh_keys')
    bus = module.params.get('bus')
    lan = module.params.get('lan')
    nat = module.params.get('nat')
    assign_public_ip = module.params.get('assign_public_ip')
    subscription_user = module.params.get('subscription_user')
    subscription_password = module.params.get('subscription_password')
    location = module.params.get('location')
    image = module.params.get('image')
    assign_public_ip = module.boolean(module.params.get('assign_public_ip'))
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    if assign_public_ip:
        public_found = False

        lans = profitbricks.list_lans(datacenter)
        for lan in lans['items']:
            if lan['properties']['public']:
                public_found = True
                lan = lan['id']

        if not public_found:
            i = LAN(
                name='public',
                public=True)

            lan_response = profitbricks.create_lan(datacenter, i)
            _wait_for_completion(profitbricks, lan_response,
                                 wait_timeout, "_create_machine")
            lan = lan_response['id']

    v = Volume(
        name=str(uuid.uuid4()).replace('-', '')[:10],
        size=volume_size,
        image=image,
        image_password=image_password,
        ssh_keys=ssh_keys,
        disk_type=disk_type,
        availability_zone=volume_availability_zone,
        bus=bus
        )

    n = NIC(
        name=str(uuid.uuid4()).replace('-', '')[:10],
        nat=nat,
        lan=int(lan)
        )

    s = Server(
        name=name,
        ram=ram,
        cores=cores,
        cpu_family=cpu_family,
        availability_zone=availability_zone,
        create_volumes=[v],
        nics=[n],
        )

    try:
        create_server_response = profitbricks.create_server(
            datacenter_id=datacenter, server=s)

        _wait_for_completion(profitbricks, create_server_response,
                             wait_timeout, "create_virtual_machine")

        server_response = profitbricks.get_server(
            datacenter_id=datacenter,
            server_id=create_server_response['id'],
            depth=3
        )
    except Exception as e:
        module.fail_json(msg="failed to create the new server: %s" % str(e))
    else:
        server_response['nic'] = server_response['entities']['nics']['items'][0]
        return server_response


def _update_machine(module, profitbricks, datacenter_id, server_id):
    cores = module.params.get('cores')
    ram = module.params.get('ram')
    cpu_family = module.params.get('cpu_family')
    subscription_user = module.params.get('subscription_user')
    subscription_password = module.params.get('subscription_password')
    location = module.params.get('location')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    try:
        # create_server_response = profitbricks.update_server(
            # datacenter_id=datacenter, server=s, name=name)

        create_server_response = profitbricks.update_server(
            datacenter_id=datacenter_id,
            server_id=server_id,
            cores=cores,
            ram=ram,
            cpu_family=cpu_family)

        _wait_for_completion(profitbricks, create_server_response,
                             wait_timeout, "update_virtual_machine")

        server_response = profitbricks.get_server(
            datacenter_id=datacenter_id,
            server_id=create_server_response['id'],
            depth=3
        )
    except Exception as e:
        module.fail_json(msg="failed to update machine: %s" % str(e))
    else:
        server_response['nic'] = server_response['entities']['nics']['items'][0]
        return server_response


def _startstop_machine(module, profitbricks, datacenter_id, server_id):
    state = module.params.get('state')

    try:
        if state == 'running':
            profitbricks.start_server(datacenter_id, server_id)
        else:
            profitbricks.stop_server(datacenter_id, server_id)

        return True
    except Exception as e:
        module.fail_json(msg="failed to start or stop the virtual machine %s: %s" % (name, str(e)))


def _create_datacenter(module, profitbricks):
    datacenter = module.params.get('datacenter')
    location = module.params.get('location')
    wait_timeout = module.params.get('wait_timeout')

    i = Datacenter(
        name=datacenter,
        location=location
        )

    try:
        datacenter_response = profitbricks.create_datacenter(datacenter=i)

        _wait_for_completion(profitbricks, datacenter_response,
                             wait_timeout, "_create_datacenter")

        return datacenter_response
    except Exception as e:
        module.fail_json(msg="failed to create the new server(s): %s" % str(e))


def create_virtual_machine(module, profitbricks):
    """
    Create new virtual machine

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object

    Returns:
        True if a new virtual machine was created, false otherwise
    """
    datacenter = module.params.get('datacenter')
    name = module.params.get('name')
    auto_increment = module.params.get('auto_increment')
    count = module.params.get('count')
    lan = module.params.get('lan')
    nat = module.params.get('nat')
    wait_timeout = module.params.get('wait_timeout')
    failed = True
    datacenter_found = False

    virtual_machines = []
    virtual_machine_ids = []

    # Locate UUID for datacenter if referenced by name.
    datacenter_list = profitbricks.list_datacenters()
    datacenter_id = _get_datacenter_id(datacenter_list, datacenter)
    if datacenter_id:
        datacenter_found = True

    if not datacenter_found:
        datacenter_response = _create_datacenter(module, profitbricks)
        datacenter_id = datacenter_response['id']

        _wait_for_completion(profitbricks, datacenter_response,
                             wait_timeout, "create_virtual_machine")

    if auto_increment:
        numbers = set()
        count_offset = 1

        try:
            name % 0
        except TypeError, e:
            if e.message.startswith('not all'):
                name = '%s%%d' % name
            else:
                module.fail_json(msg=e.message)

        number_range = xrange(count_offset, count_offset + count + len(numbers))
        available_numbers = list(set(number_range).difference(numbers))
        names = []
        numbers_to_use = available_numbers[:count]
        for number in numbers_to_use:
            names.append(name % number)
    else:
        names = [name]

    # Prefetch a list of servers for later comparison.
    server_list = profitbricks.list_servers(datacenter_id)
    for name in names:
        # Skip server creation if the server already exists.
        if _get_server_id(server_list, name):
            continue

        create_response = _create_machine(module, profitbricks, str(datacenter_id), name)
        nics = profitbricks.list_nics(datacenter_id, create_response['id'])
        for n in nics['items']:
            if lan == n['properties']['lan']:
                create_response.update({'public_ip': n['properties']['ips'][0]})

        virtual_machines.append(create_response)

    failed = False

    results = {
        'failed': failed,
        'machines': virtual_machines,
        'action': 'create',
        'instance_ids': {
            'instances': [i['id'] for i in virtual_machines],
        }
    }

    return results


def update_virtual_machine(module, profitbricks):
    """
    Updates a virtual machine

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object

    Returns:
        True if a virtual machine was updated, false otherwise
    """
    datacenter = module.params.get('datacenter')
    name = module.params.get('name')
    wait_timeout = module.params.get('wait_timeout')
    failed = True
    datacenter_found = False

    virtual_machines = []

    # Locate UUID for datacenter if referenced by name.
    datacenter_list = profitbricks.list_datacenters()
    datacenter_id = _get_datacenter_id(datacenter_list, datacenter)
    if datacenter_id:
        datacenter_found = True

    if not datacenter_found:
        datacenter_response = _create_datacenter(module, profitbricks)
        datacenter_id = datacenter_response['id']

        _wait_for_completion(profitbricks, datacenter_response,
                             wait_timeout, "update_virtual_machine")

    names = [name]

    # Prefetch a list of servers for later comparison.
    server_list = profitbricks.list_servers(datacenter_id)
    for name in names:
        # Skip server creation if the server already exists.
        server_id = _get_server_id(server_list, name)

        create_response = _update_machine(module, profitbricks, str(datacenter_id), server_id)

        virtual_machines.append(create_response)

    failed = False

    results = {
        'failed': failed,
        'machines': virtual_machines,
        'action': 'update',
        'instance_ids': {
            'instances': [i['id'] for i in virtual_machines],
        }
    }

    return results


def remove_virtual_machine(module, profitbricks):
    """
    Removes a virtual machine.

    This will remove the virtual machine along with the bootVolume.

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object.

    Not yet supported: handle deletion of attached data disks.

    Returns:
        True if a new virtual server was deleted, false otherwise
    """
    datacenter = module.params.get('datacenter')
    instance_ids = module.params.get('instance_ids')
    remove_boot_volume = module.params.get('remove_boot_volume')
    changed = False

    if not isinstance(module.params.get('instance_ids'), list) or len(module.params.get('instance_ids')) < 1:
        module.fail_json(msg='instance_ids should be a list of virtual machine ids or names, aborting')

    # Locate UUID for datacenter if referenced by name.
    datacenter_list = profitbricks.list_datacenters()
    datacenter_id = _get_datacenter_id(datacenter_list, datacenter)
    if not datacenter_id:
        module.fail_json(msg='Virtual data center \'%s\' not found.' % str(datacenter))

    # Prefetch server list for later comparison.
    server_list = profitbricks.list_servers(datacenter_id)
    for instance in instance_ids:
        # Locate UUID for server if referenced by name.
        server_id = _get_server_id(server_list, instance)
        if server_id:
            # Remove the server's boot volume
            if remove_boot_volume:
                _remove_boot_volume(module, profitbricks, datacenter_id, server_id)

            # Remove the server
            try:
                server_response = profitbricks.delete_server(datacenter_id, server_id)
            except Exception as e:
                module.fail_json(msg="failed to terminate the virtual server: %s" % str(e))
            else:
                changed = True

    return changed


def _remove_boot_volume(module, profitbricks, datacenter_id, server_id):
    """
    Remove the boot volume from the server
    """
    try:
        server = profitbricks.get_server(datacenter_id, server_id)
        volume_id = server['properties']['bootVolume']['id']
        volume_response = profitbricks.delete_volume(datacenter_id, volume_id)
    except Exception as e:
        module.fail_json(msg="failed to remove the server's boot volume: %s" % str(e))


def startstop_machine(module, profitbricks, state):
    """
    Starts or Stops a virtual machine.

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object.

    Returns:
        True when the servers process the action successfully, false otherwise.
    """
    if not isinstance(module.params.get('instance_ids'), list) or len(module.params.get('instance_ids')) < 1:
        module.fail_json(msg='instance_ids should be a list of virtual machine ids or names, aborting')

    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')
    changed = False

    datacenter = module.params.get('datacenter')
    instance_ids = module.params.get('instance_ids')

    # Locate UUID for datacenter if referenced by name.
    datacenter_list = profitbricks.list_datacenters()
    datacenter_id = _get_datacenter_id(datacenter_list, datacenter)
    if not datacenter_id:
        module.fail_json(msg='Virtual data center \'%s\' not found.' % str(datacenter))

    # Prefetch server list for later comparison.
    server_list = profitbricks.list_servers(datacenter_id)
    for instance in instance_ids:
        # Locate UUID of server if referenced by name.
        server_id = _get_server_id(server_list, instance)
        if server_id:
            _startstop_machine(module, profitbricks, datacenter_id, server_id)
            changed = True

    if wait:
        wait_timeout = time.time() + wait_timeout
        while wait_timeout > time.time():
            matched_instances = []
            for res in profitbricks.list_servers(datacenter_id)['items']:
                if state == 'running':
                    if res['properties']['vmState'].lower() == state:
                        matched_instances.append(res)
                elif state == 'stopped':
                    if res['properties']['vmState'].lower() == 'shutoff':
                        matched_instances.append(res)

            if len(matched_instances) < len(instance_ids):
                time.sleep(5)
            else:
                break

        if wait_timeout <= time.time():
            # waiting took too long
            module.fail_json(msg="wait for virtual machine state timeout on %s" % time.asctime())

    return (changed)


def _get_datacenter_id(datacenters, identity):
    """
    Fetch and return datacenter UUID by datacenter name if found.
    """
    for datacenter in datacenters['items']:
        if identity in (datacenter['properties']['name'], datacenter['id']):
            return datacenter['id']
    return None


def _get_server_id(servers, identity):
    """
    Fetch and return server UUID by server name if found.
    """
    for server in servers['items']:
        if identity in (server['properties']['name'], server['id']):
            return server['id']
    return None


def main():
    module = AnsibleModule(
        argument_spec=dict(
            datacenter=dict(type='str'),
            name=dict(type='str'),
            image=dict(type='str'),
            cores=dict(type='int', default=2),
            ram=dict(type='int', default=2048),
            cpu_family=dict(type='str', choices=CPU_FAMILIES, default='AMD_OPTERON'),
            volume_size=dict(type='int', default=10),
            disk_type=dict(type='str', choices=DISK_TYPES, default='HDD'),
            availability_zone=dict(type='str', choices=AVAILABILITY_ZONES, default='AUTO'),
            volume_availability_zone=dict(type='str', choices=AVAILABILITY_ZONES, default=None),
            image_password=dict(type='str', default=None),
            ssh_keys=dict(type='list', default=[]),
            bus=dict(type='str', choices=BUS_TYPES, default='VIRTIO'),
            lan=dict(type='int', default=1),
            nat=dict(type='bool', default=None),
            count=dict(type='int', default=1),
            auto_increment=dict(type='bool', default=True),
            instance_ids=dict(type='list', default=[]),
            subscription_user=dict(type='str', default=os.environ.get('PROFITBRICKS_USERNAME')),
            subscription_password=dict(type='str', default=os.environ.get('PROFITBRICKS_PASSWORD')),
            location=dict(type='str', choices=LOCATIONS, default='us/las'),
            assign_public_ip=dict(type='bool', default=False),
            wait=dict(type='bool', default=True),
            wait_timeout=dict(type='int', default=600),
            remove_boot_volume=dict(type='bool', default=True),
            state=dict(type='str', default='present'),
        )
    )

    if not HAS_PB_SDK:
        module.fail_json(msg='profitbricks required for this module')

    if not module.params.get('subscription_user'):
        module.fail_json(msg='subscription_user parameter or ' +
            'PROFITBRICKS_USERNAME environment variable is required.')
    if not module.params.get('subscription_password'):
        module.fail_json(msg='subscription_password parameter or ' +
            'PROFITBRICKS_PASSWORD environment variable is required.')

    subscription_user = module.params.get('subscription_user')
    subscription_password = module.params.get('subscription_password')
    wait = module.params.get('wait')
    wait_timeout = module.params.get('wait_timeout')

    profitbricks = ProfitBricksService(
        username=subscription_user,
        password=subscription_password)

    user_agent = 'profitbricks-sdk-ruby/%s Ansible/%s' % (sdk_version, __version__)
    profitbricks.headers = {'User-Agent': user_agent}

    state = module.params.get('state')

    if state == 'absent':
        if not module.params.get('datacenter'):
            module.fail_json(msg='datacenter parameter is required ' +
                'for running or stopping machines.')

        try:
            (changed) = remove_virtual_machine(module, profitbricks)
            module.exit_json(changed=changed)
        except Exception as e:
            module.fail_json(msg='failed to set instance state: %s' % str(e))

    elif state in ('running', 'stopped'):
        if not module.params.get('datacenter'):
            module.fail_json(msg='datacenter parameter is required for ' +
                'running or stopping machines.')
        try:
            (changed) = startstop_machine(module, profitbricks, state)
            module.exit_json(changed=changed)
        except Exception as e:
            module.fail_json(msg='failed to set instance state: %s' % str(e))

    elif state == 'present':
        if not module.params.get('name'):
            module.fail_json(msg='name parameter is required for new instance')

        datacenter_list = profitbricks.list_datacenters()
        datacenter_id = _get_datacenter_id(datacenter_list, module.params.get('datacenter'))
        server_list = profitbricks.list_servers(datacenter_id)
        if not _get_server_id(server_list, module.params.get('name')):
            # create
            if not module.params.get('image'):
                module.fail_json(msg='image parameter is required for new instance')

            try:
                (machine_dict_array) = create_virtual_machine(module, profitbricks)
                module.exit_json(**machine_dict_array)
            except Exception as e:
                module.fail_json(msg='failed to set instance state: %s' % str(e))
        else:
            # update
            try:
                (machine_dict_array) = update_virtual_machine(module, profitbricks)
                module.exit_json(**machine_dict_array)
            except Exception as e:
                module.fail_json(msg='failed to set instance state: %s' % str(e))

from ansible import __version__
from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
