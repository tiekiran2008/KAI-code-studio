# =============================================================================
# KAI Code Studio — Frontend Production Dockerfile (multi-stage)
# =============================================================================
#
# Stage 1: Build
#   Installs dependencies and runs the Vite/TypeScript production build.
#   VITE_* variables are build-time arguments — they get compiled into the
#   static JS bundle by Vite at build time, NOT at container runtime.
#   Inject them via `docker build --build-arg VITE_API_BASE_URL=...`
#   or via the CI `build-args:` block.
#
# Stage 2: Serve
#   Copies only the compiled dist/ output into a minimal nginx:alpine image.
#   No Node.js, no source code, no secrets remain in the final image.
# =============================================================================

# ---- Stage 1: Build --------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer-cached separately from source)
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

# Declare build-time variables (populated by --build-arg or CI build-args)
ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ARG VITE_API_PREFIX=/api/v1
ARG VITE_SUPABASE_URL=""
ARG VITE_SUPABASE_ANON_KEY=""

# Expose them as real environment variables so Vite picks them up during build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_PREFIX=${VITE_API_PREFIX}
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL}
ENV VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}

# Copy source and build
COPY . .
RUN npm run build

# ---- Stage 2: Serve --------------------------------------------------------
FROM nginx:alpine AS production

# Remove the default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our SPA-aware nginx config
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copy the production build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx listens on port 80
EXPOSE 80

# Default command (nginx runs in foreground)
CMD ["nginx", "-g", "daemon off;"]
