# Developer Runtime Configuration

Read by the launch script to determine which model Aider uses.
Change this file to switch models — do NOT edit the launch script directly.

---

provider: nara
executor: kilo-code
model: mistral-large
fallback_enabled: true
api_base: https://router.bynara.id/v1
api_base_env_var: OPENAI_API_BASE
api_key_env_var: OPENAI_API_KEY
env_file: DeveloperTools\.env