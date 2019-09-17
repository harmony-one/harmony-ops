# variables for ec2 instances

variable "private_key_path" {
  description = "The path to the SSH Private Key to access ec2 instance."
  default     = "/Users/bwu2/Harmony/keys/california-key-benchmark.pem"
}

variable "node_volume_size" {
  description = "Root Volume size of the ec2 node instance"
  default     = 250
}

variable "node_instance_type" {
  description = "Instance type of the ec2 node instance"
  default     = "m5d.large"
}

variable "aws_region" {
  description = "Region user wants to run node instance in"
  default     = "us-west-1"
}

variable "node_owner" {
  description = "The user starts the node instance"
  default     = "harmony-monitoring"
}

variable "security_groups" {
  type        = map
  description = "Security Group Map"
  default = {
    "us-west-1"      = "sg-04bd70e941e53e557"
  }
}

variable "user_data" {
  description = "User Data for EC2 Instance"
  default     = "files/userdata.sh"
}

variable "default_key" {
  default = ""
}


