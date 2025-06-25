def next_shadcn_deployment_rule(project_name: str) -> str:
    return f"""
Project directory `{project_name}` created successfully. Application code is in `{project_name}/src`. File tree:
```
{project_name}/
│   ├── .gitignore              # Git ignore file
│   ├── biome.json              # Biome linter/formatter configuration
│   ├── jest.config.js          # Jest configuration
│   ├── pnpm.lock               # Lock file for dependencies
│   ├── components.json         # shadcn/ui configuration
│   ├── eslint.config.mjs       # ESLint configuration
│   ├── netlify.toml            # ignore for now
│   ├── next-env.d.ts           # Next.js TypeScript declarations
│   ├── next.config.js          # Next.js configuration
│   ├── package.json            # Project dependencies and scripts
│   ├── postcss.config.mjs      # PostCSS configuration
│   ├── README.md               # Project documentation
│   ├── __tests__/              # Jest test directory
│   ├── src/                    # Source code directory
│   │   ├── app/                # Next.js App Router directory
│   │   │   ├── ClientBody.tsx  # Client-side body component
│   │   │   ├── globals.css     # Global styles
│   │   │   ├── layout.tsx      # Root layout component
│   │   ├── page.tsx            # Home page component
│       └── lib/                # Utility functions and libraries
│           └── utils.ts        # Utility functions
│       └── components/         # Components directory
│           └── ui/             # shadcn/ui components
│               └── button.tsx  # Button component
│   ├── tailwind.config.ts      # Tailwind CSS configuration
    └── tsconfig.json           # TypeScript configuration
```
IMPORTANT NOTE: This project is built with TypeScript(tsx) and Next.js App Router.
Add components with `cd {project_name} && pnpx shadcn@latest add -y -o`. Import components with `@/` alias. Note, 'toast' is deprecated, use 'sonner' instead. Before editing, run `cd {project_name} && pnpm install` to install dependencies. Run `cd {project_name} && pnpm run dev` to start the dev server ASAP to catch any runtime errors. Remember that all terminal commands must be run from the project directory.
Any database operations should be done with Prisma ORM.
Authentication is done with NextAuth. Use bcrypt for password hashing.
Use Chart.js for charts. Moveable for Draggable, Resizable, Scalable, Rotatable, Warpable, Pinchable, Groupable, Snappable components.
Use AOS for scroll animations.
Advance animations are done with Framer Motion, Anime.js, and React Three Fiber.
Before writing the frontend integration, you must write an openapi spec for the backend then you must write test for all the expected http requests and responses using supertest (already installed).
Run the test by running `pnpm test`. Any backend operations should pass all test begin you begin your deployment
The integration must follow the api contract strictly. Your predecessor was killed because he did not follow the api contract.

If you need to use websocket, follow this guide: https://socket.io/how-to/use-with-nextjs
Banned libraries (will break with this template): Quill
"""


def vite_react_deployment_rule(project_name: str) -> str:
    return f"""
Project directory `{project_name}` created successfully. Application code is in `{project_name}/src`. File tree:
```
 {project_name}/
│   ├── .gitignore              # Git ignore file
│   ├── biome.json              # Biome linter/formatter configuration
│   ├── pnpm.lock               # Lock file for dependencies
│   ├── components.json         # shadcn/ui configuration
│   ├── index.html              # HTML entry point
│   ├── netlify.toml            # ignore for now
│   ├── package.json            # Project dependencies and scripts
│   ├── postcss.config.js       # PostCSS configuration
│   ├── public/                 # Static assets directory
│       ├── _redirects          # ignore for now
│   ├── README.md               # Project documentation
│   ├── src/                    # Source code directory
│   │   ├── App.tsx             # Main App component
│   │   ├── index.css           # Global styles
│   │   ├── lib/                # Utility functions and libraries
│   │       └── utils.ts        # Utility functions
│   │   ├── components/         # Components directory
│   │   │   └── ui/             # shadcn/ui components
│   │   │       └── button.tsx  # Button component
│   │   ├── main.tsx            # Entry point
│   │   └── vite-env.d.ts       # Vite TypeScript declarations
│   ├── tailwind.config.js      # Tailwind CSS configuration
│   ├── tsconfig.json           # TypeScript configuration
    └── vite.config.ts          # Vite bundler configuration
```
IMPORTANT NOTE: This project is built with TypeScript(tsx) and Vite + React.

Add components with `cd {project_name} && pnpx shadcn@latest add -y -o`. Import components with `@/` alias. Note, 'toast' is deprecated, use 'sonner' instead. Before editing, run `cd {project_name} && pnpm install` to install dependencies. Run `cd {project_name} && pnpm run dev` to start the dev server ASAP to catch any runtime errors. Remember that all terminal commands must be run from the project directory. 
Use Chart.js for charts. Moveable for Draggable, Resizable, Scalable, Rotatable, Warpable, Pinchable, Groupable, Snappable components.
Use AOS for scroll animations.
Use and install Framer Motion, Anime.js, and React Three Fiber for advance animations.
If you are unsure how to use a library, use search tool to find the documentation.
"""
