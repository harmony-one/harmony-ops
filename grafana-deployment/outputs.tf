output "public_ip" {
  description = "Public IP of instance (or EIP)"
  value       = aws_instance.grafana-server.*.public_ip
}