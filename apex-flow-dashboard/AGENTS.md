<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Frontend Architecture & Development Rules

## 1. Directory Structure
- All frontend code must live in `src/`.

## 2. Routing (`src/app/`)
- Use route groups to organize routes:
  - `(auth)/`: For authentication-related pages (login, signup, etc.).
  - `dashboard/`: For main dashboard and core application pages.

## 3. Components (`src/components/`)
- `ui/`: Strictly reserved for auto-generated `shadcn/ui` primitive components.
- `shared/`: For global, generic, and layout components (e.g., Header, Footer, Sidebar, Loader).

## 4. Feature-Driven Architecture (`src/features/`)
- Encapsulate logic by feature rather than type. 
- Each feature directory (e.g., `src/features/project/`) contains its own specific logic.
- **Components**: Feature-specific components must be placed in a `components/` subfolder within the feature (e.g., `src/features/project/components/`).
- **Hooks, Context, Types, Utils**: Initially, omit subfolders for these and use single files at the feature root (e.g., `hooks.ts`, `types.ts`, `utils.ts`, `context.tsx`). Only create folders if the module grows to require multiple files.

## 5. Libraries (`src/lib/`)
- Dedicated for generic utilities, global configurations, third-party library setups, and API clients.
