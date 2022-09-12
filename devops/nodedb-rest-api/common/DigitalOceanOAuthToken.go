package common

type DigitalOceanOAuthToken struct {
	AccessToken  string `json:"access_token"`
	Bearer       string `json:"bearer"`
	ExpiresIn    int    `json:"expires_in"`
	RefreshToken string `json:"refresh_token"`
	Scope        string `json:"scope"`
}
