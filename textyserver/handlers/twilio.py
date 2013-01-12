from botoweb.appserver.handlers import RequestHandler
import logging
log = logging.getLogger('texty.twilioHandler')

class TwilioHandler(RequestHandler):

	def _post(self, request, response, id=None):
		response.content_type = "text/plain"
		log.info(request.body)
		response.body = "Message received."
		return response

