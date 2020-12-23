import re
import urllib
import urllib.request

from urllib.parse import urlencode
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER


class SteamSignIn():

	_provider = 'https://steamcommunity.com/openid/login'

	def redirect_user(self, str_post_data):
		return RedirectResponse(
            url="{0}?{1}".format(self._provider, str_post_data),
		    status_code=HTTP_303_SEE_OTHER,
		    headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

	def construct_url(self, response_url):
		refinedScripts = re.search('(?:http)', response_url)

		if refinedScripts == None or refinedScripts.group(0) == None:
			response_url = "http://{0}".format(response_url)

		authParameters = {
			"openid.ns":"http://specs.openid.net/auth/2.0",
			"openid.mode": "checkid_setup",
			"openid.return_to": response_url,
			"openid.realm": response_url,
			"openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
			"openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select"
		}

		return urlencode(authParameters)

	def validate_results(self, results):
		validationArgs ={
			'openid.assoc_handle': results['openid.assoc_handle'],
			'openid.signed': results['openid.signed'],
			'openid.sig' : results['openid.sig'],
			'openid.ns': results ['openid.ns']
		}

		signedArgs = results['openid.signed'].split(',')

		for item in signedArgs:
			itemArg = 'openid.{0}'.format(item)
			if results[itemArg] not in validationArgs:
				validationArgs[itemArg] = results[itemArg]

		validationArgs['openid.mode'] = 'check_authentication'
		parsedArgs = urlencode(validationArgs).encode("utf-8")

		with urllib.request.urlopen(self._provider, parsedArgs) as requestData:
			responseData = requestData.read().decode('utf-8')

		if re.search('is_valid:true', responseData):
			matched64ID = re.search('https://steamcommunity.com/openid/id/(\d+)', results['openid.claimed_id'])
			if matched64ID != None or matched64ID.group(1) != None:
				return matched64ID.group(1)
			else:
				return False
		else:
			return False
