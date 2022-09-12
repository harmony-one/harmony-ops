package common

type DigitalOceanDto struct {
	Id          int      `json:"id"`
	Region      string   `json:"region"`
	Name        string   `json:"name"`
	PublicIPv4  string   `json:"public_ip_v4"`
	PublicIPv6  string   `json:"public_ip_v6"`
	PrivateIPv4 string   `json:"private_ip_v4"`
	Tags        []string `json:"tags"`
}
