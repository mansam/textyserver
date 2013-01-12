from botoweb.resources.user import User
from botoweb.db.property import StringProperty
from botoweb.db.property import BooleanProperty
from botoweb.db.property import DateTimeProperty
from botoweb.db.property import ReferenceProperty

class TextyUser(User):
	
	is_active = BooleanProperty(verbose_name="Is Active", default=False)