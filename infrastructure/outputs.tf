output "service_url" {
  description = "The public URL of the backend service"
  value       = "https://${koyeb_app.portfolio.name}.koyeb.app"
}
