"""ExpiresIn helper methods."""

from pydynox.attributes import ExpiresIn

# All methods return a datetime in UTC

# Short-lived items
token_expires = ExpiresIn.minutes(15)  # 15 minutes
session_expires = ExpiresIn.hours(1)  # 1 hour

# Medium-lived items
cache_expires = ExpiresIn.hours(24)  # 24 hours
temp_file_expires = ExpiresIn.days(7)  # 7 days

# Long-lived items
trial_expires = ExpiresIn.weeks(2)  # 2 weeks
