# Pin the complete browser/OS/Python environment, not only a mutable tag.
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble@sha256:330d401ae23c905896a0c26c66c36fc971b621519e7b11b435a8328d7bf6e031
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DISPLAY="" WAYLAND_DISPLAY=""
COPY data_pipeline/professions/requirements.lock data_pipeline/professions/requirements-dev.lock /locks/
RUN python -m pip install --no-cache-dir --require-hashes -r /locks/requirements.lock
ARG WITH_TESTS=0
RUN if [ "$WITH_TESTS" = "1" ]; then python -m pip install --no-cache-dir --require-hashes -r /locks/requirements-dev.lock; fi
COPY data_pipeline/ /workspace/data_pipeline/
# These are integration-test subjects, never acquisition/generation inputs.
COPY Core/ /workspace/Core/
COPY Locales/ /workspace/Locales/
COPY validation/ /workspace/validation/
COPY DungeonsForever.toc /workspace/DungeonsForever.toc
ENTRYPOINT ["python", "-m", "data_pipeline.professions"]
