from botoweb.resources.user import User
from botoweb.db.coremodel import Model
from botoweb.db.property import StringProperty
from botoweb.db.property import BooleanProperty
from botoweb.db.property import DateTimeProperty
from botoweb.db.property import ReferenceProperty

class TextyUser(User):

	is_active = BooleanProperty(verbose_name="Is Active", default=False)
	refresh_token = StringProperty(verbose_name="Skydrive Refresh Token")
	phone = property.StringProperty(verbose_name="Phone Number", unique=True) # Used for SMS notify

	def put(self):
		self.username = self.email
		return User.put(self)

	def to_dict(self, *args, **kwargs):
		"""
		Convert obj to dictionary for JSON serialization.
		Override Botoweb User's default to_dict()
		because we don't give a damn about the Authorization
		groups.

		"""
		
		ret = {}
		ret["email"] = self.email
		ret["phone"] = self.phone
		ret["__id__"] = self.id
		return ret