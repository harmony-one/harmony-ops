package common

type HetznerDto struct {
	Id         int      `json:"id"`
	Region     string   `json:"region"`
	Name       string   `json:"name"`
	PublicIPv4 string   `json:"public_ip_v4"`
	PublicIPv6 string   `json:"public_ip_v6"`
	PrivateIP  []string `json:"private_ip"`
}
