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
import logging
import re
import urlparse

from oslo_config import cfg

from syntribos.clients.http.client import SynHTTPClient
import syntribos.extensions.rax_billing_system.models as models
from syntribos.extensions.rax_identity.client import get_token
from syntribos.utils.memoize import memoize

logging.basicConfig(level=logging.CRITICAL)
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


@memoize
def list_paymentMethods():
    headers = {'accept': 'application/json', 'x-auth-token': get_token()}
    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/%s/methods" % CONF.rax_billing_system.ran)
    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)
    _methods = resp.json()['methods']['method']
    paymentMethods = {}
    for m in _methods:
        paymentMethods[m['id']] = models.PaymentMethod._dict_to_obj(m)
    return paymentMethods


def get_one_methodId():
    return list_paymentMethods().items()[0][0]


def get_one_method():
    return list_paymentMethods().items()[0][1]


def get_paymentmethod(methodId):
    headers = {'accept': 'application/json', 'x-auth-token': get_token()}
    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/{0}/methods/{1}".format(CONF.rax_billing_system.ran,
                                              methodId))
    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)
    m = models.PaymentMethod._dict_to_obj(resp.json())
    return m


methodValidations = {}


def create_methodValidation(lineOfBusiness=None,
                            contractEntity=None,
                            currencyCode=None,
                            addressVerificationInformation=None,
                            method=None):
    headers = {'accept': 'application/json', 'x-auth-token': get_token(),
               'content-type': 'application/json'}
    endpoint = urlparse.urljoin(CONF.syntribos.endpoint,
                                "/v1/methodValidations")
    if addressVerificationInformation:
        _avi = addressVerificationInformation
    else:
        _avi = {
            'country': 'US',
            'state': 'TX',
            'city': 'San Antonio',
            'addressLine1': '1 Fanatical Pl',
            'addressLine2': '',
            'postalCode': '78218',
        }
    method = method or get_one_method()
    if not method.addressVerificationInformation:
        method.addressVerificationInformation = _avi
    _mv = models.MethodValidation(
        method=method,
        lineOfBusiness=lineOfBusiness or 'US_CLOUD',
        contractEntity=contractEntity or 'CONTRACT_US',
        currencyCode=currencyCode or 'USD')
    data = _mv._obj_to_dict()
    resp, _ = SynHTTPClient().request(
        "POST", endpoint, data=data, headers=headers, sanitize=True)
    validation = models.MethodValidation._dict_to_obj(resp.json())
    methodValidations[validation.methodValidationId] = validation

    return validation


def get_one_methodValidationId():
    if not methodValidations:
        create_methodValidation()
    return methodValidations.items()[0][0]


def get_one_methodValidation():
    if not methodValidations:
        create_methodValidation()
    return methodValidations.items()[0][1]


@memoize
def list_payments():
    headers = {'accept': 'application/json', 'x-auth-token': get_token(),
               'content-type': 'application/json'}
    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/%s/payments" % CONF.rax_billing_system.ran)
    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)
    _payments = resp.json()['payments']['payment']
    payments = {}
    for p in _payments:
        payments[p['id']] = models.Payment._dict_to_obj(p)
    return payments


def get_one_paymentId():
    return list_payments().items()[0][0]


def get_one_payment():
    return list_payments().items()[0][1]


@memoize
def list_voids():
    headers = {'accept': 'application/json', 'x-auth-token': get_token(),
               'content-type': 'application/json'}
    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/payments/%s/voids" % get_one_paymentId())
    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)
    _voids = resp.json()['voids']['void']
    voids = {}
    for v in _voids:
        voids[v['id']] = models.Void._dict_to_obj(v)
    return voids


def get_one_voidId():
    return list_voids().items()[0][0]


def get_one_void():
    return list_voids().items()[0][1]


@memoize
def list_refunds():
    headers = {'accept': 'application/json', 'x-auth-token': get_token(),
               'content-type': 'application/json'}
    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/%s/refunds" % CONF.rax_billing_system.ran)
    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)
    _refunds = resp.json()['refunds']['refund']
    refunds = {}
    for r in _refunds:
        refunds[r['id']] = models.Refund._dict_to_obj(r)
    return refunds


def get_one_refundId():
    return list_refunds().items()[0][0]


def get_one_refund():
    return list_refunds().items()[0][1]
