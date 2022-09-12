package common

type ConfigurationDto struct {
	RedirectUri  string            `json:"redirectUri"`
	HomeUri      string            `json:"homeUri"`
	DigitalOcean DigitalOceanOAuth `json:"digitalOcean"`
}
