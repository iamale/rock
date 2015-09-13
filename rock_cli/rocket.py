import uuid
import requests

__version__ = "0.0.1"

class Rocket:
  def __init__(self, device_id=None, token=None):
    self.token = token
    self.device_id = device_id or self.generate_id()

  @staticmethod
  def generate_id(namespace="SCIENCE"):
    return "%s_%s" % (namespace, hex(uuid.getnode()).replace("0x", ""))

  def request(self, method, url, headers=None, json=None, **kw):
    headers = headers or {}
    json = json or {}

    if not url.startswith(("http://", "https://")):
        url = "https://rocketbank.ru/api/v4/" + url

    headers['x-device-id'] = self.device_id
    headers['x-device-os'] = "RocketScience %s" % __version__
    headers['x-app-version'] = "2.1.0"
    headers['x-device-type'] = "Ale RocketScience_%s" % __version__

    if self.token:
      json['token'] = self.token

    r = requests.request(method, url, data=json, headers=headers, **kw)
    try:
      resp = r.json()['response']
    except:
      resp = {
        'description': "Unknown error",
        'status': r.status_code,
        'code': "UNKNOWN"
      }

    if r.status_code != requests.codes.ok:
      raise RocketException(
        description=resp['description'],
        status=resp['status'],
        code=resp['code'])

    return r

  def head(self, *a, **kw):   return self.request("HEAD", *a, **kw)
  def get(self, *a, **kw):    return self.request("GET", *a, **kw)
  def post(self, *a, **kw):   return self.request("POST", *a, **kw)
  def put(self, *a, **kw):    return self.request("PUT", *a, **kw)
  def patch(self, *a, **kw):  return self.request("PATCH", *a, **kw)
  def delete(self, *a, **kw): return self.request("DELETE", *a, **kw)

  def register(self, phone):
    r = self.post(
      "https://rocketbank.ru/api/v4/devices/register",
      json={'phone': phone})
    id = r.json()['sms_verification']['id']
    return RocketSmsVerification(id, self)

  def login(self, email, password):
    """
    email == привязанный email
    password == "рокеткод" / код, вводимый при открытии
    """
    r = self.get(
      "https://rocketbank.ru/api/v4/login",
      json={
        'email': email,
        'password': password
      })
    j = r.json()

    if 'token' in j:
      self.email = email
      self.password = password
      self.token = j['token']

    return j

  def tariffs(self):
    r = self.get("https://rocketbank.ru/api/v4/tariffs")
    for j in r.json():
      yield RocketTariff(j)

  @property
  def balance(self):
      return self._feed.balance

  @property
  def operations(self):
    return self._feed.operations


class RocketException(Exception):
  def __init__(self, description, status, code):
    self.description = description
    self.status = status
    self.code = code

  def __str__(self):
    return self.description


class RocketSmsVerification:
  def __init__(self, id, rocket):
    self.id = id
    self.rocket = rocket

  def verify(self, code):
    r = self.rocket.patch(
      "https://rocketbank.ru/api/v4/sms_verifications/%s/verify" % self.id,
      json={'code': code})
    j = r.json()

    if 'token' in j:
      self.rocket.token = j['token']

    return j

  def __repr__(self):
    return "<RocketSmsVerification '%s'>" % self.id