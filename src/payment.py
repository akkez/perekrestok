import json
import logging
import requests


class PayAgent:
	def send_payment(self, purse, comment, amount):
		raise NotImplemented()


class YandexAgent(PayAgent):
	def __init__(self, token):
		self.token = token

	def send_payment(self, purse, comment, amount):
		request_data = {
			"pattern_id": "p2p",
			"to": purse,
			"amount_due": str(amount),
			"comment": comment,
			"message": comment
		}
		request_payment = requests.post(
			"https://money.yandex.ru/api/request-payment",
			headers={'Authorization': 'Bearer {token}'.format(token=self.token)},
			data=request_data
		)
		data = json.loads(request_payment.text)
		logging.info("RequestPayment: {}".format(request_payment.text))
		transfer_id = data['request_id']
		# logging.info("Transfer id: {}".format(transfer_id))

		process_payment = requests.post(
			"https://money.yandex.ru/api/process-payment",
			headers={'Authorization': 'Bearer {token}'.format(token=self.token)},
			data={"request_id": transfer_id}
		)
		data2 = json.loads(process_payment.text)
		logging.info("PaymentResult: {}".format(data2))
