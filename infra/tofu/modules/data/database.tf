ephemeral "random_password" "database" {
  length  = 40
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_parameter_group" "this" {
  name   = "${var.name}-postgres17"
  family = "postgres17"

  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "log_parameter_max_length"
    value = "0"
  }

  parameter {
    name  = "log_parameter_max_length_on_error"
    value = "0"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
}

resource "aws_db_instance" "this" {
  identifier                 = var.name
  engine                     = "postgres"
  engine_version             = "17"
  instance_class             = var.database_class
  allocated_storage          = 20
  max_allocated_storage      = 200
  storage_type               = "gp3"
  storage_encrypted          = true
  kms_key_id                 = aws_kms_key.this.arn
  db_name                    = "bodha"
  username                   = "bodha_app"
  password_wo                = ephemeral.random_password.database.result
  password_wo_version        = var.database_password_version
  db_subnet_group_name       = aws_db_subnet_group.this.name
  parameter_group_name       = aws_db_parameter_group.this.name
  vpc_security_group_ids     = [var.database_security_group_id]
  publicly_accessible        = false
  multi_az                   = false
  backup_retention_period    = var.database_backup_days
  backup_window              = "07:00-07:30"
  maintenance_window         = "sun:08:00-sun:08:30"
  auto_minor_version_upgrade = true
  copy_tags_to_snapshot      = true
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${var.name}-final"
  apply_immediately          = true
}
