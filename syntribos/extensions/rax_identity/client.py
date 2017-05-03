# Copyright 2017 Rackspace
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import logging

from oslo_config import cfg
from requests import RequestException as RequestException

from syntribos.clients.http.client import SynHTTPClient
from syntribos.utils.memoize import memoize

logging.basicConfig(level=logging.CRITICAL)
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def authenticate(endpoint, username, apiKey):
    headers = {'content-type': 'application/json'}
    if endpoint.endswith('/v2.0/'):
        endpoint = '{0}tokens'.format(endpoint)
    elif endpoint.endswith('/v2.0'):
        endpoint = '{0}/tokens'.format(endpoint)
    elif endpoint.endswith('/v2.0/tokens'):
        pass
    else:
        endpoint = '{0}/v2.0/tokens'.format(endpoint)
    data = {'auth': {"RAX-KSKEY:apiKeyCredentials": {"username": username,
                                                     "apiKey": apiKey}}}
    data = json.dumps(data)

    try:
        resp, _ = SynHTTPClient().request(
            "POST", endpoint, headers=headers, data=data, sanitize=True)
        r = resp.json()
    except RequestException as e:
        LOG.debug(e)
    else:
        if not r:
            raise Exception("Failed to authenticate")
        if 'access' not in r or not r['access']:
            raise Exception("Failed to parse Auth response Body")
        return r['access']


def authenticate_config(user_section):
    return authenticate(
        endpoint=CONF.get(user_section).endpoint or CONF.user.endpoint,
        username=CONF.get(user_section).username or CONF.user.username,
        apiKey=CONF.get(user_section).apiKey or CONF.user.apiKey)


@memoize
def get_token(user_section='user'):
    """Returns  unscoped v2 token."""
    access_data = authenticate_config(user_section)
    return access_data['token']['id']
