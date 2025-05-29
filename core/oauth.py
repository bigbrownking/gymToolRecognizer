import logging
import httpx
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from fastapi import HTTPException

from core.config import settings
from crud.user import get_user_by_email, create_oauth_user
from schemas.user import UserCreateOAuth
from core.security import create_access_token

logger = logging.getLogger(__name__)


class OAuthStateManager:

    def __init__(self):
        self.states = {}
        self.cleanup_interval = 3600

    def generate_state(self, provider: str) -> str:
        state = secrets.token_urlsafe(32)
        self.states[state] = {
            "provider": provider,
            "timestamp": datetime.utcnow().timestamp()
        }
        return state

    def verify_state(self, state: str, provider: str) -> bool:
        if state not in self.states:
            return False

        state_data = self.states.pop(state)

        if datetime.utcnow().timestamp() - state_data["timestamp"] > self.cleanup_interval:
            return False

        return state_data["provider"] == provider

    def cleanup_expired_states(self):
        current_time = datetime.utcnow().timestamp()
        expired_states = [
            state for state, data in self.states.items()
            if current_time - data["timestamp"] > self.cleanup_interval
        ]
        for state in expired_states:
            del self.states[state]


class OAuthProvider:

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        raise NotImplementedError

    async def exchange_code_for_token(self, code: str) -> str:
        raise NotImplementedError

    async def get_user_info(self, access_token: str) -> Dict:
        raise NotImplementedError


class GoogleOAuthProvider(OAuthProvider):

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.auth_url = "https://accounts.google.com/o/oauth2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.scopes = ["openid", "email", "profile"]

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                }
            )

            if response.status_code != 200:
                logger.error(f"Google token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

            token_data = response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")

            return access_token

    async def get_user_info(self, access_token: str) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.user_info_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                logger.error(f"Failed to get Google user info: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to get user information")

            return response.json()


class MicrosoftOAuthProvider(OAuthProvider):

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, tenant_id: str = "common"):
        super().__init__(client_id, client_secret, redirect_uri)
        self.tenant_id = tenant_id
        self.auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.user_info_url = "https://graph.microsoft.com/v1.0/me"
        self.scopes = ["openid", "profile", "email", "User.Read"]

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "state": state,
            "response_mode": "query"
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                }
            )

            if response.status_code != 200:
                logger.error(f"Microsoft token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

            token_data = response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")

            return access_token

    async def get_user_info(self, access_token: str) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.user_info_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                logger.error(f"Failed to get Microsoft user info: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to get user information")

            user_data = response.json()

            # Normalize Microsoft user data to match expected format
            normalized_data = {
                "id": user_data.get("id"),
                "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                "name": user_data.get("displayName"),
                "given_name": user_data.get("givenName"),
                "family_name": user_data.get("surname"),
            }

            return normalized_data


class DiscordOAuthProvider(OAuthProvider):

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.auth_url = "https://discord.com/api/oauth2/authorize"
        self.token_url = "https://discord.com/api/oauth2/token"
        self.user_info_url = "https://discord.com/api/users/@me"
        self.scopes = ["identify", "email"]

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "state": state,
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                }
            )

            if response.status_code != 200:
                logger.error(f"Discord token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

            token_data = response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")

            return access_token

    async def get_user_info(self, access_token: str) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.user_info_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                logger.error(f"Failed to get Discord user info: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to get user information")

            user_data = response.json()

            normalized_data = {
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "name": user_data.get("username"),
                "avatar": user_data.get("avatar"),
                "discriminator": user_data.get("discriminator"),
                "global_name": user_data.get("global_name"),
            }

            return normalized_data


class OAuthService:
    def __init__(self):
        self.state_manager = OAuthStateManager()
        self.providers = {}
        self._setup_providers()

    def _setup_providers(self):
        # Google
        google_client_id = settings.GOOGLE_CLIENT_ID
        google_client_secret = settings.GOOGLE_CLIENT_SECRET
        google_redirect_uri = settings.GOOGLE_REDIRECT_URI

        if google_client_id and google_client_secret:
            self.providers["google"] = GoogleOAuthProvider(
                google_client_id, google_client_secret, google_redirect_uri
            )

        # Microsoft
        microsoft_client_id = getattr(settings, 'MICROSOFT_CLIENT_ID', None)
        microsoft_client_secret = getattr(settings, 'MICROSOFT_CLIENT_SECRET', None)
        microsoft_redirect_uri = getattr(settings, 'MICROSOFT_REDIRECT_URI', None)
        microsoft_tenant_id = getattr(settings, 'MICROSOFT_TENANT_ID', 'common')

        if microsoft_client_id and microsoft_client_secret:
            self.providers["microsoft"] = MicrosoftOAuthProvider(
                microsoft_client_id, microsoft_client_secret, microsoft_redirect_uri, microsoft_tenant_id
            )

        # Discord
        discord_client_id = getattr(settings, 'DISCORD_CLIENT_ID', None)
        discord_client_secret = getattr(settings, 'DISCORD_CLIENT_SECRET', None)
        discord_redirect_uri = getattr(settings, 'DISCORD_REDIRECT_URI', None)

        if discord_client_id and discord_client_secret:
            self.providers["discord"] = DiscordOAuthProvider(
                discord_client_id, discord_client_secret, discord_redirect_uri
            )

    def get_available_providers(self) -> list:
        provider_info = []

        for provider_name, provider in self.providers.items():
            display_names = {
                "google": "Google",
                "microsoft": "Microsoft",
                "discord": "Discord"
            }

            provider_info.append({
                "name": provider_name,
                "display_name": display_names.get(provider_name, provider_name.capitalize()),
                "login_url": f"/auth/{provider_name}/login"
            })

        return provider_info

    def initiate_oauth_flow(self, provider_name: str) -> str:
        if provider_name not in self.providers:
            raise HTTPException(status_code=404, detail=f"OAuth provider '{provider_name}' not found")

        provider = self.providers[provider_name]
        state = self.state_manager.generate_state(provider_name)
        authorization_url = provider.get_authorization_url(state)

        logger.info(f"Initiating OAuth flow for {provider_name}")
        return authorization_url

    def _generate_username_from_email(self, email: str) -> str:
        username_base = email.split('@')[0]
        random_suffix = secrets.token_hex(3)
        return f"{username_base}_{random_suffix}"

    def _extract_user_data(self, user_info: Dict, provider_name: str) -> Tuple[str, str, str]:
        email = user_info.get("email")
        provider_id = str(user_info.get("id"))

        if provider_name == "google":
            name = user_info.get("name")
        elif provider_name == "microsoft":
            name = user_info.get("name") or user_info.get("displayName")
        elif provider_name == "discord":
            name = (user_info.get("global_name") or
                    user_info.get("name") or
                    f"{user_info.get('username', '')}#{user_info.get('discriminator', '')}")
        else:
            name = user_info.get("name") or user_info.get("login")

        return email, name, provider_id

    async def handle_oauth_callback(
            self,
            provider_name: str,
            code: str,
            state: str,
            db: Session
    ) -> Tuple[str, Dict]:

        if provider_name not in self.providers:
            raise HTTPException(status_code=404, detail=f"OAuth provider '{provider_name}' not found")

        if not self.state_manager.verify_state(state, provider_name):
            logger.warning(f"Invalid OAuth state for {provider_name}: {state}")
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        provider = self.providers[provider_name]

        try:
            access_token = await provider.exchange_code_for_token(code)

            user_info = await provider.get_user_info(access_token)

            email, name, provider_id = self._extract_user_data(user_info, provider_name)

            if not email:
                raise HTTPException(status_code=400, detail="No email provided by OAuth provider")

            logger.info(f"OAuth login attempt for {provider_name}: {email}")

            existing_user = get_user_by_email(db, email)

            if existing_user:
                logger.info(f"Existing user {email} logged in via {provider_name}")
                user_obj = existing_user
            else:
                username = name or self._generate_username_from_email(email)

                user_create_data = UserCreateOAuth(
                    email=email,
                    password=secrets.token_urlsafe(32),
                    username=username
                )

                user_obj = create_oauth_user(
                         db,
                         email=email,
                         username=username,
                         oauth_provider=provider_name,
                         oauth_id=provider_id
                     )
                logger.info(f"New {provider_name} OAuth user {email} created with ID {user_obj.id}")

            jwt_token = create_access_token(
                data={"sub": user_obj.email},
                expires_delta=timedelta(minutes=60)
            )

            user_data = {
                "id": user_obj.id,
                "email": user_obj.email,
                "username": getattr(user_obj, 'username', None),
                "gender": getattr(user_obj, 'gender', None),
                "dateOfBirth": getattr(user_obj, 'dateOfBirth', None),
                "profile_image_url": getattr(user_obj, 'profile_image_url', None),
                "is_oauth_user": getattr(user_obj, 'is_oauth_user', True),
                "oauth_provider": provider_name
            }

            logger.info(f"OAuth user {email} logged in successfully via {provider_name}")
            return jwt_token, user_data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during {provider_name} OAuth: {str(e)}")
            raise HTTPException(status_code=500, detail=f"{provider_name} OAuth authentication failed")
        except Exception as e:
            logger.error(f"Unexpected error during {provider_name} OAuth: {str(e)}")
            raise HTTPException(status_code=500, detail=f"{provider_name} OAuth authentication failed")

    def cleanup_expired_states(self):
        self.state_manager.cleanup_expired_states()


oauth_service = OAuthService()
