#!/usr/bin/env python
from textyserver.resources.user import TextyUser
import multiprocessing
import boto
import logging
import signal
import json
import skydrive
from skydrive import api_v5, conf


class Worker(multiprocessing.Process):

	def __init__(self, client_id, client_secret):
		super(Worker, self).__init__()

		#Create and set up the connection to SkyDrive
		#client_secret and client_id do not change from user to user
		self.sd = skydrive.api_v5.SkyDriveAPI()
		self.sd.client_id = client_id
		self.sd.client_secret = client_secret

		self.sqs = boto.connect_sqs()
		self.text_queue = self.sqs.lookup('texts')
		self.log = logging.getLogger('texty.workers')
		self.running = True

	def run(self):

		while self.running:

			msg = self.text_queue.read()
			if msg:
				#Consists of a phone number and a text message body
				body = json.loads(msg.get_body())
				phone_num = body[0]
				txt = body[1]
				split_txt = txt.split(' ')
				
				if split_txt[0] == 'get' and len(split_txt) == 2:
					results = traverse(split_txt[1])
					if len(results['fileNames']) == 1:
						return_msg = results['fileNames'][0]
					elif len(results['fileNames'] < 5
						 return_msg = 'Did you mean:\n'
						 for a in range(len(results['fileNames'])):
							 a = a+'%d . ',a+1 + 
					

				else:
					return_msg = 'Error: Command not found or incorrectly formated'
				try:
					user = TextyUser.find(phone=phone_num).next()
					sd.auth_access_token = user.auth_token #also user.refresh_token

					#if confirmation code, set the user to active user.is_active = True and user.put()
					try:
						user.sms(return_msg)
					except:
						# failed to send message
						self.log.exception('Failed sending sms to %s.' % phone_num)
				except StopIteration:
					self.log.info("Didn't recognize number: %s" % phone_num)
				
				self.text_queue.delete_message(msg)
				
			else:
				self.log.info('Waiting.')


	#Traverses the SkyDrive, starting from the location given by path.
	def traverse(path):
		ls = sd.listdir(path)
		for a in range(len(ls)):
			if ls[a]['type'] == u'folder':
				traverse(ls[a]['id'])
			elif ls[a]['name'].find(searchTerm) != -1:
				filesFound.append(ls[a]['name'])
				filesFoundIDs.append(ls[a]['id'])
		return {'fileNames':filesFound, 'fileIDs':filesFoundIDs}


if __name__ == "__main__":

	w = Worker()
	w.start()
