import asyncio

INPUT_KEYS = ['source', 'destination']

class ValidationError(Exception):
    pass

async def validate_input(data):
   if not all(key in data for key in INPUT_KEYS):
       missing_keys = list(filter(lambda key: key not in data, INPUT_KEYS))
       raise ValidationError(
           "Can't process input (data = {}) due to missing keys {}".format(
               data,
               missing_keys,
           )
       )

