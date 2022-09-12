package common

type DigitalOceanOAuth struct {
	OAuthUrl     string `json:"oauthUrl"`
	ClientId     string `json:"clientId"`
	ClientSecret string `json:"clientSecret"`
}
