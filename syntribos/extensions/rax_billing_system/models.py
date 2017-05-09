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
import re
import xml.etree.ElementTree as ET

from oslo_config import cfg

logging.basicConfig(level=logging.CRITICAL)
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class BaseBillingSystemModel(object):

    def __init__(self, kwargs):
        super(BaseBillingSystemModel, self).__init__()
        self._log = logging.getLogger(__name__)
        for k, v in kwargs.items():
            if k != "self" and not k.startswith("_"):
                setattr(self, k, v)

    def serialize(self, format_type):
        try:
            serialize_method = '_obj_to_{0}'.format(format_type)
            return getattr(self, serialize_method)()
        except Exception as serialization_exception:
            self._log.error(
                'Error occured during serialization of a data model into'
                'the "%s: \n%s" format',
                format_type, serialization_exception)
            self._log.exception(serialization_exception)

    @classmethod
    def deserialize(cls, serialized_str, format_type):
        if serialized_str and len(serialized_str) > 0:
            try:
                deserialize_method = '_{0}_to_obj'.format(format_type)
                return getattr(cls, deserialize_method)(serialized_str)
            except Exception as deserialization_exception:
                cls._log.exception(deserialization_exception)
                cls._log.debug(
                    "Deserialization Error: Attempted to deserialize type"
                    " using type: {0}".format(format_type.decode(
                        encoding='UTF-8', errors='ignore')))
                cls._log.debug(
                    "Deserialization Error: Unable to deserialize the "
                    "following:\n{0}".format(serialized_str.decode(
                        encoding='UTF-8', errors='ignore')))

    @classmethod
    def _remove_xml_namespaces(cls, element):
        """Prunes namespaces from XML element

        :param element: element to be trimmed
        :returns: element with namespaces trimmed
        :rtype: :class:`xml.etree.ElementTree.Element`
        """
        for key, value in vars(cls._namespaces).items():
            if key.startswith("__"):
                continue
            element = cls._remove_xml_etree_namespace(element, value)
        return element

    @classmethod
    def _json_to_obj(cls, serialized_str):
        data_dict = json.loads(serialized_str, strict=False)
        return cls._dict_to_obj(data_dict)

    @classmethod
    def _xml_to_obj(cls, serialized_str, encoding="iso-8859-2"):
        parser = ET.XMLParser(encoding=encoding)
        element = ET.fromstring(serialized_str, parser=parser)
        return cls._xml_ele_to_obj(cls._remove_xml_namespaces(element))

    def _obj_to_json(self):
        return json.dumps(self._obj_to_dict())

    def _obj_to_xml(self):
        element = self._obj_to_xml_ele()
        element.attrib["xmlns"] = self._namespaces.XMLNS
        return ET.tostring(element)

    # These next two functions must be defined by the child classes before
    # serializing
    def _obj_to_dict(self):
        raise NotImplementedError

    def _obj_to_xml_ele(self):
        raise NotImplementedError

    @staticmethod
    def _find(element, tag):
        """Finds element with tag

        :param element: :class:`xml.etree.ElementTree.Element`, the element
            through which to start searching
        :param tag: the tag to search for
        :returns: The element with tag `tag` if found, or a new element with
            tag None if not found
        :rtype: :class:`xml.etree.ElementTree.Element`
        """
        if element is None:
            return ET.Element(None)
        new_element = element.find(tag)
        if new_element is None:
            return ET.Element(None)
        return new_element

    @staticmethod
    def _build_list_model(data, field_name, model):
        """Builds list of python objects from XML or json data

        If data type is json, will find all json objects with `field_name` as
        key, and convert them into python objects of type `model`.
        If XML, will find all :class:`xml.etree.ElementTree.Element` with
        `field_name` as tag, and convert them into python objects of type
        `model`

        :param data: Either json or XML object
        :param str field_name: json key or XML tag
        :param model: Class of objects to be returned
        :returns: list of `model` objects
        :rtype: `list`
        """
        if data is None:
            return []
        if isinstance(data, dict):
            if data.get(field_name) is None:
                return []
            return [model._dict_to_obj(tmp) for tmp in data.get(field_name)]
        return [model._xml_ele_to_obj(tmp) for tmp in data.findall(field_name)]

    @staticmethod
    def _build_list(items, element=None):
        """Builds json object or xml element from model

        Calls either :func:`item._obj_to_dict` or
        :func:`item.obj_to_xml_ele` on all objects in `items`, and either
        returns the dict objects as a list or appends `items` to `element`

        :param items: list of objects for conversion
        :param element: The element to be appended, or None if json
        :returns: list of dicts if `element` is None or  `element` otherwise.
        """
        if element is None:
            if items is None:
                return []
            return [item._obj_to_dict() for item in items]
        else:
            if items is None:
                return element
            for item in items:
                element.append(item._obj_to_xml_ele())
            return element

    @staticmethod
    def _create_text_element(name, text):
        """Creates element with text data

        :returns: new element with name `name` and text `text`
        :rtype: :class:`xml.etree.ElementTree.Element`
        """
        element = ET.Element(name)
        if text is True or text is False:
            element.text = str(text).lower()
        elif text is None:
            return ET.Element(None)
        else:
            element.text = str(text)
        return element

    def __ne__(self, obj):
        return not self.__eq__(obj)

    @classmethod
    def _remove_empty_values(cls, data):
        """Remove empty values

        Returns a new dictionary based on 'dictionary', minus any keys with
        values that evaluate to False.

        :param dict data: Dictionary to be pruned
        :returns: dictionary without empty values
        :rtype: `dict`
        """
        if isinstance(data, dict):
            return dict(
                (k, v) for k, v in data.items() if v not in (
                    [], {}, None))
        elif isinstance(data, ET.Element):
            if data.attrib:
                data.attrib = cls._remove_empty_values(data.attrib)
            data._children = [
                c for c in data._children if c.tag is not None and (
                    c.attrib or c.text is not None or c._children)]
            return data

    @staticmethod
    def _get_sub_model(model, json=True):
        """Converts object to json or XML

        :param model: Object to convert
        :param boolean json: True if converting to json, false if XML
        """
        if json:
            if model is not None:
                return model._obj_to_dict()
            else:
                return None
        else:
            if model is not None:
                return model._obj_to_xml_ele()
            else:
                return ET.Element(None)


class PaymentMethod(BaseBillingSystemModel):

    def __init__(self,
                 methodId=None,
                 creationDate=None,
                 ran=None,
                 status=None,
                 isDefault=None,
                 modifiedDate=None,
                 methodClass=None,
                 methodClassName=None,
                 addressVerificationInformation=None,
                 level3Eligible=None):
        super(PaymentMethod, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        if 'paymentCard' in data:
            _model_class = PaymentCardMethod
            _model_name = 'paymentCard'
        elif 'electronicCheck' in data:
            _model_class = ACHMethod
            _model_name = 'electronicCheck'
        elif 'ukDirectDebit' in data:
            _model_class = UKDebitMethod
            _model_name = 'ukDirectDebit'
        elif 'sepa' in data:
            _model_class = SEPAMethod
            _model_name = 'sepa'

        _model = _model_class(data.get(_model_name))
        _avi = data.get('addressVerificationInformation')
        return cls(methodId=cls._strip_urn_namespace(data.get('id')),
                   creationDate=data.get('creationDate'),
                   ran=data.get('ran'),
                   status=data.get('status'),
                   isDefault=data.get('isDefault'),
                   modifiedDate=data.get('modifiedDate'),
                   methodClass=_model,
                   methodClassName=_model_name,
                   addressVerificationInformation=_avi,
                   level3Eligible=data.get('level3Eligible'))

    def _obj_to_dict(self):
        if self.methodClassName == 'paymentCard':
            _model_name = 'paymentCard'
        elif self.methodClassName == 'electronicCheck':
            _model_name = 'electronicCheck'
        elif self.methodClassName == 'ukDirectDebit':
            _model_name = 'ukDirectDebit'
        elif self.methodClassName == 'sepa':
            _model_name = 'sepa'

        dic = {}
        dic['addressVerificationInformation'] = \
            self.addressVerificationInformation
        dic[_model_name] = self.methodClass._obj_to_dict()['papi:method']
        return {"method": self._remove_empty_values(dic)}


class PaymentCardMethod(BaseBillingSystemModel):

    def __init__(self,
                 cardVerificationNumber=None,
                 expirationDate=None,
                 cardHolderName=None,
                 cardType=None,
                 cardNumber=None):
        super(PaymentCardMethod, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        return cls(cardVerificationNumber=data.get('cardVerificationNumber'),
                   expirationDate=data.get('expirationDate'),
                   cardHolderName=data.get('cardHolderName'),
                   cardType=data.get('cardType'),
                   cardNumber=data.get('cardNumber'))

    def _obj_to_dict(self):
        dic = {}
        dic['expirationDate'] = self.expirationDate
        dic['cardVerificationNumber'] = self.cardVerificationNumber
        dic['cardHolderName'] = self.cardHolderName
        dic['cardType'] = self.cardType
        dic['cardNumber'] = self.cardNumber
        return {"papi:method": self._remove_empty_values(dic)}


class ACHMethod(BaseBillingSystemModel):

    def __init__(self,
                 accountNumber=None,
                 accountType=None,
                 achPaymentType=None,
                 routingNumber=None,
                 accountHolderName=None):
        super(ACHMethod, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        return cls(accountNumber=data.get('accountNumber'),
                   accountType=data.get('accountType'),
                   achPaymentType=data.get('achPaymentType'),
                   routingNumber=data.get('routingNumber'),
                   accountHolderName=data.get('accountHolderName'))

    def _obj_to_dict(self):
        dic = {}
        dic['accountNumber'] = self.accountNumber
        dic['accountType'] = self.accountType
        dic['achPaymentType'] = self.achPaymentType
        dic['routingNumber'] = self.routingNumber
        dic['accountHolderName'] = self.accountHolderName
        return {"papi:method": self._remove_empty_values(dic)}


class UKDebitMethod(BaseBillingSystemModel):

    def __init__(self,
                 bankSortCode=None,
                 bankNumber=None,
                 accountHolderName=None):
        super(UKDebitMethod, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        return cls(bankSortCode=data.get('bankSortCode'),
                   bankNumber=data.get('bankNumber'),
                   accountHolderName=data.get('accountHolderName'))

    def _obj_to_dict(self):
        dic = {}
        dic['bankSortCode'] = self.bankSortCode
        dic['bankNumber'] = self.bankNumber
        dic['accountHolderName'] = self.accountHolderName
        return {"papi:method": self._remove_empty_values(dic)}


class SEPAMethod(BaseBillingSystemModel):

    def __init__(self,
                 bic=None,
                 iban=None,
                 accountHolderName=None):
        super(SEPAMethod, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        return cls(bic=data.get('bic'),
                   iban=data.get('iban'),
                   accountHolderName=data.get('accountHolderName'))

    def _obj_to_dict(self):
        dic = {}
        dic['bic'] = self.bic
        dic['iban'] = self.iban
        dic['accountHolderName'] = self.accountHolderName
        return {"papi:method": self._remove_empty_values(dic)}


class MethodValidation(BaseBillingSystemModel):

    def __init__(self,
                 methodValidationId=None,
                 validationResults=None,
                 gatewayMessage=None,
                 approvalStatus=None,
                 lineOfBusiness=None,
                 contractEntity=None,
                 currencyCode=None,
                 method=None):
        super(MethodValidation, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        return cls(methodValidationId=data.get('id'),
                   validationResults=data.get('validationResults'),
                   lineOfBusiness=data.get('lineOfBusiness'),
                   gatewayMessage=data.get('gatewayMessage'),
                   contractEntity=data.get('contractEntity'),
                   currencyCode=data.get('currencyCode'),
                   approvadsflStatus=data.get('approvalStatus'),
                   method=PaymentMethod(data.get('method')))

    def _obj_to_dict(self):
        dic = {}
        dic['lineOfBusiness'] = self.lineOfBusiness
        dic['contractEntity'] = self.contractEntity
        dic['currencyCode'] = self.currencyCode
        dic['method'] = self.method._obj_to_dict()
        return {"papi:methodValidation": self._remove_empty_values(dic)}


class MethodAssociation(BaseBillingSystemModel):
    def __init__(self,
                 methodValidationId=None,
                 methodId=None,
                 ran=None):
        super(MethodAssociation, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        return cls(methodValidationId=data.get('methodValidationId'),
                   methodId=data.get('methodId'),
                   ran=data.get('ran'))

    def _obj_to_dict(self):
        dic = {}
        dic['methodValidationId'] = self.methodValidationId
        dic.ran = self.ran
        return {"methodAssociation": self._remove_empty_values(dic)}


class Payment(BaseBillingSystemModel):

    def __init__(self,
                 levelThreeOrderInformation=None,
                 addressVerificationInformation=None,
                 submissionDate=None,
                 submissionId=None,
                 amount=None,
                 comments=None,
                 methodId=None,
                 status=None,
                 gatewayMessage=None):
        super(Payment, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        _ltoi = data.get('levelThreeOrderInformation')
        _avi = data.get('addressVerification')
        _subid = data.get('submissionId')
        _methid = data.get('methodId')
        _gtr = data.get('gatewayTransactionReference')
        return cls(levelThreeOrderInformation=_ltoi,
                   addressVerificationInformation=_avi,
                   submissionDate=data.get('submissionDate'),
                   submissionId=_subid,
                   amount=data.get('amount'),
                   gatewayTransactionReference=_gtr,
                   comments=data.get('comments'),
                   status=data.get('status'),
                   methodId=_methid)

    def _obj_to_dict(self):
        dic = {}
        dic['levelThreeOrderInformation'] = self.levelThreeOrderInformation
        dic['addressVerificationInformation'] = \
            self.addressVerificationInformation
        dic['submissionId'] = self.submissionId
        dic['amount'] = self.amount,
        dic['comments'] = self.comments,
        dic['methodId'] = self.methodId
        return {'papi:payment': self._remove_empty_values(dic)}


class Void(BaseBillingSystemModel):

    def __init__(self,
                 voidId=None,
                 voidAmount=None,
                 comments=None,
                 submissionId=None,
                 gatewayTransactionReference=None,
                 gatewayMessage=None,
                 status=None,
                 submissionDate=None):
        super(Void, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        _subid = data.get('submissionId')
        _gtr = data.get('gatewayTransactionReference')
        return cls(voidId=data.get('id'),
                   status=data.get('status'),
                   gatewayTransactionReference=_gtr,
                   gatewayMessage=data.get('gatewayMessage'),
                   voidAmount=data.get('voidAmount'),
                   comments=data.get('comments'),
                   submissionId=_subid,
                   submissionDate=data.get('submissionDate'))

    def _obj_to_dict(self):
        dic = {}
        dic['voidAmount'] = self.voidAmount
        dic['comments'] = self.comments
        dic['submissionId'] = self.submissionId
        return {'papi:void': self._remove_empty_values(dic)}


class Refund(BaseBillingSystemModel):

    def __init__(self,
                 refundId=None,
                 refundAmount=None,
                 comments=None,
                 submissionId=None,
                 status=None,
                 submissionDate=None,
                 gatewayTransactionReference=None,
                 gatewayMessage=None,
                 methodId=None):
        super(Refund, self).__init__(locals())

    @classmethod
    def _dict_to_obj(cls, data):
        _subid = cls._strip_urn_namespace(data.get('submissionId'))
        _gtr = data.get('gatewayTransactionReference')
        _methid = cls._strip_urn_namespace(data.get('methodId'))
        return cls(refundId=data.get('id'),
                   refundAmount=data.get('refundAmount'),
                   comments=data.get('comments'),
                   submissionId=_subid,
                   status=data.get('status'),
                   submissionDate=data.get('submissionDate'),
                   gatewayTransactionReference=_gtr,
                   gatewayMessage=data.get('gatewayMessage'),
                   methodId=_methid)

    def _obj_to_dict(self):
        dic = {}
        dic['refundAmount'] = self.refundAmount
        dic['comments'] = self.comments,
        dic['submissionId'] = self.submissionId
        return {'papi:refund': self._remove_empty_values(dic)}
