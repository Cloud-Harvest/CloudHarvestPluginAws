module "aurora_mysql" {
  source = "./rds-aurora"
  engine = "aurora-mysql"
  engine_mode = "provisioned"
  identifier = "mysql-test"
}