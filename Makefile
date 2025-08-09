.PHONY: install dev test clean
SHELL = /bin/zsh
CONDA_ACTIVATE = source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate
ENV_NAME = ai-agent-with-mongodb

install:
	conda env create -f environment.yml --name $(ENV_NAME) || true && \
	$(CONDA_ACTIVATE) $(ENV_NAME) && \
	pip install --upgrade pip && \
	pip install -r requirements.txt

dev:
	docker-compose up -d mongodb-health
	$(CONDA_ACTIVATE) $(ENV_NAME) && \
	$$(conda info --envs | grep $(ENV_NAME) | awk '{print $$NF}')/bin/python src/main.py

test:
	$(CONDA_ACTIVATE) $(ENV_NAME) && \
	pytest tests/

clean:
	docker-compose down -v
	conda env remove -y --name $(ENV_NAME) || true
	rm -rf .pytest_cache .pytest_cache