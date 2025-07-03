FROM nikolaik/python-nodejs:python3.10-nodejs20-slim

# Set environment variables
ENV NODE_OPTIONS="--max-old-space-size=4096"

RUN apt-get update && apt-get install -y \
    build-essential \
    procps \
    lsof \
    git \
    tmux \
    bc \
    net-tools \
    unzip

#RUN echo 'export PS1="[CMD_BEGIN]\\n\\u@\\h:\\w\\n[CMD_END]"; export PS2=""' >> /root/.bashrc

COPY src/ii_agent/utils/tool_client /app/ii_client

WORKDIR /app

RUN pip install -r ii_client/requirements.txt

COPY .templates /app/templates

RUN npm install -g @anthropic-ai/claude-code

RUN pip install claude-code-sdk

RUN mkdir /root/.claude/

COPY claude_code_credentials.json /root/.claude/.credentials.json

RUN curl -fsSL https://bun.sh/install | bash

RUN npm install -g vercel

CMD ["python", "-m", "ii_client.sandbox_server", "--port", "17300" , "--cwd", "/workspace"]
