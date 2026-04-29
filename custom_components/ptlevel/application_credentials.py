from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    return AuthorizationServer(
        authorize_url="https://ptdevices.com/api/authorize",
        token_url="https://ptdevices.com/api/token",
    )
