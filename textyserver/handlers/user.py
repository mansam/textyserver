from botoweb.appserver.handlers import RequestHandler
from botoweb.exceptions import BadRequest, NotFound
from textyserver.resources.user import TextyUser
import logging
import json
import boto

log = logging.getLogger('texty.userHandler')

class UserHandler(RequestHandler):

	def _get(self, request, response, id=None):
		param = id.split('/')[0]
		# if param == "code":
		# 	code = request.params["code"]

	def _post(self, request, response, id=None):
		response.content_type = "application/json"

		user = createUser(request.params)
		try:
			challenge = getChallengeCode()
		except Exception:
			# retry 
			raise

		try:
			user.sms(challenge)
		except Exception:
			# deal with twilio errors
			raise

		response.body = json.dumps(user.to_dict()) 
		return response

	def _put(self, request, response, id=None):
		required_params = ["email", "refresh"]
		missing_fields = []
		for param in required_params:
			if param not in request.params:
				missing_fields.append(param)
		if missing_fields:
			raise BadRequest("Missing required field(s): %s" % " ".join(missing_fields))

		try:
			user = TextyUser.find(email=request.params.email).next()
		except StopIteration:
			raise NotFound("No such user.")

		user.refresh_token = request.params["refresh"]
		user.put()

		return response

def createUser(params):
	required_params = ["email", "token", "number"]
	log.info(params)
	missing_fields = []
	for param in required_params:
		if param not in params:
			missing_fields.append(param)
	if missing_fields:
		raise BadRequest("Missing required field(s): %s" % " ".join(missing_fields))

	user = TextyUser()
	user.email = params["email"]
	user.auth_token = params["token"] 
	user.phone = params["number"]

	return user.put()

def getChallengeCode():
	import urllib2
	length = "6"
	digits = "on"
	loweralpha = "on"
	upperalpha = "off"
	url = "https://www.random.org/cgi-bin/randstring?num=1&len=%s&digits=%s&upperalpha=%s&loweralpha=%s&unique=on&format=text&rnd=new" % (length, digits, upperalpha, loweralpha)
	headers = {"User-Agent": "%s %s (%s)" % (boto.config.get("app", "name", "skydrive_texty"), boto.config.get("app", "version", "0.1"), boto.config.get("app", "admin_email", ""))}
	req = urllib2.Request(url, None, headers)
	challenge = urllib2.urlopen(req).read().strip()
	return challenge
