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
  description = "Cloudflare Worker name."
}

resource "cloudflare_worker" "this" {
  account_id = var.account_id
  name       = var.name

  subdomain = {
    enabled          = true
    previews_enabled = false
  }
}

output "name" {
  value       = cloudflare_worker.this.name
  description = "Cloudflare Worker name used by Wrangler."
}
