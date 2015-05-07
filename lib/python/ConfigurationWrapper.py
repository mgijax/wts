# Name: ConfigurationWrapper
# Purpose: serves as a wrapper over a Configuration object and the config
#	data stored in the database.  Pulls from the Configuration object
#	(the config file) where available, queries the database where it's
#	not available.

import Configuration
import wtslib

error = 'ConfigurationWrapper.error'

class ConfigurationWrapper:
	def __init__ (self):
		self.config = {}
		for key in Configuration.config.keys():
			self.config[key] = Configuration.config[key]
		return

	def __getitem__ (self, key):
		if self.config.has_key(key):
			return self.config[key]

		if not self.config.has_key('DB_SCHEMA'):
			raise error, 'Missing config parameter: DB_SCHEMA'

		cmd = '''select int_value, string_value, date_value
			from %s.wts_config
			where _Config_name = '%s' ''' % (
				self.config['DB_SCHEMA'], key)

		value = None
		results = wtslib.sql(cmd)

		if len(results) > 0:
			row = results[0]

			if row['int_value'] != None:
				value = row['int_value']
			elif row['string_value'] != None:
				value = row['string_value']
			elif row['date_value'] != None:
				value = row['date_value']

		self.config[key] = value
		return value

# create one instance when the module is imported
config = ConfigurationWrapper()
