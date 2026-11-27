locals {
  services = {
    api    = { group = var.security_groups.api, target = aws_lb_target_group.api.arn, port = 8000 }
    worker = { group = var.security_groups.worker, target = null, port = null }
    web    = { group = var.security_groups.web, target = aws_lb_target_group.web.arn, port = 3000 }
  }
}

resource "aws_ecs_cluster" "this" {
  name = var.name

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}

resource "aws_ecs_service" "this" {
  for_each                          = local.services
  name                              = each.key
  cluster                           = aws_ecs_cluster.this.id
  task_definition                   = aws_ecs_task_definition.this[each.key].arn
  desired_count                     = var.desired_count
  health_check_grace_period_seconds = each.value.target == null ? null : 60
  enable_execute_command            = false
  propagate_tags                    = "SERVICE"
  force_new_deployment              = true

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [each.value.group]
    assign_public_ip = true
  }

  dynamic "load_balancer" {
    for_each = each.value.target == null ? [] : [1]

    content {
      target_group_arn = each.value.target
      container_name   = each.key
      container_port   = each.value.port
    }
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_ecs_cluster_capacity_providers.this, aws_lb_listener_rule.api]
}
