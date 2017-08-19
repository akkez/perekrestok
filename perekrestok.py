import json
import logging

import requests


class Perekrestok:
	def __init__(self, login, password):
		self.login = login
		self.password = password
		self.balance = 0
		self.session = requests.Session()
		self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2950.0 Safari/537.36'
		self.post_headers = dict()
		self.is_logged = False

		self.session.headers.update({
			'User-Agent': self.user_agent,
			'Referer': 'https://my.perekrestok.ru/',
			'Origin': 'https://my.perekrestok.ru/',
			'Accept-Language': 'en-US,en;q=0.8',
		})
		# self.session.proxies = dict(http='127.0.0.1:8888', https='127.0.0.1:8888')
		# self.session.verify = False

	def _handshake(self):
		h = self.session.post('https://my.perekrestok.ru/api/v3/startup/handshake', json={
			"version": "1", "app": {"version": "1", "platform": "web", "user_agent": self.user_agent}
		})
		hs = json.loads(h.text)
		logging.info("Handshake: {}".format(hs))
		token = hs['server']['features']['security/session']['token']['value']
		bearer = 'Bearer {}'.format(token)
		self.post_headers = {'X-Authorization': bearer}
		self.session.cookies['token'] = bearer.replace(" ", "%20")
		self.session.cookies['header_name'] = 'X-Authorization'

	def auth(self):
		r = self.session.get('https://my.perekrestok.ru/', headers=dict(Origin=None))

		self._handshake()

		r = self.session.get('https://my.perekrestok.ru/api/v1/users/self')
		logging.info("Self not-logged: c={} {}".format(r.status_code, r.text))

		r = self.session.post('https://my.perekrestok.ru/api/v1/logout', headers=self.post_headers)
		logging.info("Logout not-logged: c={} {}".format(r.status_code, r.text))

		self._handshake()

		r = self.session.post('https://my.perekrestok.ru/api/v3/sessions/phone/establish', headers=self.post_headers, json={
			"password": self.password, "token": "", "request_id": "", "phone_no": self.login
		})
		auth_data = json.loads(r.text)
		logging.info("Auth: c={} {}".format(r.status_code, auth_data))

		if 'error' in auth_data:
			return dict(ok=False, error=auth_data['error']['title'])

		self.is_logged = True

		r = self.session.get('https://my.perekrestok.ru/api/v1/users/self', headers={**self.post_headers, 'Origin': None})
		logging.info("Self logged: c={} {}".format(r.status_code, json.loads(r.text)))

		r = self.session.get('https://my.perekrestok.ru/api/v1/balances', headers=self.post_headers)
		bl = json.loads(r.text)
		self.balance = sum(map(lambda x: x['balance']['amount'], bl['data']['balance_list'])) // 100
		logging.info("Balance: c={} b={} {}".format(r.status_code, self.balance, bl))

		return dict(ok=True, balance=self.balance)

	def change_password(self, new_password):
		if not self.is_logged:
			return False

		r = self.session.post('https://my.perekrestok.ru/api/v1/change_password', headers={
			**self.post_headers,
			'Referer': 'https://my.perekrestok.ru/profile'
		}, json={"old_pass": self.password, "new_pass": new_password})
		logging.info("Password changed? c={} {}".format(r.status_code, r.text))

		return r.status_code == 200