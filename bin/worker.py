#!/usr/bin/env python
from textyserver.resources.user import TextyUser
import multiprocessing
import boto
import logging
import signal
import json

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
				body = json.loads(msg.get_body())
				phone_num = body[0]
				txt = body[1]
				try:
					user = TextyUser.find(phone=phone_num).next()
					try:
						user.sms('Got your message.')
					except:
						# failed to send message
						self.log.exception('Failed sending sms to %s.' % phone_num)
				except StopIteration:
					self.log.info("Didn't recognize number: %s" % phone_num)
				
				self.text_queue.delete_message(msg)
				
			else:
				self.log.info('Waiting.')

if __name__ == "__main__":

	w = Worker()
	w.start()
