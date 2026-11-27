variable "region" {
  type = string
}

variable "cluster" {
  type = string
}

locals {
  services = ["api", "worker", "web"]
  alb      = var.load_balancer.arn_suffix
  widgets = [
    {
      title   = "Requests and server errors"
      metrics = [["AWS/ApplicationELB", "RequestCount", "LoadBalancer", local.alb, { stat = "Sum" }], [".", "HTTPCode_Target_5XX_Count", ".", ".", { stat = "Sum" }]]
    },
    {
      title   = "Response time (p95, seconds)"
      metrics = [["AWS/ApplicationELB", "TargetResponseTime", "TargetGroup", var.load_balancer.api, "LoadBalancer", local.alb, { stat = "p95", label = "api" }], ["...", var.load_balancer.web, ".", ".", { stat = "p95", label = "web" }]]
    },
    {
      title   = "Container CPU (%)"
      metrics = [for service in local.services : ["AWS/ECS", "CPUUtilization", "ClusterName", var.cluster, "ServiceName", service, { stat = "Average", label = service }]]
    },
    {
      title   = "Container memory (%)"
      metrics = [for service in local.services : ["AWS/ECS", "MemoryUtilization", "ClusterName", var.cluster, "ServiceName", service, { stat = "Average", label = service }]]
    },
    {
      title   = "Analysis queue"
      metrics = [["BodhaCoder", "QueuedAnalyses", { stat = "Maximum", label = "queued" }], [".", "RunningAnalyses", { stat = "Maximum", label = "running" }]]
    },
    {
      title   = "Database"
      metrics = [["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", var.database_identifier, { stat = "Average", label = "CPU %" }], [".", "DatabaseConnections", ".", ".", { stat = "Maximum", label = "connections" }]]
    },
  ]
}

resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = var.name
  dashboard_body = jsonencode({
    widgets = [for index, widget in local.widgets : {
      type   = "metric"
      x      = (index % 2) * 12
      y      = floor(index / 2) * 6
      width  = 12
      height = 6
      properties = {
        title   = widget.title
        region  = var.region
        view    = "timeSeries"
        stacked = false
        period  = 300
        metrics = widget.metrics
      }
    }]
  })
}
