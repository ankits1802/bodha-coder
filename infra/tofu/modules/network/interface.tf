variable "name" {
  type = string
}

variable "cidr" {
  type = string
}

variable "region" {
  type = string
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "cidr" {
  value = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "security_groups" {
  value = {
    alb      = aws_security_group.alb.id
    api      = aws_security_group.api.id
    web      = aws_security_group.web.id
    worker   = aws_security_group.worker.id
    database = aws_security_group.database.id
  }
}
