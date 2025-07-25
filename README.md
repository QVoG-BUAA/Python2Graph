# Python2Graph

Python2Graph is a tool designed to generate a Simplified Code Property Graph from Python source code. It leverages the `python-scalpel` library to extract detailed structural and relational information, facilitating advanced code analysis.

## Project Structure

This section outlines the directory structure and the key components of the Python2Graph project.

- `patch/`
  Contains Python files that provide patches for external dependencies.

- `src/`
  Contains the complete source code for the Python2Graph application.

  - `src/core/`
    Houses the core logic and functionalities of Python2Graph.

    - `cache/`
      Manages caching mechanisms for various data types. 
      - `cache_proxy.py`: Provides a unified interface for different cache implementations. 
      - `connection.py`: Handles establishing connections to diverse caching systems.

    - `db/`
      Defines interfaces and implementations for database integration.
      - `filedb/`: Implements a file-based database storage.
      - `gremlin/`: Implements integration with Gremlin-server for graph database operations.
      - `client.py`: An abstract base class defining the common database interface.
    - `graph/`
      Defines the data structures used to represent the S-CPG.
    - `process/`
      Orchestrates the graph building process, including frontend analysis and backend database upload.
      - `backend/`: Handles the persistence of the constructed graph to a database.
        - `backend_diff.py`: Implements incremental graph updates.
        - `backend.py`: Contains the core logic for uploading the graph.
      - `frontend/`: Performs static analysis to extract graph components from source code.
        - `impl/`: Houses the concrete implementations for different graph types.
          - `cfg` and `cfg_lib/`: Modules for building the Control Flow Graph (CFG).
          - `dfg` and `dfg_lib/`: Modules for building the Data Flow Graph (DFG).
          - `cg` and `cg_lib/`: Modules for building the Call Graph (CG).
        - `frontend.py`: Provides a high-level, multi-threaded interface for invoking analysis.
        - `common.py`: Contains shared utility functions for frontend operations.
      - `collector/`: Manages the data pipeline, transferring results from the frontend analysis to the backend for persistence.
      - `process.py`: Defines the primary interfaces and workflow orchestration for frontend analysis and backend upload.
  - `src/lib/`
    Contains common libraries and utility modules.

    - `shared/`: Provides a collection of common utility functions and shared resources.
      - `argument.py`: Assists in parsing command-line arguments.
      - `conf.py`: Manages the loading and resolution of configuration settings from `config.yaml`.

  - `src/py2graph.py`
    The main entry point for the Python2Graph application.
- `build.sh`
  A shell script responsible for parsing command-line arguments and initiating the Python2Graph analysis process.

## Requirements

- Python 3.8+

- `requirements.txt`, using pip to install

- Gremin-Server

#### Gremlin-Server Install

The docker now is available, [click here to access.](https://zenodo.org/records/16418079/files/gremlin_image.tar?download=1)

> Neo4j 3.3.9

```bash
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable legacy' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
apt list -a neo4j
apt install neo4j=1:3.3.9
```

> Gemlin-server 3.7.0

```bash
wget https://dlcdn.apache.org/tinkerpop/3.7.0/apache-tinkerpop-gremlin-server-3.7.0-bin.zip
unzip apache-tinkerpop-gremlin-server-3.7.0-bin.zip
cd apache-tinkerpop-gremlin-server-3.7.0-bin
bin/gremlin-server.sh install org.apache.tinkerpop neo4j-gremlin 3.7.0 #Installing the Neo4j control plugin for Gremlin.
```

> Gremlin-Server config
>
> > gremlin-server-neo4j.yaml

```yaml
host: 0.0.0.0
port: 7687
```

> Gremlin-Server config
>
> > neo4j-empty.properties

```yaml
gremlin.neo4j.directory=/opt/neo4j/data/databases/graph.db #neo4j location, use `neo4j console`
```

> Start Gremlin-Server
>
> > if there is no error shown in console, the service is ready to use.

```bash
./bin/gremlin-server.sh conf/gremlin-server-neo4j.yaml console
```

## How to start

Create a file named `config.yaml` in the root directory of the project, and fill in the following content:

```yaml
BACKEND:
  DATABASE: "gremlin"
  GREMLIN:
    CONNECTION_STRING: "ws://<host>:8182/gremlin"
  FILEDB:
    VERTEX_FILE: "./tmp/vertex.json"
    EDGE_FILE: "./tmp/edge.json"
CACHE:
  DATABASE: "memory"
  REDIS:
    HOST: <host>
    PORT: 6379
    DB: <database>
    PASSWORD: <password>
```

- For `BACKEND`, you can choose `DATABASE` from `gremlin` and `filedb`. And fill in the corresponding connection string.
- For `CACHE`, you can choose `DATABASE` from `memory` and `redis`. And fill in the corresponding `redis` connection information. If you use `redis`, you should fill the `REDIS` section, set `PASSWORD` to `null` if you don't have a password.

## Build Graph

See help for `build.sh`, or you can directly run `src/py2graph.py` to get more options. For detailed usage, see both files respectively.
