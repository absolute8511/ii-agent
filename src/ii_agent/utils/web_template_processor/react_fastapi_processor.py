from ii_agent.prompts.system_prompt import SystemPromptBuilder
from ii_agent.tools.clients.terminal_client import TerminalClient
from ii_agent.utils.web_template_processor.base_processor import BaseProcessor
from ii_agent.utils.workspace_manager import WorkspaceManager


def react_tailwind_python_deployment_rule(project_name: str) -> str:
    return f"""
Project directory `{project_name}` created successfully. Application code is in `{project_name}/src`. 
<UI_design_rules>
### How to Describe a Website UI in Text

Think of yourself as an art director briefing a designer. Break it down into these categories

1. Overall Aesthetic & Mood
This is the high-level "vibe." Use descriptive adjectives. Examples:
  * Minimalist & Serene: Clean, lots of white space, uncluttered
  * Corporate & Trustworthy: Professional, structured, often blue and white palettes
  * Tech & Futuristic: Dark mode, neon accents, sharp lines, maybe monospaced fonts
  * Playful & Vibrant: Bright colors, rounded shapes, fun animations
  * Elegant & Luxurious: Serif fonts, muted tones, sophisticated spacing, high-quality imagery
  * Brutalist & Raw: Exposed structures, monospaced fonts, high contrast, often stark
  * Earthy & Organic: Natural tones (browns, greens), textured backgrounds, soft edges

2. Color Palette
Be specific. Instead of just "blue," define the roles of your colors. 
- Primary: The main brand color, used for primary actions (e.g., main buttons, active links).
- Secondary/Accent: The second most important color, used to highlight secondary information or actions.
- Neutral Palette: The colors for the background, text, borders, and cards. This is crucial. (e.g., `Neutral-50` for background, `Neutral-900` for text, `Neutral-200` for borders).
- Functional Colors: For states like success (green), error (red), warning (yellow/orange).

- Example Description:
  * "A muted, earthy color palette.
      * Primary: A deep forest green (`#2F4F4F`).
      * Accent: A warm terracotta orange (`#E2725B`) for call-to-action buttons.
      * Neutrals: A range from off-white (`#F5F5DC`) for backgrounds to a dark charcoal (`#36454F`) for primary text.
      * Borders: A soft, light gray (`#D3D3D3`)."

3. Typography
This defines the personality of your text.
- Font Family: Specify the type (e.g., Sans-serif, Serif, Monospaced) and if possible, the name (e.g., Inter, Lora, Fira Code).
- Hierarchy: Define sizes and weights for different elements.
  * Headings (`H1`, `H2`, `H3`): e.g., "H1 is large, bold, and has tight letter spacing. H2 is semi-bold and smaller."
  * Body Copy: e.g., "Body text is very readable, with normal weight and generous line height for easy reading."
  * Captions/Labels: e.g., "Small, lighter-weight text."
- Font Pairing: If using more than one font, explain their roles (e.g., "Use a bold serif font like 'Playfair Display' for headings and a clean sans-serif like 'Lato' for body text.")

4. Layout & Spacing
This is the structure and "breathing room."
- Density: Is the layout dense and data-heavy (like a dashboard) or sparse and airy (like a portfolio)?
- Grid System: Mention if it's a strict column-based grid.
- White Space (Negative Space): "Generous white space around elements to give a clean, uncluttered feel."
- Alignment: "All content is left-aligned for readability."

5. Component & Element Styling
Describe the look of your interactive building blocks.
- Buttons:
  * Shape: "Pill-shaped with fully rounded corners" or "Sharp, rectangular buttons."
  * Style: "Solid fill for primary buttons, outline/ghost style for secondary."
  * Effects: "Subtle shadow on hover," "Slightly scales up when pressed."
- Cards:
  * Borders & Shadow: "Cards have a very light 1px border and a soft, diffused shadow to lift them off the page."
  * Corner Radius: "A moderate border-radius of 8px (`rounded-lg` in Tailwind)."
- Input Fields: "Clean, with a simple bottom border that becomes colored when active. No background fill."
- Modals/Pop-ups: "A modal with a semi-transparent dark overlay behind it to focus the user's attention."

6. Iconography
- Style: "Line art icons," "Filled icons," or "Duotone icons."
- Weight: "Thin and light" or "Bold and chunky."
- Consistency: "All icons should come from the same family (e.g., Heroicons, Phosphor Icons)."

### Current UI Trends

Incorporate these trends to make your UI feel modern
- Bento Grids: A grid-based layout inspired by Japanese bento boxes. It uses different-sized containers to display a variety of content in a visually engaging and organized way. Perfect for dashboards and portfolios
- Glassmorphism / Frosted Glass: A style where a light, blurred background is visible through an element, creating a "frosted glass" effect. It adds depth and focus. In Tailwind, you'd use `backdrop-blur` and semi-transparent background colors
- Kinetic Typography: Text that moves or animates to grab attention or guide the user. Use this sparingly for headings or key phrases
- AI-Generated Visuals & Gradients: Using AI to create unique, abstract blob shapes, textures, and complex, dynamic gradients for backgrounds. It adds a very modern, organic, and unique feel
- Enhanced Microinteractions: Small, delightful animations on hover, click, or page load that provide feedback and add personality (e.g., a like button that bursts into confetti, a toggle that smoothly animates)
- Minimalism with a "Brutalist" Edge: Keeping the core clean and minimal, but adding one or two "raw" elements like a monospaced font, a sharp-cornered button, or a high-contrast color scheme for a bold, confident look
</UI_design_rules>

<web_application_development_rules>
When assigned a full-stack web application development task using a React/FastAPI stack, you will adopt a UI-First development methodology. This approach prioritizes building and validating the user interface with stakeholders before developing the backend logic. You will use Mock Service Worker (MSW) to simulate the backend API, ensuring the frontend is developed against a consistent and predictable contract.

Follow these structured phases and steps meticulously:

### **Phase 1: Discovery and Design**

This phase is about understanding the requirements and creating the technical blueprint for the application

1. Clarify Requirements (Interactive Dialogue)
- Begin by discussing with the user to fully understand the project scope, key features, and user personas
- Ask one or two clarifying questions at a time to avoid overwhelming the user. Focus on "what" the user wants to achieve, not "how" it will be implemented yet
- If the user is unsure, propose the simplest, most common implementation as a starting point for feedback

2. Define Core Features and User Stories
- Based on the discussion, break down the application into a list of core features
- For each feature, write simple user stories (e.g., "As a user, I want to see a list of my projects so I can select one to view its details.")

3. Design the API Contract
- This is the most critical step for the UI-First workflow. Before writing any code, define the API endpoints that the frontend will need
- Document this contract in OpenAPI YAML specification format (openapi.yaml)
- This contract is the source of truth for both the MSW mocks and the future FastAPI implementation

4. Design the UI
- Must follow the <UI_design_rules> section strictly except user explicitly specifies otherwise
- Describe the detailed visual UI design to user follow the <UI_design_rules> section

### **Phase 2: Project Setup**
- Use `fullstack_project_init` tool to establish the project structure and install all necessary dependencies
- Project structure:
```
{project_name}/
├── backend
│   ├── README.md
│   ├── requirements.txt
│   └── src
│       ├── __init__.py
│       ├── main.py
│       └── tests
│           └── __init__.py
└── frontend
    ├── README.md
    ├── eslint.config.js
    ├── index.html
    ├── package.json
    ├── public
    │   └── _redirects
    ├── src
    │   ├── components
    │   ├── context
    │   ├── lib
    │   ├── mocks # MSW mocks
    │   ├── pages
    │   ├── App.jsx
    │   ├── index.css
    │   └── main.jsx
    └── vite.config.js
```
- Installed dependencies:
  * Frontend: `bun install`, `bun install tailwindcss @tailwindcss/vite`, `bun add axios lucide-react react-router-dom`, `bun add msw --dev`
  * Backend: `pip install -r requirements.txt`
- Contents of `backend/requirements.txt`:
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
- You don't need to re-install the dependencies above, they are already installed

### **Phase 3: UI Development with Mocking (React + MSW)**

Build the complete user interface as if the backend already exists

1. Configure MSW
- In the `frontend` directory, run the MSW init command to create the service worker script: `npx msw init public/ --save`
- Inside `src/mocks`, create `handlers.js`. This is where you will implement the mock API endpoints
- Create `src/mocks/browser.js` to set up and export the worker
- Integrate MSW into your application's entry point (`src/main.jsx`) by conditionally starting the worker in development mode

2. Develop UI Components with Tailwind CSS
- Follow a component-driven approach. Start with small, reusable "atomic" components (Button, Input, Card) and compose them into larger page layouts
- Use Tailwind CSS utility classes directly in your JSX for rapid, consistent styling
- Build the full UI as if it's connected to a complete backend—do not include any references to it being a demo
  * For authentication, do not display demo account credentials in the UI. Instead, share them with the user through the `message_user` tool

3. Implement Data Fetching against Mocks
- Create a dedicated service layer for API calls (e.g., `src/services/api.js`). This module will use axios to make HTTP requests
- In your `handlers.js`, create mock data objects that manually follow the structure defined in your openapi.yaml contract. This step requires discipline, as there is no automatic type-checking
- In your React components, use hooks like `useEffect` and `useState` (or preferably a server-state library like React Query) to fetch data by calling functions from your API service
- MSW will automatically intercept these outgoing requests and return the mocked responses you defined in handlers.js, making it seem like you are communicating with a real backend

4. Demo and Iterate
- Once a feature's UI is complete and functioning with mock data, deploy it locally to a preview service
  * Use port `3030` by default (`bun run dev -- --port 3030`); if unavailable, increment by +1
  * After deploying locally, use the `register_deployment` tool to obtain the public URL
  * Validate all frontend pages through browser tool before sharing it with the user
- UI Component Validation Loop:
  * Inspect: Use Browser Developer Tools to view the rendered UI
  * Validate: Confirm that all components render correctly and are fully functional
  * Action: If any component is missing or broken, immediately halt the process and fix the issue before proceeding
- If you hit the error when validate through the browser tool (e.g. cannot login)
  * View the frontend shell output to see any error messages
  * Review the code at the error page to see if there is any issue
  * Fix until the frontend is working before sending the public URL to the user
  * Any assume like it will work is FORBIDDEN, you must ensure all the components are working and the UI is as expected
- Present the public URL to the user and wait for feedback
  * Use `message_user` tool to ask the user for feedback
  * Use `return_control_to_user` tool to wait for approval
- Incorporate feedback and repeat the cycle until the UI is approved by the user
- If the user is satisfied with the UI, proceed to the next phase

#### **Important notes about frontend development:**
- Your knowledge about tailwind css is quite outdated, in latest version:
  * No need of `postcss.config.js`, `tailwind.config.js`  
  * Add an @import to your CSS file that imports Tailwind CSS
```css
@import "tailwindcss";
```
  * Make sure your compiled CSS is included in the <head> then start using Tailwind's utility classes to style your content. Example:
```html
<!doctype html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="/src/styles.css" rel="stylesheet">
</head>
<body>
  <h1 class="text-3xl font-bold underline">
    Hello world!
  </h1>
</body>
</html>
```
- Use `bun` for all operations (bun install, bun add, bun run dev, bun run build, bun run preview, ...)
  * For demo testing, use `bun run dev -- --port PORT`
  * For final deployment (intergrate with backend), build the frontend with `bun run build`, then deploy the frontend with `bun run preview -- --port PORT`
- A common issue in your development is blank or empty pages. To prevent this:
  * Thoroughly test and review your code after each major update
  * Inspect console logs and browser dev tools for errors
  * Add fallback UI or error boundaries if needed
  * Manually visit **all pages** in the browser using the public URL to ensure correct rendering and functionality before sharing it with the user
- Make sure the frontend contains no "coming soon" or "under development" pages - all user-requested features must be fully implemented and functional
- According to PostCSS, all @import statements must come before any other rules, but also, all `@import url(...)` must come before `@import "tailwindcss"` (when using Tailwind with PostCSS). Example:
  * If you want to import Google Fonts in index.css, you need to move Google Fonts `@import url(...)` to the very top, before `@import "tailwindcss";`.

### **Phase 4: Backend Implementation (FastAPI)**

With the UI approved, build the real backend to match the established API contract
Technology stack: Python, FastAPI, SQLite, OpenAI (for LLM-based functionality)

0. Third-party Services Integration
- Search and review official documentation for the service
- Do not assume anything because your knowledge may be outdated; verify every endpoint and parameter
- If credentials are required (API key, access token, etc.), request them from the user explicitly through the `message_user` & `return_control_to_user` tools

1. Implement Pydantic Models
- In your `backend` project, create Pydantic models that precisely match the request and response body structures defined in the **API Contract**. This provides automatic data validation and serialization

2. Build FastAPI Endpoints
- Create the path operation functions (`@app.get`, `@app.post`, etc.) for each endpoint in the contract
- Use the Pydantic models for request bodies and `response_model` declarations

5. Implement Business Logic and Database Integration
- Connect to a database, perform CRUD operations, implement core features and handle any other required logic

6. Write and Run Tests
- Framework: `pytest`, `httpx`, FastAPI's `TestClient`
- Mocked interactions with third-party services to test your integration logic without making real, slow, or costly API calls during testing
- Cover Key Cases: Write tests that cover:
  * Success cases (correct data, 200/201 status)
  * Error cases (404, 401, 422)
  * Business logic rules
  * Mocked interactions with third-party services to test your integration logic without making real, slow, or costly API calls during testing
- Ensure all tests are passing before moving to the next phase

7. Deployment
- Deploy backend and frontend on separate shell sessions
- Always bind the backend server to `0.0.0.0` to ensure accessibility
- Use port `8080` by default; if unavailable, increment by +1
- After deployment, use the `register_deployment` tool to obtain the public URL
- Validate backend functionality through the public endpoint via curl or python requests
</web_application_development_rules>
"""


class ReactTailwindPythonProcessor(BaseProcessor):
    template_name = "react-tailwind-python"

    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        terminal_client: TerminalClient,
        system_prompt_builder: SystemPromptBuilder,
        project_name: str,
    ):
        super().__init__(
            workspace_manager, terminal_client, system_prompt_builder, project_name
        )
        self.project_rule = react_tailwind_python_deployment_rule(project_name)

    def install_dependencies(self):
        self.terminal_client.shell_exec(
            self.sandbox_settings.system_shell,
            f"cd {self.project_name}/frontend && bun install",
            exec_dir=str(self.workspace_manager.root_path()),
            timeout=999999,  # Quick fix: No Timeout
        )

        self.terminal_client.shell_exec(
            self.sandbox_settings.system_shell,
            f"cd {self.project_name}/backend && pip install -r requirements.txt",
            exec_dir=str(self.workspace_manager.root_path()),
            timeout=999999,  # Quick fix: No Timeout
        )
