resource "aws_security_group" "alb" {
  name        = "${var.name}-alb"
  description = "Internal load balancer, reached by CloudFront through its VPC origin"
  vpc_id      = aws_vpc.this.id
}

resource "aws_security_group" "api" {
  name        = "${var.name}-api"
  description = "API tasks"
  vpc_id      = aws_vpc.this.id
}

resource "aws_security_group" "web" {
  name        = "${var.name}-web"
  description = "Web tasks"
  vpc_id      = aws_vpc.this.id
}

resource "aws_security_group" "worker" {
  name        = "${var.name}-worker"
  description = "Worker, migration and one-off tasks"
  vpc_id      = aws_vpc.this.id
}

resource "aws_security_group" "database" {
  name        = "${var.name}-database"
  description = "Postgres"
  vpc_id      = aws_vpc.this.id
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "CloudFront VPC origin and web tasks inside the VPC"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = var.cidr
}

resource "aws_vpc_security_group_ingress_rule" "api_from_alb" {
  security_group_id            = aws_security_group.api.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_ingress_rule" "web_from_alb" {
  security_group_id            = aws_security_group.web.id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_ingress_rule" "database" {
  for_each                     = { api = aws_security_group.api.id, worker = aws_security_group.worker.id }
  security_group_id            = aws_security_group.database.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = each.value
}

resource "aws_vpc_security_group_egress_rule" "out" {
  for_each = {
    alb    = aws_security_group.alb.id
    api    = aws_security_group.api.id
    web    = aws_security_group.web.id
    worker = aws_security_group.worker.id
  }
  security_group_id = each.value
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
