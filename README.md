# AI Agent with MongoDB

A Python MongoDB service template
The connection string for the docker cluster is:
`mongodb://mongodb1:27017,mongodb2:27018,mongodb3:27019/?replicaSet=rs0`

## Features

- Integration with MongoDB
- Docker Compose setup for local development

## Prerequisites

- Python 3.13.\*
- [Conda](https://www.anaconda.com/docs/getting-started/miniconda/install)
- Docker and Docker Compose
- Make (optional, for using Makefile commands)

## Getting Started

Start by adding code in the [index.ts](src/main.py) or using the [playground](playground.ipynb)

### Local Development

1. Clean and Install dependencies:

   ```bash
   make clean install
   ```

2. Start the development server:
   ```bash
   make dev
   ```

## Development Commands

- `make clean`: Clean build artifacts
- `make install`: Install dependencies
- `make dev`: Start development server
