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
						if len(results['fileNames']) == 1:
							self.log.info(results['fileNames'])
							return_msg = shortener.shorten_url(sd.link(results['fileIDs'][0])['link'])
						elif len(results['fileNames']) < 5:
							return_msg = 'Type "choose X" to select:\n'
							for a in range(len(results['fileNames'])):
								a = '%d. %s' % (a+1, results['fileNames'][a] + '\n')
								return_msg += a
							self.log.info(user.requested_files)
							user.requested_files = results['fileIDs']
							user.put()
							self.log.info(user.requested_files)
						else:
							return_msg = "Search returned %d results. Please narrow your search." % len(results['fileNames'])

					# allow selecting from menu of files
					elif split_txt[0] == 'choose' and len(split_txt) == 2 and len(user.requested_files):
						try:
							selection = int(split_txt[1])
							if (0 < selection <= len(user.requested_files)):
								return_msg = shortener.shorten_url(sd.link(results['fileIDs'][selection-1])['link'])
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
	

	#Traverses the SkyDrive, starting from the location given by path.
	def traverse(self, sd, path, searchTerm, filesFound = [], filesFoundIDs = []):
		ls = sd.listdir(path)
		for a in range(len(ls)):
			if ls[a]['type'] == u'folder':
				garbage = self.traverse(ls[a]['id'], searchTerm, filesFound, filesFoundIDs)
			elif ((ls[a]['name'].lower()).find(searchTerm) != -1) and (ls[a]['type'] == u'file'):

				self.log.info('Appending files found.')
				filesFound.append(ls[a]['name'])
				filesFoundIDs.append(ls[a]['id'])
				self.log.info(filesFoundIDs)
		return {'fileNames':filesFound, 'fileIDs':filesFoundIDs}


if __name__ == "__main__":

	w = Worker()
	w.start()
