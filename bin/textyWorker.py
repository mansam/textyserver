#!/usr/bin/env python
from textyserver.resources.user import TextyUser
from time import localtime, strftime
from pyshorturl import Googl
import liveconnect.skydrive
import multiprocessing
import urllib2
import logging
import boto
import json
import time

DISPLAY_CUTOFF = boto.config.get("Texty", "display_cutoff", 5)
BACKOFF_STEP = 1
BACKOFF_MAX = 20
MAX_MESSAGE_LENGTH = 160

def refresh(function):
	"""
	Function decorator for automatically refreshing
	user authorization.  Requires that the user
	object be the first argument passed to the 
	wrapped function.

	"""

	def wrapper(*args, **kwargs):
		user = args[1]
		try:
			return function(*args, **kwargs)
		except:
			user.refresh_authorization()
			return function(*args, **kwargs)

	return wrapper

class Worker(multiprocessing.Process):

	def __init__(self):
		super(Worker, self).__init__()

		self.sd = liveconnect.skydrive.connect_skydrive()
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
			# "download": self.download_command,
			# "dl": self.download_command,
			"space": self.quota_command,
			"quota": self.quota_command,
			"q": self.quota_command,
			"findall": lambda user, args: self.ls_command(user, args, display_more=True),
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
					if user.is_active:
						if command in self.VALID_COMMANDS:
							self.log.info(command)
							return_msg = self.VALID_COMMANDS[command](user, args)

						elif command.isdigit():
							return_msg = self.choose_command(user, command)
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
				finally:
					self.text_queue.delete_message(msg)
			else:
				if self.backoff_level < BACKOFF_MAX:
					self.backoff_level += BACKOFF_STEP
				self.log.info("Sleeping %d seconds." % self.backoff_level)
				time.sleep(self.backoff_level)

	@refresh
	def download_command(self, user, args):
		split_url = args.split('/') 
		upload_name = split_url[len(split_url)-1] #name it will be given on the skydrive
		downloaded_file = urllib2.urlopen(args)
		downloaded_file.close()
		self.sd.put(name=upload_name, fobj=downloaded_file, access_token=user.auth_token)
		return "Downloaded %s to skydrive." % upload_name

	def shorten_link(self, link):
		shortener = Googl()
		return shortener.shorten_url(link)

	def bitly_link(self, link):
		from pyshorturl import Bitly
		bitly = Bitly(boto.config.get("bitly", "username"), boto.config.get('bitly', "api_key"))
		return bitly.shorten_url(link)

	@refresh
	def quota_command(self, user, args):
		ans = self.sd.get_quota(access_token=user.auth_token)
		return 'You have %f GB availible out of %f GB total' % (ans['available']/float(1000000000), ans['quota']/float(1000000000))		

	@refresh
	def choose_command(self, user, number):
		return_msg = "Error: Invalid selection."
		try:
			selection = int(number)
		except:
			return return_msg

		if (0 < selection <= len(user.requested_files)):
			share_link = self.sd.get_share_link(user.requested_files[selection-1], access_token=user.auth_token)
			return_msg = self.bitly_link(share_link)
			user.requested_files = []
			user.put()

		return return_msg

	@refresh
	def ls_command(self, user, args, display_more=False):
		results = self.traverse(user, 'me/skydrive', args.lower())

		if len(results['file_names']) == 0:
			return "No files found."

		# Exactly 1 match found, return the shortened URL
		elif len(results['file_names']) == 1:
			self.log.info(results['file_names'])
			return self.bitly_link(self.sd.get_share_link(file_id=results['file_ids'][0], access_token=user.auth_token))

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

	@refresh
	def note_command(self, user, args):
		from StringIO import StringIO
		file_name = 'note_'+strftime("%Y%m%d%H%M%S", localtime())+'.txt'
		self.log.info('in note_command using file name: %s' % file_name)
		self.log.info('in note_command using args: %s' % args)
		self.sd.put(name=file_name, fobj=StringIO(args), access_token=user.auth_token)
		return "Wrote note %s to skydrive." % file_name.split('/')[-1]

	def generate_menu(self, file_names):
		menu = 'Enter # of selection: \n'
		for i in range(0, len(file_names)):
			option = '#%d. %s\n' % (i + 1, file_names[i])
			menu += option
		return menu

	def help_command(self, user, args):
		help_msg = "find <files> - get link\nnote <some text> - write note\ndl <remote file link> - downld file\nspace - get remaining space"
		return help_msg

	@refresh
	def traverse(self, user, path, searchTerm):
		file_names = []
		file_ids = []
		self.log.info(path)
		files = self.sd.list_dir(path, access_token=user.auth_token)
		for f in files:
			if f['type'] == 'folder':
				results_dict = self.traverse(user, f['id'], searchTerm)
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

