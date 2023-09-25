terraform {
  backend "local" {
    path = "./state.tfstate"
  }
  required_providers {
    aws = {
      version = ">= 5"
    }
  }

  required_version = ">= 1.5"
}
