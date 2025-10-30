from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class CashfreePaymentsProvider(ToolProvider):
    
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        Validate credentials for Cashfree Payments
        Supports two authentication methods:
        1. Client Credentials (client_id + client_secret)
        2. Authorization Bearer Token
        """
        # Environment validation (required for both auth methods)
        if not credentials.get("cashfree_environment"):
            raise ToolProviderCredentialValidationError("Missing required field: cashfree_environment")
        
        if credentials.get("cashfree_environment") not in ["sandbox", "production"]:
            raise ToolProviderCredentialValidationError("Environment must be 'sandbox' or 'production'")
        
        # Get the authentication method
        auth_method = credentials.get("auth_method", "client_credentials")
        
        if auth_method == "client_credentials":
            # Validate client credentials
            required_fields = ["cashfree_client_id", "cashfree_client_secret"]
            
            for field in required_fields:
                if not credentials.get(field):
                    raise ToolProviderCredentialValidationError(f"Missing required field for client credentials: {field}")
                    
        elif auth_method == "bearer_token":
            # Validate bearer token
            if not credentials.get("bearer_token"):
                raise ToolProviderCredentialValidationError("Missing required field for bearer token authentication: bearer_token")
                
        else:
            raise ToolProviderCredentialValidationError("Invalid authentication method. Must be 'client_credentials' or 'bearer_token'")
        
        # All validations passed


    #########################################################################################
    # If OAuth is supported, uncomment the following functions.
    # Warning: please make sure that the sdk version is 0.4.2 or higher.
    #########################################################################################
    # def _oauth_get_authorization_url(self, redirect_uri: str, system_credentials: Mapping[str, Any]) -> str:
    #     """
    #     Generate the authorization URL for cashfree_pg OAuth.
    #     """
    #     try:
    #         """
    #         IMPLEMENT YOUR AUTHORIZATION URL GENERATION HERE
    #         """
    #     except Exception as e:
    #         raise ToolProviderOAuthError(str(e))
    #     return ""
        
    # def _oauth_get_credentials(
    #     self, redirect_uri: str, system_credentials: Mapping[str, Any], request: Request
    # ) -> Mapping[str, Any]:
    #     """
    #     Exchange code for access_token.
    #     """
    #     try:
    #         """
    #         IMPLEMENT YOUR CREDENTIALS EXCHANGE HERE
    #         """
    #     except Exception as e:
    #         raise ToolProviderOAuthError(str(e))
    #     return dict()

    # def _oauth_refresh_credentials(
    #     self, redirect_uri: str, system_credentials: Mapping[str, Any], credentials: Mapping[str, Any]
    # ) -> OAuthCredentials:
    #     """
    #     Refresh the credentials
    #     """
    #     return OAuthCredentials(credentials=credentials, expires_at=-1)
