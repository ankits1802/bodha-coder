variable "probe_host" {
  type = string
}

resource "aws_route53_health_check" "ready" {
  fqdn              = var.probe_host
  type              = "HTTPS"
  port              = 443
  resource_path     = "/api/health/ready"
  request_interval  = 30
  failure_threshold = 3
  enable_sni        = true
  regions           = ["us-east-1", "us-west-2", "eu-west-1"]

  tags = {
    Name = "${var.name}-ready"
  }
}

resource "aws_cloudwatch_metric_alarm" "down" {
  alarm_name          = "${var.name}-down"
  namespace           = "AWS/Route53"
  metric_name         = "HealthCheckStatus"
  dimensions          = { HealthCheckId = aws_route53_health_check.ready.id }
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}
