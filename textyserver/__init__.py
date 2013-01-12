import boto

__version__ = "0.1.0"

CLIENT_ID = boto.config.get("Skydrive", "client_id")
CLIENT_SECRET = boto.config.get("Skydrive", "client_secret")