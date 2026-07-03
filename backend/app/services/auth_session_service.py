from app.core.logging import get_logger
from app.models import Project, ProjectCredential
from app.core.encryption import credential_encryption

logger = get_logger("AuthSessionService")


class AuthSessionService:
    """Handle credential decryption and login orchestration."""

    def get_credentials(self, project: Project) -> tuple[str, str] | None:
        if not project.credentials:
            return None
        cred: ProjectCredential = project.credentials
        password = credential_encryption.decrypt(cred.encrypted_password)
        logger.log("credentials_loaded", "Credentials decrypted for session", project_id=project.id)
        return cred.username, password

    async def create_login_fn(self, project: Project):
        from playwright_utils.crawler import perform_form_login

        creds = self.get_credentials(project)
        if not creds or not project.login_url:
            return None
        username, password = creds
        login_url = project.login_url

        async def login(page):
            await perform_form_login(page, login_url, username, password)

        return login


auth_session_service = AuthSessionService()
