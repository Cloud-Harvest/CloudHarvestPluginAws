resource "aws_rds_cluster" "cluster" {
  cluster_identifier_prefix = var.identifier
  engine                    = var.engine
  engine_mode               = var.engine_mode
  skip_final_snapshot       = true
  master_username           = "test"
  master_password           = "harvest-rds-test"
  backup_retention_period   = 1
}

resource "aws_rds_cluster_instance" "cluster_instance" {
  count              = var.engine_mode == "provisioned" ? var.instance_count : 0
  cluster_identifier = aws_rds_cluster.cluster.id
  engine             = var.engine
  identifier         = join("-", [var.identifier, count.index + 1])
  instance_class     = var.instance_class
}
