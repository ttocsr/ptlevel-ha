import aiohttp
from homeassistant.helpers import config_entry_oauth2_flow

class PTLevelOAuth2API:
    def __init__(self, session: config_entry_oauth2_flow.OAuth2Session):
        self.session = session

    async def async_get_devices(self):
        """Fetch all devices linked to the OAuth2 account."""
        # This one line automatically handles token expiration & refreshing!
        await self.session.async_ensure_token_valid()
        
        access_token = self.session.token["access_token"]
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as client:
            async with client.get("https://ptdevices.com/api/v1/devices", headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()
