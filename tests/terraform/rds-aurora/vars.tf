variable "engine" {
  description = "database engine"
  type = string
  validation {
    condition = startswith(var.engine, "aurora")
  }
}

variable "engine_mode" {
  description = "indicates if this is a provisioned or serverless cluster"
  type = string
  validation {
    condition = contains(["provisioned", "serverless"], var.engine_mode)
  }
}

variable "engine_version" {
  description = "database engine version; by default creates the latest version"
  default = ""
}

variable "identifier" {
  description = "the cluster identifier"
  type = string

}

variable "instance_class" {
  description = "the t-shirt size of the database instances"
  type = string
  default = "db.t4g.micro"

}

variable "instance_count" {
  description = "the number of database instances to create"
  type = number
  default = 0
}
