# Builds for the host platform; for AWS ARM: docker build --platform linux/arm64 .
#
# There is no application in this image: the placeholder `app` package was removed in
# #51, and Trazo is a governance overlay rather than a service. What remains is the
# toolchain and the test suite, so the default command runs the tests. A derived
# project replaces the COPY and CMD below with its own code.
FROM python:3.15-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /trazo
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project
COPY tests ./tests
COPY .claude ./.claude
COPY scripts ./scripts
RUN useradd --create-home --uid 10001 trazo
USER trazo
CMD ["uv", "run", "pytest"]
