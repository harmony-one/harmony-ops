provider "aws" {
  region                  = "${var.aws_region}"
  shared_credentials_file = "~/.aws/credentials"
  profile                 = "harmony-ec2"
}

resource "aws_instance" "grafana-server" {
  ami                    = "${data.aws_ami.harmony-node-ami.id}"
  instance_type          = "${var.node_instance_type}"
  vpc_security_group_ids = ["${lookup(var.security_groups, var.aws_region, var.default_key)}"]
  key_name               = "california-key-benchmark"
  user_data              = "${file(var.user_data)}"

  root_block_device {
    volume_type = "gp2"
    volume_size = "${var.node_volume_size}"
  }

  tags = {
    Name    = "Grafana-tf"
    Project = "Harmony"
  }

  volume_tags = {
    Name    = "HarmonyNode-monitoring-Volume"
    Project = "Harmony"
  }

  # provisioner "file" {
  #   source      = "files/userdata.sh"
  #   destination = "/home/ec2-user/userdata.sh"
  #   connection {
  #     host        = "${aws_instance.grafana-server.public_ip}"
  #     type        = "ssh"
  #     user        = "ec2-user"
  #     private_key = "${file(var.private_key_path)}"
  #     agent       = true
  #   }
  # }

  # provisioner "remote-exec" {
  #   inline = [
  #     "curl -LO https://harmony.one/node.sh",
  #     "chmod +x node.sh",
  #     "sudo mv -f harmony.service /etc/systemd/system/harmony.service",
  #     "sudo systemctl enable harmony.service",
  #     "sudo systemctl start harmony.service",
  #   ]
  #   connection {
  #     host        = "${aws_instance.grafana-server.public_ip}"
  #     type        = "ssh"
  #     user        = "ec2-user"
  #     private_key = "${file(var.private_key_path)}"
  #     agent       = true
  #   }
  # }

}
