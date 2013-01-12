#!/usr/bin/env python
from textyserver.resources.user import TextyUser
import multiprocessing
import boto
import logging

class Worker(multiprocessing.Process):

	def __init__(self, *args):
		super(Worker, self).__init__(args)
		self.sqs = boto.connect_sqs()
		self.text_queue = sqs.lookup('texts')
		self.log = logging.getLogger('texty.workers')

	def run(self):

		while running:

			msg = self.text_queue.read()
			if msg:
				phone_num, body = msg.get_body()
				user = TextyUser.find(number=phone_num).next()
				user.sms('got your message')
			else:
				self.log('Waiting.')

if __name__ == "__main__":

	w = Worker()
	w.start()
