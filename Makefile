DEPENDENCIES_DIR=dependencies
DATA_DIR=data

install: 
	mkdir -p $(DEPENDENCIES_DIR)
	mkdir -p $(DATA_DIR)
	pip install -r requirements.txt
	pip install $(DEPENDENCIES_DIR)/graphwerk-0.0.0-py3-none-any.whl $(DEPENDENCIES_DIR)/openai_lib-0.0.0-py3-none-any.whl


clean:
	pip uninstall -r requirements.txt
	pip uninstall openai_lib graphwerk

distclean:
	rm -f $(DEPENDENCIES_DIR)/*
