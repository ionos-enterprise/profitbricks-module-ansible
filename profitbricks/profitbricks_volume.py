#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: profitbricks_volume
short_description: Create, update or destroy a volume.
description:
     - Allows you to create, update or remove a volume from a ProfitBricks datacenter.
version_added: "2.0"
options:
  datacenter:
    description:
      - The datacenter in which to create the volumes.
    required: true
  name:
    description:
      - The name of the volumes. You can enumerate the names using auto_increment.
    required: true
  size:
    description:
      - The size of the volume.
    required: false
    default: 10
  bus:
    description:
      - The bus type.
    required: false
    default: VIRTIO
    choices: [ "IDE", "VIRTIO"]
  image:
    description:
      - The image alias or ID for the volume. This can also be a snapshot image ID.
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
  disk_type:
    description:
      - The disk type of the volume.
    required: false
    default: HDD
    choices: [ "HDD", "SSD" ]
  licence_type:
    description:
      - The licence type for the volume. This is used when the image is non-standard.
    required: false
    default: UNKNOWN
    choices: ["LINUX", "WINDOWS", "UNKNOWN" , "OTHER", "WINDOWS2016"]
  availability_zone:
    description:
      - The storage availability zone assigned to the volume.
    required: false
    default: None
    choices: [ "AUTO", "ZONE_1", "ZONE_2", "ZONE_3" ]
    version_added: "2.3"
  count:
    description:
      - The number of volumes you wish to create.
    required: false
    default: 1
  auto_increment:
    description:
      - Whether or not to increment a single number in the name for created virtual machines.
    default: yes
    choices: ["yes", "no"]
  instance_ids:
    description:
      - list of instance ids, currently only used when state='absent' to remove instances.
    required: false
  api_url:
    description:
      - The ProfitBricks API base URL.
    required: false
    default: null
    version_added: "2.4"
  username:
    description:
      - The ProfitBricks username. Overrides the PROFITBRICKS_USERNAME environment variable.
    required: false
    aliases: subscription_user
  password:
    description:
      - The ProfitBricks password. Overrides the PROFITBRICKS_PASSWORD environment variable.
    required: false
    aliases: subscription_password
  wait:
    description:
      - wait for the datacenter to be created before returning
    required: false
    default: "yes"
    choices: [ "yes", "no" ]
  wait_timeout:
    description:
      - how long before wait gives up, in seconds
    default: 600
  state:
    description:
      - Indicate desired state of the resource
    required: false
    default: "present"
    choices: ["present", "absent", "update"]

requirements:
    - "python >= 2.6"
    - "ionosenterprise >= 5.2.0"
author:
    - "Matt Baldwin (baldwin@stackpointcloud.com)"
    - "Ethan Devenport (@edevenport)"
'''

EXAMPLES = '''

# Create Multiple Volumes

- profitbricks_volume:
    datacenter: Tardis One
    name: vol%02d
    count: 5
    auto_increment: yes
    wait_timeout: 500
    state: present

# Update Volumes

- profitbricks_volume:
    datacenter: Tardis One
    instance_ids:
      - 'vol01'
      - 'vol02'
    size: 50
    bus: IDE
    wait_timeout: 500
    state: update

# Remove Volumes

- profitbricks_volume:
    datacenter: Tardis One
    instance_ids:
      - 'vol01'
      - 'vol02'
    wait_timeout: 500
    state: absent

'''

import re
import time
import traceback

from uuid import UUID

HAS_SDK = True

try:
    from ionosenterprise import __version__ as sdk_version
    from ionosenterprise.client import IonosEnterpriseService
    from ionosenterprise.items import Volume
except ImportError:
    HAS_SDK = False

from ansible import __version__
from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.module_utils.six.moves import xrange
from ansible.module_utils._text import to_native

DISK_TYPES = ['HDD',
              'SSD']

BUS_TYPES = ['VIRTIO',
             'IDE']

AVAILABILITY_ZONES = ['AUTO',
                      'ZONE_1',
                      'ZONE_2',
                      'ZONE_3']

LICENCE_TYPES = ['LINUX',
                 'WINDOWS',
                 'UNKNOWN',
                 'OTHER',
                 'WINDOWS2016']

uuid_match = re.compile(
    '[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}', re.I)


def _wait_for_completion(client, promise, wait_timeout, msg):
    if not promise:
        return
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)
        operation_result = client.get_request(
            request_id=promise['requestId'],
            status=True)

        if operation_result['metadata']['status'] == "DONE":
            return
        elif operation_result['metadata']['status'] == "FAILED":
            raise Exception(
                'Request failed to complete ' + msg + ' "' + str(
                    promise['requestId']) + '" to complete.')

    raise Exception('Timed out waiting for async operation ' + msg + ' "' +
                    str(promise['requestId']) + '" to complete.')


def _create_volume(module, client, datacenter, name):
    size = module.params.get('size')
    bus = module.params.get('bus')
    image = module.params.get('image')
    image_password = module.params.get('image_password')
    ssh_keys = module.params.get('ssh_keys')
    disk_type = module.params.get('disk_type')
    availability_zone = module.params.get('availability_zone')
    licence_type = module.params.get('licence_type')
    wait_timeout = module.params.get('wait_timeout')
    wait = module.params.get('wait')

    if module.check_mode:
        module.exit_json(changed=True)

    try:
        v = Volume(
            name=name,
            size=size,
            bus=bus,
            image_password=image_password,
            ssh_keys=ssh_keys,
            disk_type=disk_type,
            licence_type=licence_type,
            availability_zone=availability_zone
        )

        try:
            UUID(image)
        except Exception:
            v.image_alias = image
        else:
            v.image = image

        volume_response = client.create_volume(datacenter, v)

        if wait:
            _wait_for_completion(client, volume_response,
                                 wait_timeout, "_create_volume")

    except Exception as e:
        module.fail_json(msg="failed to create the volume: %s" % to_native(e))

    return volume_response


def _update_volume(module, client, datacenter, volume):
    size = module.params.get('size')
    bus = module.params.get('bus')
    wait_timeout = module.params.get('wait_timeout')
    wait = module.params.get('wait')

    if module.check_mode:
        module.exit_json(changed=True)

    try:
        volume_response = client.update_volume(
            datacenter_id=datacenter,
            volume_id=volume,
            size=size,
            bus=bus
        )

        if wait:
            _wait_for_completion(client, volume_response,
                                 wait_timeout, "_update_volume")

    except Exception as e:
        module.fail_json(msg="failed to update the volume: %s" % to_native(e))

    return volume_response


def _delete_volume(module, client, datacenter, volume):
    if module.check_mode:
        module.exit_json(changed=True)
    try:
        client.delete_volume(datacenter, volume)
    except Exception as e:
        module.fail_json(msg="failed to remove the volume: %s" % to_native(e))


def create_volume(module, client):
    """
    Create volumes.

    This will create one or more volumes in a datacenter.

    module : AnsibleModule object
    client: authenticated ionosenterprise object.

    Returns:
        dict of created volumes
    """
    datacenter = module.params.get('datacenter')
    name = module.params.get('name')
    auto_increment = module.params.get('auto_increment')
    count = module.params.get('count')

    datacenter_found = False
    volumes = []

    datacenter_list = client.list_datacenters()
    for d in datacenter_list['items']:
        dc = client.get_datacenter(d['id'])
        if datacenter in [dc['properties']['name'], dc['id']]:
            datacenter = d['id']
            datacenter_found = True
            break

    if not datacenter_found:
        module.fail_json(msg='datacenter could not be found.')

    if auto_increment:
        numbers = set()
        count_offset = 1

        try:
            name % 0
        except TypeError as e:
            if (hasattr(e, 'message') and e.message.startswith('not all') or to_native(e).startswith('not all')):
                name = '%s%%d' % name
            else:
                module.fail_json(msg=e.message, exception=traceback.format_exc())

        number_range = xrange(count_offset, count_offset + count + len(numbers))
        available_numbers = list(set(number_range).difference(numbers))
        names = []
        numbers_to_use = available_numbers[:count]
        for number in numbers_to_use:
            names.append(name % number)
    else:
        names = [name] * count

    changed = False

    # Prefetch a list of volumes for later comparison.
    volume_list = client.list_volumes(datacenter)

    for name in names:
        # Skip volume creation if a volume with the same name already exists.
        if _get_instance_id(volume_list, name):
            continue

        create_response = _create_volume(module, client, str(datacenter), name)
        volumes.append(create_response)
        _attach_volume(module, client, datacenter, create_response['id'])
        changed = True

    results = {
        'changed': changed,
        'failed': False,
        'volumes': volumes,
        'action': 'create',
        'instance_ids': {
            'instances': [i['id'] for i in volumes],
        }
    }

    return results


def update_volume(module, client):
    """
    Update volumes.

    This will update one or more volumes in a datacenter.

    module : AnsibleModule object
    client: authenticated ionosenterprise object.

    Returns:
        dict of updated volumes
    """
    datacenter = module.params.get('datacenter')
    instance_ids = module.params.get('instance_ids')

    datacenter_found = False
    failed = True
    changed = False
    volumes = []

    datacenter_list = client.list_datacenters()
    for d in datacenter_list['items']:
        dc = client.get_datacenter(d['id'])
        if datacenter in [dc['properties']['name'], dc['id']]:
            datacenter = d['id']
            datacenter_found = True
            break

    if not datacenter_found:
        module.fail_json(msg='datacenter could not be found.')

    for n in instance_ids:
        if(uuid_match.match(n)):
            update_response = _update_volume(module, client, datacenter, n)
            changed = True
        else:
            volume_list = client.list_volumes(datacenter)
            for v in volume_list['items']:
                if n == v['properties']['name']:
                    volume_id = v['id']
                    update_response = _update_volume(module, client, datacenter, volume_id)
                    changed = True

        volumes.append(update_response)
        failed = False

    results = {
        'changed': changed,
        'failed': failed,
        'volumes': volumes,
        'action': 'update',
        'instance_ids': {
            'instances': [i['id'] for i in volumes],
        }
    }

    return results


def delete_volume(module, client):
    """
    Remove volumes.

    This will remove one or more volumes from a datacenter.

    module : AnsibleModule object
    client: authenticated ionosenterprise object.

    Returns:
        True if the volumes were removed, false otherwise
    """
    if not isinstance(module.params.get('instance_ids'), list) or len(module.params.get('instance_ids')) < 1:
        module.fail_json(msg='instance_ids should be a list of volume ids or names, aborting')

    datacenter = module.params.get('datacenter')
    changed = False
    instance_ids = module.params.get('instance_ids')

    # Locate UUID for Datacenter
    if not (uuid_match.match(datacenter)):
        datacenter_list = client.list_datacenters()
        for d in datacenter_list['items']:
            dc = client.get_datacenter(d['id'])
            if datacenter in [dc['properties']['name'], dc['id']]:
                datacenter = d['id']
                break

    for n in instance_ids:
        if(uuid_match.match(n)):
            _delete_volume(module, client, datacenter, n)
            changed = True
        else:
            volumes = client.list_volumes(datacenter)
            for v in volumes['items']:
                if n == v['properties']['name']:
                    volume_id = v['id']
                    _delete_volume(module, client, datacenter, volume_id)
                    changed = True

    return changed


def _attach_volume(module, client, datacenter, volume):
    """
    Attaches a volume.

    This will attach a volume to the server.

    module : AnsibleModule object
    client: authenticated ionosenterprise object.

    Returns:
        the volume instance being attached
    """
    server = module.params.get('server')

    # Locate UUID for Server
    if server:
        if not (uuid_match.match(server)):
            server_list = client.list_servers(datacenter)
            for s in server_list['items']:
                if server == s['properties']['name']:
                    server = s['id']
                    break

        try:
            return client.attach_volume(datacenter, server, volume)
        except Exception as e:
            module.fail_json(msg='failed to attach volume: %s' % to_native(e))


def _get_instance_id(instance_list, identity):
    """
    Return instance UUID by name or ID, if found.
    """
    for i in instance_list['items']:
        if identity in (i['properties']['name'], i['id']):
            return i['id']
    return None


def main():
    module = AnsibleModule(
        argument_spec=dict(
            datacenter=dict(type='str'),
            server=dict(type='str'),
            name=dict(type='str'),
            size=dict(type='int', default=10),
            image=dict(type='str'),
            image_password=dict(type='str', default=None, no_log=True),
            ssh_keys=dict(type='list', default=[]),
            bus=dict(type='str', choices=BUS_TYPES, default='VIRTIO'),
            disk_type=dict(type='str', choices=DISK_TYPES, default='HDD'),
            licence_type=dict(type='str', choices=LICENCE_TYPES, default='UNKNOWN'),
            availability_zone=dict(type='str', choices=AVAILABILITY_ZONES, default=None),
            count=dict(type='int', default=1),
            auto_increment=dict(type='bool', default=True),
            instance_ids=dict(type='list', default=[]),
            api_url=dict(type='str', default=None),
            username=dict(
                type='str',
                required=True,
                aliases=['subscription_user'],
                fallback=(env_fallback, ['PROFITBRICKS_USERNAME'])
            ),
            password=dict(
                type='str',
                required=True,
                aliases=['subscription_password'],
                fallback=(env_fallback, ['PROFITBRICKS_PASSWORD']),
                no_log=True
            ),
            wait=dict(type='bool', default=True),
            wait_timeout=dict(type='int', default=600),
            state=dict(type='str', default='present'),
        ),
        supports_check_mode=True
    )

    if not HAS_SDK:
        module.fail_json(msg='ionosenterprise is required for this module, run `pip install ionosenterprise`')

    username = module.params.get('username')
    password = module.params.get('password')
    api_url = module.params.get('api_url')

    if not api_url:
        ionosenterprise = IonosEnterpriseService(username=username, password=password)
    else:
        ionosenterprise = IonosEnterpriseService(
            username=username,
            password=password,
            host_base=api_url
        )

    user_agent = 'profitbricks-sdk-python/%s Ansible/%s' % (sdk_version, __version__)
    ionosenterprise.headers = {'User-Agent': user_agent}

    state = module.params.get('state')

    if state == 'absent':
        if not module.params.get('datacenter'):
            module.fail_json(msg='datacenter parameter is required for creating, updating or deleting volumes.')

        try:
            (changed) = delete_volume(module, ionosenterprise)
            module.exit_json(changed=changed)
        except Exception as e:
            module.fail_json(msg='failed to set volume state: %s' % to_native(e))

    elif state == 'present':
        if not module.params.get('datacenter'):
            module.fail_json(msg='datacenter parameter is required for new instance')
        if not module.params.get('name'):
            module.fail_json(msg='name parameter is required for new instance')

        try:
            (volume_dict_array) = create_volume(module, ionosenterprise)
            module.exit_json(**volume_dict_array)
        except Exception as e:
            module.fail_json(msg='failed to set volume state: %s' % to_native(e))

    elif state == 'update':
        try:
            (volume_dict_array) = update_volume(module, ionosenterprise)
            module.exit_json(**volume_dict_array)
        except Exception as e:
            module.fail_json(msg='failed to update volume: %s' % to_native(e))


if __name__ == '__main__':
    main()
