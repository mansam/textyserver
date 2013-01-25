from botoweb.appserver.handlers import RequestHandler
from botoweb.exceptions import BadRequest, NotFound, TemporaryRedirect, Conflict
from textyserver.resources.user import TextyUser
import logging
import json
import boto
import urllib
import textyserver
import liveconnect.skydrive 

log = logging.getLogger('texty.userHandler')
sd = liveconnect.skydrive.connect_skydrive()

class UserHandler(RequestHandler):

	def _get(self, request, response, id=None):
		if id:
			params = id.split('/')
			if params:
				if params[0] == "code":
					log.info(request)	
					user_params = {}

					auth_code = request.params["code"]
					log.info(auth_code)
					state = request.params["state"]
					phone, email = state.split(' ')
					user_params["phone"] = phone
					user_params["email"] = email

					resp = sd.authorize(auth_code=auth_code, redirect_uri=textyserver.REDIRECT_URI)
					log.info(resp)
	
					user_params["auth_token"] = resp["access_token"]
					user_params["refresh_token"] = resp["refresh_token"]
					user = createUser(user_params)
					try:
						challenge = getChallengeCode()
						user.challenge = challenge
						user.put()
					except Exception:
						# retry 
						raise
					try:
						user.sms("Texty Confirmation: %s" % challenge)
					except Exception:
						# deal with twilio errors
						raise
					raise TemporaryRedirect(textyserver.AUTHCODE_URI)
		return response

	def _post(self, request, response, id=None):
		response.content_type = "application/json"
		if id:
			params = id.split('/')
			if params and params[0] == "new":
				try:
					email = request.params["email"]
					phone = request.params["phone"]
					user = TextyUser.find(phone=phone).next()
				except StopIteration:
					scopes = ['wl.basic', 'wl.skydrive', 'wl.skydrive_update', 'wl.offline_access']
					auth_url = sd.generate_auth_url(scopes=scopes,
													redirect_uri=textyserver.REDIRECT_URI,
													state="%s %s" % (phone, email))
					raise TemporaryRedirect(auth_url)
				except:
					raise BadRequest("Missing required fields.")
				else:
					raise Conflict("Phone number already in use.")
		else:
			challenge = request.params["challenge"]
			try:
				user = TextyUser.find(challenge=challenge).next()
			except StopIteration:
				log.exception('Invalid challenge code: %s' % challenge)
				raise NotFound("Invalid challenge code.")
			user.is_active = True
			user.put()
			user.sms('Thanks for signing up with Texty! Text HLP for commands.')

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
	required_params = ["email", "phone", "auth_token", "refresh_token"]
	log.info(params)
	missing_fields = []
	for param in required_params:
		if param not in params:
			missing_fields.append(param)
	if missing_fields:
		raise BadRequest("Missing required field(s): %s" % " ".join(missing_fields))

	user = TextyUser()
	user.email = params["email"]
	user.phone = params["phone"]
	user.auth_token = params["auth_token"]
	user.refresh_token = params["refresh_token"]

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
