terraform {
  required_version = "= 1.12.5"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "= 5.22.0"
    }
  }
}

variable "account_id" {
  type        = string
  description = "Cloudflare account identifier."
}

variable "name" {
  type        = string
  description = "Cloudflare Pages project name."
}

resource "cloudflare_pages_project" "this" {
  account_id        = var.account_id
  name              = var.name
  production_branch = "main"
}

output "name" {
  value       = cloudflare_pages_project.this.name
  description = "Cloudflare Pages project name used by Wrangler."
}
