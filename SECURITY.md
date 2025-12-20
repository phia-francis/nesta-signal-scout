# Security Policy

Thank you for helping to keep **Nesta Signal Scout** secure. We take the security of our data, our partners' data, and our infrastructure seriously.

## 📦 Supported Versions

Only the latest version of the `main` branch is currently supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| Other   | :x:                |

## 🐞 Reporting a Vulnerability

If you discover a security vulnerability within this project, please **do not create a public GitHub issue**. Instead, please report it via email to the project maintainers or the Nesta security team.

* **Email:** [sophia.francis@nesta.org.uk]
* **Response Time:** We aim to acknowledge receipt of vulnerability reports within 48 hours.

Please include as much information as possible to help us reproduce the issue.

## 🔐 Secrets & Credentials Management

This project relies on sensitive credentials to function. **Improper handling of these secrets is the single largest security risk.**

### 1. OpenAI & Google Search Keys
* **Never commit API keys** (e.g., `OPENAI_API_KEY`, `Google Search_KEY`) to version control.
* **Local Development:** Use a `.env` file that is listed in `.gitignore`.
* **Production:** Use the Environment Variables settings in your hosting provider (e.g., Render Dashboard).

### 2. Google Service Account (`GOOGLE_CREDENTIALS`)
* The `GOOGLE_CREDENTIALS` environment variable contains a **private RSA key** that grants write access to the Nesta Signal Database (Google Sheet).
* **Critical:** If this key is leaked, an attacker could delete or corrupt the entire database.
* **Action:** If you suspect this key has been compromised, immediately revoke the key in the Google Cloud Console and generate a new one.

## 🛡️ Infrastructure & Access Control

### Frontend Authentication
* **Current State:** The frontend (`index.html`) currently performs **no user authentication**. It is designed for internal use within a trusted environment.
* **Risk:** If the frontend URL is exposed publicly, anyone can initiate searches (consuming OpenAI credits) and view the signal database.
* **Mitigation:**
    * Deploy the frontend behind a password-protected gateway (e.g., Cloudflare Access, Render Private Service, or basic HTTP Auth).
    * Do not share the deployment URL on public forums.

### CORS Configuration
* The backend (`main.py`) is currently configured with `allow_origins=["*"]` to facilitate easy deployment.
* **Recommendation:** For a hardened production environment, restrict `allow_origins` to the specific domain where your frontend is hosted.

## 📝 Third-Party Dependencies

This project uses Python dependencies listed in `requirements.txt`.
* We recommend regularly scanning dependencies for known vulnerabilities using tools like `pip-audit` or GitHub's Dependabot.
* To update dependencies locally:
    ```bash
    pip install -U -r requirements.txt
    ```
