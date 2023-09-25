resource "aws_rds_cluster" "cluster" {
    cluster_identifier_prefix = var.identifier
    engine_mode = var.engine_mode
    skip_final_snapshot  = true
    master_username = "test"
    master_password = "harvest-rds-test"
    backup_retention_period = 1
    kms_key_id = aws_kms_key.aurora_kms_key.id
}

resource "aws_rds_cluster_instance" "cluster_instance" {
  count = var.engine_mode == "provisioned" ? var.instance_count : 0
  cluster_identifier = aws_rds_cluster.cluster.id
  identifier = join("-", [var.identifier, count.index + 1])
  instance_class     = var.instance_class
}

resource "aws_kms_key" "aurora_kms_key" {
  description = format("kms key for %s", var.identifier)
  deletion_window_in_days = 0
}