#!/usr/bin/env python
from textyserver.resources.user import TextyUser
import multiprocessing
import boto
import logging
import signal

class Worker(multiprocessing.Process):

	def __init__(self):
		super(Worker, self).__init__()
		self.sqs = boto.connect_sqs()
		self.text_queue = self.sqs.lookup('texts')
		self.log = logging.getLogger('texty.workers')
		self.running = True

	def run(self):

		while self.running:

			msg = self.text_queue.read()
			if msg:
				body = msg.get_body()
				phone_num = body[0]
				txt = body[1]
				user = TextyUser.find(number=phone_num).next()
				user.sms('got your message')
			else:
				self.log.info('Waiting.')

if __name__ == "__main__":

	w = Worker()
	w.start()
