#!/usr/bin/env python
from textyserver.resources.user import TextyUser
import multiprocessing
import boto
import logging
import signal
import json
import skydrive
import urllib
from skydrive import api_v5, conf
from pyshorturl import Googl

CLIENT_ID = boto.config.get("Skydrive", "client_id")
CLIENT_SECRET = boto.config.get("Skydrive", "client_secret")

class Worker(multiprocessing.Process):

	def __init__(self):
		super(Worker, self).__init__()

		self.sqs = boto.connect_sqs()
		self.text_queue = self.sqs.lookup('texts')
		self.log = logging.getLogger('texty.workers')
		self.running = True

	def run(self):
		
		shortener = Googl()

		while self.running:

			msg = self.text_queue.read()
			if msg:
				# Create and set up the connection to SkyDrive
				# client_secret and client_id do not change from user to user
				sd = skydrive.api_v5.SkyDriveAPI()
				sd.client_id = CLIENT_ID
				sd.client_secret = CLIENT_SECRET
				
				#Consists of a phone number and a text message body
				body = json.loads(msg.get_body())
				phone_num = body[0]
				txt = body[1]
				split_txt = txt.split(' ', 1)
				self.log.info(split_txt)
				return_msg = "No files found."

				try:
					user = TextyUser.find(phone=phone_num).next()
					sd.auth_access_token = user.auth_token
					sd.auth_refresh_token = user.refresh_token

					# parse text commands
					if split_txt[0] == 'get' and len(split_txt) == 2:

						results = []
						results = self.traverse(sd, 'me/skydrive', split_txt[1].lower())
						self.log.info(results)

						# Exactly 1 match found, return the shortened URL
						if len(results['file_names']) == 1:
							self.log.info(results['file_names'])
							return_msg = shortener.shorten_url(sd.link(results['file_ids'][0])['link'])
						elif len(results['file_names']) < 5:
							return_msg = 'Type "choose X" to select:\n'
							for a in range(len(results['file_names'])):
								a = '%d. %s' % (a+1, results['file_names'][a] + '\n')
								return_msg += a
							self.log.info(user.requested_files)
							user.requested_files = results['file_ids']
							user.put()
							self.log.info(user.requested_files)
						else:
							return_msg = "Search returned %d results. Please narrow your search." % len(results['file_names'])

					# allow selecting from menu of files
					elif split_txt[0] == 'choose' and len(split_txt) == 2 and len(user.requested_files):
						try:
							selection = int(split_txt[1])
							if (0 < selection <= len(user.requested_files)):
								return_msg = shortener.shorten_url(sd.link(results['file_ids'][selection-1])['link'])
							user.requested_files = []
							user.put()
						except:
							return_msg = "Error: Invalid selection"


					else:
						return_msg = 'Error: Command not found or incorrectly formated'
					try:
						self.log.info(return_msg)
						user.sms(return_msg)
					except:
						# failed to send message
						self.log.exception('Failed sending sms to %s.' % phone_num)
				except StopIteration:
					self.log.info("Didn't recognize number: %s" % phone_num)
				
				self.text_queue.delete_message(msg)

	#Helps a user find a file
	def findFile(self, searchTerm, user):
		print 'blah'

	def traverse(self, sd, path, searchTerm):
		file_names = []
		file_ids = []
		files = sd.listdir(path)
		for f in files:
			if f['type'] == 'folder':
				results_dict = self.traverse(sd, f['id'], searchTerm)
				file_names += results_dict["file_names"]
				file_ids += results_dict["file_ids"]
			elif f['name'].lower().find(searchTerm) != -1:
				self.log.info('Found %s.' % f['name'])
				file_names.append(f['name'])
				file_ids.append(f['id'])
		return {'file_names':file_names, 'file_ids': file_ids}

if __name__ == "__main__":
	workers = []
	num_workers = int(boto.config.get("Texty", "number_workers", 1))
	for i in range(0, num_workers):
		w = Worker()
		w.start()
		workers.append[w]