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
- `lib/supabase/client.ts`: Supabase **browser** client only — used solely for auth flows (sign in, sign up, session management). Do NOT add a server client.

## 6. Backend-First API Rule
- **All data operations go through the FastAPI backend**. Never call Supabase directly for data.
- Auth is the only exception: the Supabase browser client is used to authenticate the user and obtain a JWT session token.
- The JWT `access_token` from Supabase is then passed as `Authorization: Bearer <token>` to every FastAPI request.
- Use `useAuth()` to access the `accessToken` in any client component.

## 7. Server Actions (`actions.ts`)
- Do **not** create `actions.ts` for features that communicate with the FastAPI backend. Use client-side service functions or hooks instead.
- `actions.ts` is only appropriate for auth flows or other cases where a Next.js Server Action is genuinely needed (e.g., session management that requires cookies).

## 8. Auth State
- `AuthProvider` (in `src/features/auth/context.tsx`) wraps the entire app and is the single source of truth for auth state.
- Consume it via `useAuth()` from `src/features/auth/hooks.ts`.
- Do not duplicate session state elsewhere.
