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
import urlparse
import xmltodict

from oslo_config import cfg

from syntribos.clients.http.client import SynHTTPClient
import syntribos.extensions.rax_payment_system.models as models
from syntribos.extensions.rax_identity.client import get_token
from syntribos.utils.memoize import memoize

logging.basicConfig(level=logging.CRITICAL)
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


@memoize
def list_paymentMethods(ran=CONF.rax_payment_system.ran,
                        serialize_format='json',
                        deserialize_format='json'):
    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/%s/methods" % ran)

    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)

    if deserialize_format == 'json':
        _methods = resp.json()['methods']['method']
    else:
        _methods = xmltodict.parse(resp.data())['ns1:methods']

    paymentMethods = {}
    for m in _methods:
        _method_obj = models.PaymentMethod._dict_to_obj(m)
        paymentMethods[_method_obj.methodId] = _method_obj
    return paymentMethods


def get_one_methodId():
    return list_paymentMethods().items()[0][0]


def get_one_method():
    return list_paymentMethods().items()[0][1]


def get_paymentMethod(methodId,
                      ran=CONF.rax_payment_system.ran,
                      serialize_format='json',
                      deserialize_format='json'):
    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/{0}/methods/{1}".format(ran,
                                              methodId))
    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)
    m = models.PaymentMethod._dict_to_obj(resp.json())
    return m


def create_paymentMethod(methodType,
                         ran=CONF.rax_payment_system.ran,
                         serialize_format='json',
                         deserialize_format='json',
                         model=None,
                         **kwargs):
    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['content-type'] = 'application/%s' % serialize_format
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/{0}/methods".format(ran))

    if not model:
        if 'paymentCard' in methodType:
            _model_class = models.PaymentCardMethod
        elif 'electronicCheck' in methodType:
            _model_class = models.ACHMethod
        elif 'ukDirectDebit' in methodType:
            _model_class = models.UKDebitMethod
        elif 'sepa' in methodType:
            _model_class = models.SEPAMethod
        model = _model_class(**kwargs)

    if serialize_format == 'json':
        data = model._obj_to_dict()
    else:
        data = model._obj_to_xml()

    resp, _ = SynHTTPClient().request(
        "POST", endpoint, data=data, headers=headers, sanitize=True)

    if deserialize_format == 'json':
        resp_data = resp.json()['papi:method']
    else:
        resp_data = xmltodict.parse(resp.data())['ns2:method']

    return type(model)._dict_to_obj(resp_data)


def delete_paymentMethod(methodId,
                         ran=CONF.rax_payment_system.ran,
                         serialize_format='json',
                         deserialize_format='json'):
    headers = {}
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/{0}/methods/{1}".format(ran,
                                              methodId))
    resp, _ = SynHTTPClient().request(
        "DELETE", endpoint, headers=headers, sanitize=True)


methodValidations = {}


def create_methodValidation(lineOfBusiness=None,
                            contractEntity=None,
                            currencyCode=None,
                            addressVerificationInformation=None,
                            method=None,
                            ran=CONF.rax_payment_system.ran,
                            serialize_format='json',
                            deserialize_format='json'):
    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['content-type'] = 'application/%s' % serialize_format
    headers['x-auth-token'] = get_token()

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

    if serialize_format == 'json':
        data = _mv._obj_to_dict()
    else:
        data = _mv._obj_to_xml()

    resp, _ = SynHTTPClient().request(
        "POST", endpoint, data=data, headers=headers, sanitize=True)

    if deserialize_format == 'json':
        _data = resp.json()['papi:methodValidation']
    else:
        _data = xmltodict.parse(resp.data())['ns3:methodValidation']

    validation = models.MethodValidation._dict_to_obj(_data)
    methodValidations[validation.methodValidationId] = validation

    return validation


def get_one_methodValidationId():
    if not methodValidations:
        return create_methodValidation().methodValidationId
    return methodValidations.items()[0][0]


def get_one_methodValidation():
    if not methodValidations:
        return create_methodValidation()
    return methodValidations.items()[0][1]


@memoize
def list_payments(ran=CONF.rax_payment_system.ran,
                  serialize_format='json',
                  deserialize_format='json'):

    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/%s/payments" % ran)

    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)

    if deserialize_format == 'json':
        _payments = resp.json()['payments']['payment']
    else:
        _payments = xmltodict.parse(resp.data())['ns1:payments']

    payments = {}
    for p in _payments:
        payments[p['id']] = models.Payment._dict_to_obj(p)
    return payments


def get_one_paymentId():
    return list_payments().items()[0][0]


def get_one_payment():
    return list_payments().items()[0][1]


def create_payment(ran=CONF.rax_payment_system.ran,
                   serialize_format='json',
                   deserialize_format='json',
                   model=None,
                   **kwargs):
    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['content-type'] = 'application/%s' % serialize_format
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/{0}/payments".format(ran))

    if not model:
        model = models.Payment(**kwargs)

    if serialize_format == 'json':
        data = model._obj_to_dict()
    else:
        data = model._obj_to_xml()

    resp, _ = SynHTTPClient().request(
        "POST", endpoint, data=data, headers=headers, sanitize=True)

    if deserialize_format == 'json':
        resp_data = resp.json()['papi:payment']
    else:
        resp_data = xmltodict.parse(resp.data())['ns2:payment']

    return models.Payment._dict_to_obj(resp_data)


@memoize
def list_voids(ran=CONF.rax_payment_system.ran,
               serialize_format='json',
               deserialize_format='json'):
    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/payments/%s/voids" % get_one_paymentId())

    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)

    if deserialize_format == 'json':
        _voids = resp.json()['voids']['void']
    else:
        _voids = xmltodict.parse(resp.data())['ns1:voids']

    voids = {}
    for v in _voids:
        voids[v['id']] = models.Void._dict_to_obj(v)
    return voids


def get_one_voidId():
    return list_voids().items()[0][0]


def get_one_void():
    return list_voids().items()[0][1]


def create_void(paymentId,
                serialize_format='json',
                deserialize_format='json',
                model=None,
                **kwargs):
    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['content-type'] = 'application/%s' % serialize_format
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/payments/{0}/voids".format(paymentId))

    if not model:
        model = models.Void(**kwargs)

    if serialize_format == 'json':
        data = model._obj_to_dict()
    else:
        data = model._obj_to_xml()

    resp, _ = SynHTTPClient().request(
        "POST", endpoint, data=data, headers=headers, sanitize=True)

    if deserialize_format == 'json':
        resp_data = resp.json()['papi:void']
    else:
        resp_data = xmltodict.parse(resp.data())['ns3:void']

    return models.Void._dict_to_obj(resp_data)


@memoize
def list_refunds(ran=CONF.rax_payment_system.ran,
                 serialize_format='json',
                 deserialize_format='json'):
    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/%s/refunds" % ran)

    resp, _ = SynHTTPClient().request(
        "GET", endpoint, headers=headers, sanitize=True)

    if deserialize_format == 'json':
        _refunds = resp.json()['refunds']['refund']
    else:
        _refunds = xmltodict.parse(resp.data())['ns1:refunds']
    refunds = {}
    for r in _refunds:
        refunds[r['id']] = models.Refund._dict_to_obj(r)
    return refunds


def get_one_refundId():
    return list_refunds().items()[0][0]


def get_one_refund():
    return list_refunds().items()[0][1]


def create_refund(ran,
                  serialize_format='json',
                  deserialize_format='json',
                  model=None,
                  **kwargs):
    headers = {}
    headers['accept'] = 'application/%s' % deserialize_format
    headers['content-type'] = 'application/%s' % serialize_format
    headers['x-auth-token'] = get_token()

    endpoint = urlparse.urljoin(
        CONF.syntribos.endpoint,
        "/v1/accounts/{0}/refunds".format(ran))

    if not model:
        model = models.Void(**kwargs)

    if serialize_format == 'json':
        data = model._obj_to_dict()
    else:
        data = model._obj_to_xml()

    resp, _ = SynHTTPClient().request(
        "POST", endpoint, data=data, headers=headers, sanitize=True)

    if deserialize_format == 'json':
        resp_data = resp.json()['papi:refund']
    else:
        resp_data = xmltodict.parse(resp.data())['ns2:refund']

    return models.Refund._dict_to_obj(resp_data)
