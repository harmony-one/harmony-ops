package common

type Ec2Dto struct {
	TagName    string `json:"tag_name"`
	InstanceId string `json:"instance_id"`
	PublicIP   string `json:"public_ip"`
	PrivateIP  string `json:"private_ip"`
	Region     string `json:"region"`
}
