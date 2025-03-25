package nodedb

type ConfigurationDto struct {
	RedirectUri  string            `json:"redirectUri"`
	HomeUri      string            `json:"homeUri"`
	DigitalOcean DigitalOceanOAuth `json:"digitalOcean"`
}

type DigitalOceanDto struct {
	Id          int      `json:"id"`
	Region      string   `json:"region"`
	Name        string   `json:"name"`
	PublicIPv4  string   `json:"public_ip_v4"`
	PublicIPv6  string   `json:"public_ip_v6"`
	PrivateIPv4 string   `json:"private_ip_v4"`
	Tags        []string `json:"tags"`
}

type DigitalOceanOAuth struct {
	OAuthUrl     string `json:"oauthUrl"`
	ClientId     string `json:"clientId"`
	ClientSecret string `json:"clientSecret"`
}

type DigitalOceanOAuthToken struct {
	AccessToken  string `json:"access_token"`
	Bearer       string `json:"bearer"`
	ExpiresIn    int    `json:"expires_in"`
	RefreshToken string `json:"refresh_token"`
	Scope        string `json:"scope"`
}

type Ec2Dto struct {
	TagName    string `json:"tag_name"`
	InstanceId string `json:"instance_id"`
	PublicIP   string `json:"public_ip"`
	PrivateIP  string `json:"private_ip"`
	Region     string `json:"region"`
}

type HetznerDto struct {
	Id         int      `json:"id"`
	Region     string   `json:"region"`
	Name       string   `json:"name"`
	PublicIPv4 string   `json:"public_ip_v4"`
	PublicIPv6 string   `json:"public_ip_v6"`
	PrivateIP  []string `json:"private_ip"`
}
