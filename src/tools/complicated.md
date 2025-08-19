Well, it's a bit longer story with keys. You can simply put them at `keys` directory
(you'll need to create it first at root dir of project).

In provided docker-compose.yml, you can find:

```
  - "${PATH_TO_KEYS}/:/src/keys"
```

Reason for this: I host docker-compose file on separate path from project itself. Mainly because you usually operate on multiple
microservices and having separate special location for docker files, keys and other stuff that shared between all projects.<br>
<br>


So, in my case i have `/deploy/` directory at different location and structure is:<br>
```
.
├── docker-compose.yml
├── env.sh
└── keys
    └── firebase-keyjson

2 directories, 3 files
```

Here, env.sh looks like:<br>

```sh
export PATH_TO_PROJECTS="/codetemp/chat"

export PATH_TO_CHAT_REPO="$PATH_TO_PROJECTS/api/chat"
export PATH_TO_KEYS="$PATH_TO_PROJECTS/compose/keys"
```

This is pathes to my projects. You can alternatively add here your env variables for databases and other stuff and
modify docker-compose.yml to use variables instead of plain text.<br>

Note that you'll need to execute .sh scripts to load in shell env before building/running/restarting/anything with docker compose.<br>
<br>

alternative, more simple docker-compose.yml without variables will look like:

```yml
services:
  backend-chat:
    build: "${PATH_TO_CHAT_REPO}"
    container_name: chat-backend
    ports:
      - "8000:8000"
    working_dir: /src
    volumes:
      - "/codetemp/chat/chat/chat/:/src"
    depends_on:
      postgres-chat:
        condition: service_healthy
        restart: true

  postgres-chat:
    image: postgres:latest
    container_name: postgresql-chat
    volumes:
      - "/codetemp/chat/chat/chat//sql.sql:/docker-entrypoint-initdb.d/init.sql"
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: chat
      POSTGRES_USER: postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      # test: ["CMD-SHELL", "pg_isready"]
      interval: 5s
      timeout: 5s
      retries: 5

  test-postgres-chat:
    image: postgres:latest
    container_name: postgresql-test-chat
    volumes:
      - "/codetemp/chat/chat/chat//sql.sql:/docker-entrypoint-initdb.d/init.sql"
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: testchat
      POSTGRES_USER: postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      # test: ["CMD-SHELL", "pg_isready"]
      interval: 5s
      timeout: 5s
      retries: 5


```

