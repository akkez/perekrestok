import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup


class Deer:
	def __init__(self, url, email, pay_agent):
		self.url = url
		self.email = email
		self.items = dict()
		self.csrf_token = ''
		self.session = requests.Session()
		self.pay_agent = pay_agent  # type: PayAgent

	def _request(self, url, method, **kwargs):
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2950.0 Safari/537.36',
			'Referer': self.url,
		}
		if 'headers' in kwargs:
			kwargs['headers'].update(headers)
		else:
			kwargs['headers'] = headers

		return self.session.request(method=method, url=url, **kwargs)  # proxies={'http': '127.0.0.1:8888'}

	def list_items(self):
		r = self._request(self.url, 'get')
		soup = BeautifulSoup(r.content, features='html.parser')
		parts = []
		match = re.search(r'name="csrf_token" value="([0-9a-f]+)"', r.text)
		if match:
			self.csrf_token = match.group(1)

		self.items = dict()
		for item in filter(lambda a: 'data-count' in a.attrs, soup.find_all('tr')):
			data = item['data-pricerub'], item['data-count'], item['data-title'], item['data-id'], item['data-mincount']
			cost, count, title, item_id, mincount = data
			shopid = item['data-shopid'] if 'data-shopid' in item.attrs else None
			title = re.sub(r'(\( Перекрёсток \)|Perekrestok.ru| - )', '', title).strip()

			part = self.items[item_id] = dict(cost=cost, title=title, count=count, shopid=shopid, mincount=mincount)
			parts.append(dict(title='{title} / {cost}₽ / {count} шт'.format(**part), id=item_id))

		return parts

	def buy(self, id, count):
		# account = '9103450347:333555	| Balance:	1502'
		# return dict(content=account)

		if id not in self.items:
			self.list_items()
		order = self._request('{}order/'.format(self.url), 'post', headers={
			'Origin': self.url,
			'X-Requested-With': 'XMLHttpRequest',
		}, data={
			'csrf_token': self.csrf_token,
			'email': self.email,
			'count': count,
			'paymethod': 'yandex',
			'type': id,
			'shop': self.items[id]['shopid']
		})
		data = json.loads(order.text)
		form_data = dict()
		purse = None
		comment = None
		if 'order' not in data:
			return dict(error='; '.join(data['errors'].values()))

		for line in data['order'].split('\n'):
			row = dict(re.findall(r' (data-pay-type|name|value)="([^"]+)"', line))
			if len(row) > 0:
				if 'name' in row:
					form_data[row['name']] = row['value']
				if '#' in row['value'] or ('order' in form_data and form_data['order'] in row['value']):
					comment = row['value']
				if 'data-pay-type' in row:
					purse = row['value']
		logging.info("purse={} comment={} form={}".format(purse, comment, form_data))

		try:
			num_cost = float(self.items[id]['cost'])
		except:
			return dict(error="Цена не является числом: {}".format(self.items[id]['cost']))

		self.pay_agent.send_payment(purse=purse, comment=comment, amount=num_cost * count)

		for attempt in range(5):
			time.sleep(5)
			payment_result = self._check_payment(form_data)
			if 'error' in payment_result:
				logging.info("Failed check #{}: {}".format(attempt, payment_result))
			else:
				logging.info("Successful payment: {}".format(payment_result))
				break

		if 'error' in payment_result:
			return payment_result
		if 'url' not in payment_result:
			return dict(error='Не удалось получить купленный товар: {}'.format(payment_result))

		url = payment_result['url']
		item = self._request(url, 'get')
		return dict(content=item.text)

	def _check_payment(self, form_data):
		response = self._request('{}pay/'.format(self.url), 'post', headers={
			'Origin': self.url,
			'X-Requested-With': 'XMLHttpRequest',
		}, data=form_data)
		data = json.loads(response.text)

		if 'csrf' in data:
			self.csrf_token = data['csrf']
		if 'errors' in data:
			return dict(error='; '.join(data['errors'].values()))
		logging.info("Received item: {}".format(data))
		return data
