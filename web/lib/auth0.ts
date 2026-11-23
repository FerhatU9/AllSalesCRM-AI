import "server-only";
import { Auth0Client } from "@auth0/nextjs-auth0/server";

// The SDK manages authorization-code login and encrypted server-side sessions.
// Access tokens are not exposed through the SDK's browser token endpoint.
export const auth0 = new Auth0Client({
  authorizationParameters: {
    audience: process.env.AUTH0_AUDIENCE,
    scope: "openid profile email offline_access",
  },
  enableAccessTokenEndpoint: false,
});
