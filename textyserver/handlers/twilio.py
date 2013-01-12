from botoweb.appserver.handlers import RequestHandler

class TwilioHandler(RequestHandler):
	
	def __init__(self, env, config):
		pass

	def _post(self, request, response, id=None):
		response.content_type = "application/json"

		return response

