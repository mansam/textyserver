#!/usr/bin/env python
from textyserver.resources.user import TextyUser
from skydrive import api_v5, conf
from pyshorturl import Googl
import multiprocessing
import boto
import logging
import signal
import json
import skydrive
import urllib2
import os
import time
from time import localtime, strftime

CLIENT_ID = boto.config.get("Skydrive", "client_id")
CLIENT_SECRET = boto.config.get("Skydrive", "client_secret")
DISPLAY_CUTOFF = boto.config.get("Texty", "display_cutoff", 5)
BACKOFF_STEP = 1
BACKOFF_MAX = 20
MAX_MESSAGE_LENGTH = 160

class Worker(multiprocessing.Process):

	def __init__(self):
		super(Worker, self).__init__()

		self.sqs = boto.connect_sqs()
		self.text_queue = self.sqs.lookup('texts')
		self.log = logging.getLogger('texty.workers')
		self.running = True
		self.backoff_level = 0
		self.VALID_COMMANDS = {
			"get": self.ls_command,
			"find": self.ls_command,
			"f": self.ls_command,
			"ls": self.ls_command,
			"download": self.download_command,
			"dl": self.download_command,
			"space": self.quota_command,
			"quota": self.quota_command,
			"q": self.quota_command,
			"findall": lambda sd, user, args: self.ls_command(sd, user, args, display_more=True),
			"note": self.note_command,
			"n": self.note_command,
			"?": self.help_command,
			"hlp": self.help_command
		}	
		
	def run(self):

		while self.running:

			msg = self.text_queue.read()
			if msg:
				self.backoff_level = 0
				# Create and set up the connection to SkyDrive
				# client_secret and client_id do not change from user to user
				sd = skydrive.api_v5.SkyDriveAPI()
				sd.client_id = CLIENT_ID
				sd.client_secret = CLIENT_SECRET
				
				#Consists of a phone number and a text message body
				body = json.loads(msg.get_body())

				phone_num = body[0]
				txt = body[1].split(' ', 1)

				command = txt[0].lower()
				if len(txt) > 1:
					args = txt[1]
				else:
					args = ""

				try:
					user = TextyUser.find(phone=phone_num).next()
					sd.auth_access_token = user.auth_token
					sd.auth_refresh_token = user.refresh_token

					if command in self.VALID_COMMANDS:
						self.log.info(command)
						return_msg = self.VALID_COMMANDS[command](sd, user, args)

					elif command.isdigit():
						return_msg = self.choose_command(sd, user, command)
					else:
						return_msg = 'Error: Command not found or incorrectly formated'
					try:
						self.log.info(return_msg)
						if len(return_msg) >= MAX_MESSAGE_LENGTH:
							messages = self.split_message(return_msg)
							for message in messages:
								user.sms(message)
						else:
							user.sms(return_msg)
					except:
						# failed to send message
						self.log.exception('Failed sending sms to %s.' % phone_num)

				except StopIteration:
					self.log.info("Didn't recognize number: %s" % phone_num)
				except:
					import traceback
					traceback.print_exc()
				
				self.text_queue.delete_message(msg)
			else:
				if self.backoff_level < BACKOFF_MAX:
					self.backoff_level += BACKOFF_STEP
				self.log.info("Sleeping %d seconds." % self.backoff_level)
				time.sleep(self.backoff_level)



	def download_command(self, sd, user, args):
		split_url = args.split('/') 
		upload_name = split_url[len(split_url)-1] #name it will be given on the skydrive
		downloaded_file = urllib2.urlopen(args)
		data = downloaded_file.read()
		downloaded_file.close()
		sd.put((upload_name, data), 'me/skydrive')
		return "Downloaded %s to skydrive." % upload_name

	def shorten_link(self, link):
		shortener = Googl()
		return shortener.shorten_url(link)

	def bitly_link(self, link):
		from pyshorturl import Bitly, BitlyError
		bitly = Bitly(boto.config.get("bitly", "username"), boto.config.get('bitly', "api_key"))
		return bitly.shorten_url(link)

	def quota_command(self, sd, user, args):
		ans = sd.get_quota()
		return 'You have %f GB availible out of %f GB total' % (ans[0]/float(1000000000), ans[1]/float(1000000000))		

	def choose_command(self, sd, user, number):
		return_msg = ""
		try:
			selection = int(number)
			if (0 < selection <= len(user.requested_files)):
				return_msg = self.bitly_link(sd.link(user.requested_files[selection-1])['link'])
				user.requested_files = []
				user.put()
		except:
			return_msg = "Error: Invalid selection"  
		return return_msg

	def ls_command(self, sd, user, args, display_more=False):
		results = self.traverse(sd, 'me/skydrive', args.lower())

		if len(results['file_names']) == 0:
			return "No files found."

		# Exactly 1 match found, return the shortened URL
		elif len(results['file_names']) == 1:
			self.log.info(results['file_names'])
			return self.bitly_link(sd.link(results['file_ids'][0])['link'])

		# Multiple results found, send them to the user so he/she can pick
		elif len(results['file_names']) < DISPLAY_CUTOFF or display_more:
			return_msg = self.generate_menu(results['file_names'])
			user.requested_files = results['file_ids']
			user.put()
			return return_msg

		# A lot of results found, tell the user to refine the search
		else:
			return_msg = "Search returned %d files. Narrow your search, or text \'findall %s\' to show all results" % (len(results['file_names']), args)
			user.requested_files = results['file_ids']
			user.put()
			return return_msg

	def note_command(self, sd, user, args):
		file_name = 'note_'+strftime("%Y%m%d%H%M%S", localtime())+'.txt'
		self.log.info('in note_command using file name: %s' % file_name)
		self.log.info('in note_command using args: %s' % args)
		sd.put((file_name, args), 'me/skydrive')
		return "Wrote note %s to skydrive." % file_name.split('/')[-1]

	def generate_menu(self, file_names):
		menu = 'Enter # of selection: \n'
		for i in range(0, len(file_names)):
			option = '#%d. %s\n' % (i + 1, file_names[i])
			menu += option
		return menu

	def help_command(self, sd, user, args):
		help_msg = "find <files> - get link\nnote <some text> - write note\ndl <remote file link> - downld file\nspace - get remaining space"
		return help_msg

	def traverse(self, sd, path, searchTerm):
		file_names = []
		file_ids = []
		self.log.info(path)
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

	def split_message(self, sms_message):
		import math
		message_segments = []
		seg_len = MAX_MESSAGE_LENGTH - 20
		chunks = int(math.ceil(len(sms_message)/float(seg_len)))
		for i in range(0, chunks):
			segment = sms_message[seg_len*i:seg_len*(i+1)]
			segment += "(%d of %d)" % (i+1, chunks)
			message_segments.append(segment)
		return message_segments

if __name__ == "__main__":
	workers = []
	num_workers = int(boto.config.get("Texty", "number_workers", 1))
	for i in range(0, num_workers):
		w = Worker()
		w.start()
		workers.append(w)

