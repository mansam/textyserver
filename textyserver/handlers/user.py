from botoweb.appserver.handlers import RequestHandler
from botoweb.exceptions import BadRequest, NotFound
from textyserver.resources.user import TextyUser
import logging
import json
import boto
import urllib
import requests
import textyserver

log = logging.getLogger('texty.userHandler')

class UserHandler(RequestHandler):

	def _get(self, request, response, id=None):
		if id:
			params = id.split('/')
			if params:
				if params[0] == "code":
					log.info(request)
					auth_code = request.params["code"]
					email = request.params["email"]
					getLiveConnectTokens(auth_code)
		return response

	def _post(self, request, response, id=None):
		response.content_type = "application/json"
		if id:
			params = id.split('/')
			if params:
				if params[0] == "token":
					user = TextyUser.find(email=email).next()
					user.auth_token = response["access_token"]
					user.refresh_token = response["refresh_token"]
					user.put()
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
		else:
			user = createUser(request.params)
			requestLiveConnectCode(user.email)
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

def getLiveConnectTokens(auth_code, email):
	base_url = "https://login.live.com/oauth20_token.srf?"
	params = {
		"grant_type" : "authorization_code",
		"redirect_url" : "https://api.buildanavy.com/user/token",
		"client_id": textyserver.CLIENT_ID,
		"client_secret": textyserver.CLIENT_SECRET,
		"email": email
	}
	live_connect_url = base_url + urllib.urlencode(params)
	return json.loads(requests.post(live_connect_url).json())

def requestLiveConnectCode(email):
	base_url = "https://login.live.com/oauth20_authorize.srf?"
	params = {
		"response_type" : "code",
		"redirect_url" : "https://api.buildanavy.com/user/code",
		"scopes" : " ".join([
			"wl.basic",
			"wl.signin",
			"wl.offline_access",
			"wl.skydrive",
			"wl.skydrive_update"
		]),
		"client_id": textyserver.CLIENT_ID,
		"email": email
	}
	live_connect_url = base_url + urllib.urlencode(params)
	return requests.get(live_connect_url)

def createUser(params):
	required_params = ["email", "number"]
	log.info(params)
	missing_fields = []
	for param in required_params:
		if param not in params:
			missing_fields.append(param)
	if missing_fields:
		raise BadRequest("Missing required field(s): %s" % " ".join(missing_fields))

	user = TextyUser()
	user.email = params["email"]
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
