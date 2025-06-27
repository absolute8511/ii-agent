from typing import Any, Optional
from ii_agent.llm.message_history import MessageHistory
from ii_agent.sandbox.config import SandboxSettings
from ii_agent.tools.base import LLMTool, ToolImplOutput
from ii_agent.tools.clients.terminal_client import TerminalClient
from ii_agent.utils.workspace_manager import WorkspaceManager


class FullStackInitTool(LLMTool):
    name = "fullstack_project_init"
    description = """This tool initializes a fullstack web application environment by using the development template. It constructs a `frontend` and `backend` template directory inside the project path, and installs all necessary packages."""

    input_schema = {
        "type": "object",
        "properties": {
            "project_name": {
                "type": "string",
                "description": "A name for your project (lowercase, no spaces, use hyphens - if needed). Example: `my-app`, `todo-app`",
            },
        },
        "required": ["project_name"],
    }

    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        terminal_client: TerminalClient,
    ) -> None:
        super().__init__()
        self.terminal_client = terminal_client
        self.workspace_manager = workspace_manager
        self.sandbox_settings = SandboxSettings()

    async def run_impl(
        self,
        tool_input: dict[str, Any],
        message_history: Optional[MessageHistory] = None,
    ) -> ToolImplOutput:
        project_name = tool_input["project_name"]
        
        # Create the frontend directory if it doesn't exist
        workspace_dir = str(self.workspace_manager.root_path())
        project_dir = f"{workspace_dir}/{project_name}"
        frontend_dir = f"{project_dir}/frontend"
        backend_dir = f"{project_dir}/backend"
        
        makedir_command = f"mkdir -p {project_dir}"
        makedir_result = self.terminal_client.shell_exec(
            session_id=self.sandbox_settings.system_shell,
            command=makedir_command,
            exec_dir=workspace_dir,
            timeout=30
        )

        if not makedir_result.success:
            raise Exception(
                f"Failed to create project directory: {makedir_result.output}"
            )

        print("Creating project directory: ", project_dir)

        template_path = "/app/.templates/react-tailwind-python/*"

        get_template_command = f"cp -r {template_path} {project_dir}"
        print("Getting template: ", get_template_command)
        get_template_result = self.terminal_client.shell_exec(
            session_id=self.sandbox_settings.system_shell,
            command=get_template_command,
            exec_dir=workspace_dir,
            timeout=30,  # Do not timeout
        )
        if not get_template_result.success:
            raise Exception(
                f"Failed to get template: {get_template_result.output}"
            )
        
        print("Copy template done, see the project directory: ", project_dir)

        # Install dependencies
        # frontend
        frontend_install_command = "bun install"
        frontend_install_result = self.terminal_client.shell_exec(
            session_id=self.sandbox_settings.system_shell,
            command=frontend_install_command,
            exec_dir=frontend_dir,
            timeout=300,  # Do not timeout
        )
        if not frontend_install_result.success:
            raise Exception(
                f"Failed to install frontend dependencies: {frontend_install_result.output}"
            )

        frontend_add_command = "bun add axios lucide-react react-router-dom"
        frontend_add_result = self.terminal_client.shell_exec(
            session_id=self.sandbox_settings.system_shell,
            command=frontend_add_command,
            exec_dir=frontend_dir,
            timeout=300,  # Do not timeout
        )
        if not frontend_add_result.success:
            raise Exception(
                f"Failed to add frontend dependencies: {frontend_add_result.output}"
            )

        # backend
        backend_install_command = "pip install -r requirements.txt"
        backend_install_result = self.terminal_client.shell_exec(
            session_id=self.sandbox_settings.system_shell,
            command=backend_install_command,
            exec_dir=backend_dir,
            timeout=300,  # Do not timeout
        )
        if not backend_install_result.success:
            raise Exception(
                f"Failed to install backend dependencies: {backend_install_result.output}"
            )

        print("Installed dependencies")

        output_message = f"""Successfully initialized codebase:
```
{project_name}
├── backend/
│   ├── README.md
│   ├── requirements.txt
│   └── src/
│       ├── __init__.py
│       ├── main.py
│       └── tests/
│           └── __init__.py
└── frontend/
    ├── README.md
    ├── eslint.config.js
    ├── index.html
    ├── package.json
    ├── public/
    │   └── _redirects
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   ├── context/
    │   ├── index.css
    │   ├── lib/
    │   ├── main.jsx
    │   ├── pages/
    │   └── services/
    └── vite.config.js
```

Installed dependencies:
- Frontend:
  * `bun install`
  * `bun install tailwindcss @tailwindcss/vite`
  * `bun add axios lucide-react react-router-dom`
- Backend:
  * `pip install -r requirements.txt`
  * Contents of `requirements.txt`:
```
fastapi
uvicorn
sqlalchemy
python-dotenv
pydantic
pydantic-settings
pytest
pytest-asyncio
httpx
openai
bcrypt
python-jose[cryptography]
python-multipart
cryptography
requests
```

You don't need to re-install the dependencies above, they are already installed"""

        return ToolImplOutput(output_message, "Successfully initialized fullstack web application")